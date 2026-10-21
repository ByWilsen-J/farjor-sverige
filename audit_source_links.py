#!/usr/bin/env python3
"""Check real source URLs, record attempts, and repair only verified safe redirects."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
from urllib.parse import parse_qsl, urlsplit

import requests
from route_registry import ACTIVE_ROUTES, REFERENCE_ONLY_ROUTES

ROOT = Path(__file__).resolve().parent
LEDGER = ROOT / "docs/source-link-checks.json"
URL_PATTERN = re.compile(r'https?://[^\s\'"<>`\\]+')


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def data_urls(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"kalla", "source", "source_url", "länk"} and isinstance(item, str) and item.startswith(("https://", "http://")):
                yield item
            elif isinstance(item, (dict, list)):
                yield from data_urls(item)
    elif isinstance(value, list):
        for item in value:
            yield from data_urls(item)


def collect_urls(root=ROOT):
    urls = {route.source_url for route in (*ACTIVE_ROUTES, *REFERENCE_ONLY_ROUTES)}
    urls.update(data_urls(json.loads((root / "farjor_data.json").read_text())))
    for path in root.glob("*.html"):
        # JavaScript URL templates need their scraper request, not a literal GET.
        urls.update(url for url in URL_PATTERN.findall(path.read_text()) if "${" not in url)
    return sorted(url for url in urls if url and not url.endswith(("/day/", "?")))


def is_api_url(url):
    parts = urlsplit(url)
    return any(token in parts.path.lower() for token in ("/api/", "/graphql", "protheus-api")) or "appsync-api" in parts.netloc


def classify_status(status, api=False):
    if 200 <= status < 300:
        return "ok"
    if status in {401, 403, 407, 429, 451}:
        return "blocked_or_limited"
    if api and status in {400, 404, 405, 406, 415, 422}:
        return "api_requires_request"
    if api and status >= 500:
        return "api_request_or_server_error"
    if status in {404, 410}:
        return "broken"
    if status >= 500:
        return "temporarily_unavailable"
    return "needs_review"


def placeholder_destination(url):
    path = urlsplit(url).path.lower().replace("_", "-")
    return any(word in path for word in ("under-construction", "underconstruction", "maintenance", "coming-soon", "placeholder"))


def safe_redirect(original, final, chain, content_type):
    """Never infer a replacement from a 302, domain move, landing page, or API."""
    old, new = urlsplit(original), urlsplit(final)
    if original == final or is_api_url(original) or placeholder_destination(final):
        return False
    if not chain or any(code not in {301, 308} for code in chain):
        return False
    if old.hostname != new.hostname or new.scheme != "https" or old.query != new.query:
        return False
    if old.username or old.password or new.username or new.password or (old.port or 443) != (new.port or 443) or old.fragment != new.fragment:
        return False
    sensitive = {"token", "access_token", "auth", "authorization", "signature", "sig", "key", "api_key", "apikey", "policy", "expires"}
    if any(key.lower() in sensitive or key.lower().startswith(("x-amz-", "x-goog-")) for key, _ in parse_qsl(old.query)):
        return False
    if new.path.rstrip("/") in {"", "/en", "/sv", "/sv-se", "/da", "/en-gb"}:
        return False
    if any(word in new.path.lower() for word in ("login", "error", "not-found", "access-denied", "captcha")):
        return False
    if old.path.lower().endswith(".pdf"):
        return new.path.lower().endswith(".pdf") and "pdf" in content_type
    return "html" in content_type and not new.path.lower().endswith(".pdf")


def check_url(url, previous=None, get=requests.get, pause=time.sleep):
    result = {"url": url, "checked_at": utc_now(), "method": "GET", "api_endpoint": is_api_url(url)}
    try:
        response = get(url, timeout=(10, 25), allow_redirects=True, headers={"User-Agent": "FarjorSourceMonitor/1.0 (+https://farjor.axling.nu)", "Range": "bytes=0-65535"}, stream=True)
        status, final = response.status_code, response.url
        chain = [item.status_code for item in response.history]
        content_type = response.headers.get("Content-Type", "")
        response.close()
        classification = classify_status(status, result["api_endpoint"])
        if classification == "ok" and placeholder_destination(final):
            classification = "needs_review"
            result["reason"] = "destination_placeholder"
        # A one-off CDN response must never be called a confirmed dead link.
        if classification == "broken":
            pause(0.3)
            retry = get(url, timeout=(10, 25), allow_redirects=True, headers={"User-Agent": "FarjorSourceMonitor/1.0"}, stream=True)
            retry_status = retry.status_code
            retry.close()
            result["confirmation_status"] = retry_status
            if classify_status(retry_status, result["api_endpoint"]) != "broken":
                classification = "needs_review"
        result.update(status=classification, http_status=status, final_url=final, redirect_statuses=chain, content_type=content_type)
        result["safe_redirect"] = classification == "ok" and safe_redirect(url, final, chain, content_type)
        if classification == "ok":
            result["last_ok_at"] = result["checked_at"]
        elif previous and previous.get("last_ok_at"):
            result["last_ok_at"] = previous["last_ok_at"]
    except requests.RequestException as exc:
        result.update(status="network_error", error=type(exc).__name__, error_detail=str(exc)[:500], safe_redirect=False)
        if previous and previous.get("last_ok_at"):
            result["last_ok_at"] = previous["last_ok_at"]
    return result


def replace_data_urls(value, mapping):
    if isinstance(value, dict):
        return {key: mapping.get(item, item) if key in {"kalla", "source", "source_url", "länk"} and isinstance(item, str) else replace_data_urls(item, mapping) for key, item in value.items()}
    if isinstance(value, list):
        return [replace_data_urls(item, mapping) for item in value]
    return value


def apply_redirects(root, results):
    mapping = {}
    for entry in results.values():
        if entry.get("safe_redirect"):
            # A second independent GET validates the final target before writing.
            confirmation = check_url(entry["final_url"])
            if confirmation.get("status") == "ok" and confirmation.get("final_url") == entry["final_url"]:
                mapping[entry["url"]] = entry["final_url"]
    if not mapping:
        return {}
    path = root / "farjor_data.json"
    data = json.loads(path.read_text())
    updated = replace_data_urls(data, mapping)
    if updated != data:
        path.write_text(json.dumps(updated, ensure_ascii=False, separators=(",", ":")) + "\n")
    for path in root.glob("*.html"):
        text = path.read_text()
        # Match entire quoted literals only. Never replace part of an API URL.
        updated = re.sub(r"([\"'])(https?://[^\"']+)\1", lambda match: match.group(1) + mapping.get(match.group(2), match.group(2)) + match.group(1), text)
        if updated != text:
            path.write_text(updated)
    return mapping


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply-safe-redirects", action="store_true")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    previous = json.loads(LEDGER.read_text()).get("links", {}) if LEDGER.exists() else {}
    urls = collect_urls()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = dict(zip(urls, pool.map(lambda url: check_url(url, previous.get(url)), urls)))
    applied = apply_redirects(ROOT, results) if args.apply_safe_redirects else {}
    # Preserve real historical attempts, including URLs no longer in use.
    ledger = {**previous, **results}
    for original, final in applied.items():
        ledger[original]["auto_replaced_with"] = final
        ledger[final] = check_url(final, previous.get(final))
    LEDGER.parent.mkdir(exist_ok=True)
    LEDGER.write_text(json.dumps({"generated_at": utc_now(), "links": ledger, "active_urls": urls, "applied_redirects": applied}, ensure_ascii=False, indent=2) + "\n")
    counts = {status: sum(row["status"] == status for row in results.values()) for status in sorted({row["status"] for row in results.values()})}
    print(json.dumps({"checked": len(urls), "results": counts, "safe_redirects_applied": len(applied)}, ensure_ascii=False))
    return 1 if counts.get("broken", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
