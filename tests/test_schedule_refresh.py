"""Regression cases for schedule loss, stale rows and uncertain arrivals."""
import contextlib
import io
import json
import tempfile
import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path
from unittest.mock import patch

import check_route_coverage as checker
import update_fartyg as updater
from route_registry import ACTIVE_BY_ROUTE, filter_instances_to_primary_sources
from schedule_instances import (
    build_base_instances, make_dynamic_instance, merge_dynamic_sailings, public_window,
)
from verified_schema_overrides import apply_verified_schema_overrides


ANCHOR = date(2026, 10, 21)
ROUTE = ACTIVE_BY_ROUTE[("Tallink Silja", "Stockholm", "Tallinn")]


def sailing(ds="2026-10-21", dep="17:30", **kwargs):
    return {
        "date": ds, "rederi": "Tallink Silja", "avghamn": "Stockholm", "ankhamn": "Tallinn",
        "avgtid": dep, "anktid": "11:00", "ankomstdatum": "2026-10-22",
        "fartyg": "Baltic Queen", "source_type": ROUTE.source_type,
        "source_detail": ROUTE.source_detail, "kalla": ROUTE.source_url, **kwargs,
    }


def schema():
    return [{
        "rederi": "Tallink Silja", "avghamn": "Stockholm", "ankhamn": "Tallinn",
        "veckodag": "Alla", "avgtid": "17:30", "anktid": "11:00", "nasta_dag": True,
        "kalla": "https://www.tallink.com/sv/tidtabeller",
    }]


def coverage(first="2026-10-21", last="2026-10-23"):
    return {
        "rederi": ROUTE.operator, "avghamn": ROUTE.avghamn, "ankhamn": ROUTE.ankhamn,
        "date_from": first, "date_to": last,
        "source_type": ROUTE.source_type, "source_detail": ROUTE.source_detail,
    }


class RefreshRegressionTests(unittest.TestCase):
    def test_single_live_day_keeps_fallback_for_other_dates(self):
        instances = build_base_instances({"schema": schema()}, ANCHOR)
        merge_dynamic_sailings(instances, [sailing()])
        filter_instances_to_primary_sources(instances)
        self.assertEqual(instances["2026-10-21"][0]["source_type"], "dynamic_schedule")
        self.assertEqual(instances["2026-10-22"][0]["source_type"], "weekly_schedule")
        self.assertEqual(len(instances["2027-01-21"]), 1)

    def test_changed_departure_replaces_old_snapshot_only_on_returned_day(self):
        cached = [sailing(), sailing("2026-10-22")]
        fresh = [sailing(dep="18:00")]
        merged = updater.combine_cached_and_fresh_sailings(cached, fresh)
        self.assertEqual([(row["date"], row["avgtid"]) for row in merged], [
            ("2026-10-22", "17:30"), ("2026-10-21", "18:00"),
        ])

    def test_empty_source_keeps_cache(self):
        cached = [sailing()]
        self.assertEqual(updater.combine_cached_and_fresh_sailings(cached, []), cached)

    def test_upcoming_catalog_preserves_departed_and_beyond_horizon_rows(self):
        def mols(clock, cached=False, day="2026-10-21"):
            return sailing(day, clock, rederi="Øresundslinjen", avghamn="Helsingør", ankhamn="Helsingborg",
                           source_detail=updater.molslinjen.SOURCE_DETAIL,
                           source_checked_at="2026-10-21T20:00:00Z", source_cached=cached)
        cached = [mols("09:00", True), mols("22:10", True), mols("22:30", True), mols("23:45", True),
                  mols("09:00", True, "2026-10-22")]
        fresh = [mols("22:20"), mols("23:30")]
        rows = updater.combine_cached_and_fresh_sailings(cached, fresh)
        self.assertEqual({(row["date"], row["avgtid"]) for row in rows}, {
            ("2026-10-21", "09:00"), ("2026-10-21", "22:20"), ("2026-10-21", "23:30"),
            ("2026-10-21", "23:45"), ("2026-10-22", "09:00"),
        })

    def test_coincident_operators_are_not_a_duplicate_event(self):
        first = make_dynamic_instance(sailing())
        second = dict(first, rederi="TT-Line")
        self.assertNotEqual(checker.event_key(first), checker.event_key(second))
        self.assertEqual(checker.event_key(first), checker.event_key(deepcopy(first)))

    def test_authoritative_empty_date_removes_cached_sailing(self):
        covered = updater.coverage_route_days([coverage()], ANCHOR, date(2026, 10, 23))
        merged = updater.combine_cached_and_fresh_sailings([sailing()], [], covered)
        self.assertEqual(merged, [])
        self.assertEqual(len(covered), 3)

    def test_secondary_source_cannot_declare_empty_coverage(self):
        bad = coverage()
        bad["source_type"] = "weekly_schedule"
        self.assertEqual(updater.coverage_route_days([bad], ANCHOR, date(2026, 10, 23)), set())

    def test_source_exception_is_isolated_and_recorded(self):
        statuses = {}
        def broken_source():
            raise TimeoutError("source unavailable")
        with self.assertLogs(updater.log, level="ERROR"):
            rows = updater.collect_source("failed", broken_source, ANCHOR, ANCHOR, statuses)
        self.assertEqual(rows, [])
        self.assertEqual(statuses["failed"]["status"], "error")
        self.assertIn("checked_at", statuses["failed"])

    def test_malformed_partial_source_does_not_replace_cache(self):
        statuses = {}
        with self.assertLogs(updater.log, level="WARNING"):
            rows = updater.collect_source("partial", lambda: [sailing(), {"date": "broken"}], ANCHOR, ANCHOR, statuses)
        self.assertEqual(rows, [])
        self.assertEqual(statuses["partial"]["status"], "partial")
        self.assertEqual(statuses["partial"]["accepted_rows"], 0)

    def test_source_checks_and_cache_labels_survive_roundtrip(self):
        statuses = {}
        rows = updater.collect_source("ok", lambda: [sailing()], ANCHOR, ANCHOR, statuses)
        instance = make_dynamic_instance(rows[0])
        self.assertFalse(instance["source_cached"])
        _, legacy = updater.sync_legacy_fields_from_instances({"2026-10-21": [instance]})
        retained = updater.legacy_dynamic_sailings(legacy)[0]
        self.assertTrue(retained["source_cached"])
        self.assertEqual(retained["source_checked_at"], statuses["ok"]["checked_at"])

    def test_arrival_not_copied_from_different_day(self):
        known = make_dynamic_instance(sailing())
        unknown = make_dynamic_instance(sailing("2026-10-23", anktid="", ankomstdatum=""))
        updater.backfill_incomplete_instances({"2026-10-21": [known], "2026-10-23": [unknown]})
        self.assertEqual(unknown["anktid"], "")
        self.assertEqual(unknown["ankomstdatum"], "")

    def test_date_table_has_date_table_priority(self):
        row = make_dynamic_instance(sailing(source_type="date_table"))
        self.assertEqual(row["source_priority"], 70)

    def test_old_publication_window_is_detected(self):
        old = build_base_instances({"schema": schema()}, date(2026, 7, 21))
        issues = checker.publication_window_issues({"avgangsinstanser": old}, ANCHOR)
        self.assertTrue(any("datumbucketar" in issue for issue in issues))

    def test_reviewed_overrides_are_idempotent(self):
        once = apply_verified_schema_overrides(schema())
        self.assertEqual(apply_verified_schema_overrides(once), once)

    def run_coverage_check(self, instances):
        output = io.StringIO()
        with patch.object(checker, "load_data", return_value={"avgangsinstanser": instances}), \
                patch.object(checker, "active_route_keys", return_value={ROUTE.key}), \
                patch.object(checker.sys, "argv", ["check_route_coverage.py", "--anchor-date", ANCHOR.isoformat()]), \
                contextlib.redirect_stdout(output):
            code = checker.main()
        return code, output.getvalue()

    def test_coverage_accepts_different_sources_on_different_dates(self):
        instances = build_base_instances({"schema": schema()}, ANCHOR)
        merge_dynamic_sailings(instances, [sailing()])
        filter_instances_to_primary_sources(instances)
        code, output = self.run_coverage_check(instances)
        self.assertEqual(code, 0, output)

    def test_coverage_rejects_route_with_only_expired_rows(self):
        instances = build_base_instances({"schema": schema()}, ANCHOR)
        for ds in instances:
            if ds >= ANCHOR.isoformat():
                instances[ds] = []
        code, output = self.run_coverage_check(instances)
        self.assertEqual(code, 1)
        self.assertIn("endast utgångna avgångar", output)

    def test_bad_arrival_calendar_date_is_rejected(self):
        statuses = {}
        with self.assertLogs(updater.log, level="WARNING"):
            rows = updater.collect_source("bad arrival", lambda: [sailing(ankomstdatum="2026-10-20")], ANCHOR, ANCHOR, statuses)
        self.assertEqual(rows, [])
        self.assertEqual(statuses["bad arrival"]["status"], "partial")

    def test_main_survives_outage_and_applies_authoritative_empty_days(self):
        class Batch(list):
            coverage = [coverage()]
        original = {"schema": schema(), "meta": {}, "avgangar_datum": {
            "2026-10-21": {"Tallink Silja:Stockholm→Tallinn:17:30": {
                "anktid": "11:00", "ankomstdatum": "2026-10-22",
                "kalltyp": ROUTE.source_type, "kalldetalj": ROUTE.source_detail,
            }},
        }}
        with tempfile.TemporaryDirectory() as directory, contextlib.ExitStack() as stack:
            target = Path(directory) / "farjor_data.json"
            target.write_text(json.dumps(original), encoding="utf-8")
            stack.enter_context(patch.object(updater, "DATA_FILE", target))
            stack.enter_context(patch.object(updater, "apply_verified_schema_overrides", side_effect=lambda value: value))
            stack.enter_context(patch.object(updater.sys, "argv", ["update_fartyg.py", ANCHOR.isoformat()]))
            stack.enter_context(patch.dict("os.environ", {"FERRY_ENABLE_VIKING_API": "false", "FERRY_PUBLIC_ANCHOR_DATE": ""}))
            for module in (updater.dfds, updater.finn, updater.stena, updater.ttline, updater.polferries, updater.molslinjen):
                stack.enter_context(patch.object(module, "fetch_all", return_value=[]))
            stack.enter_context(patch.object(updater.dfds, "fetch_all", side_effect=TimeoutError("offline")))
            stack.enter_context(patch.object(updater.tl, "fetch_all", return_value=Batch()))
            with self.assertLogs(updater.log):
                updater.main()
            result = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(result["avgangsinstanser"]["2026-10-21"], [])
            self.assertEqual(result["avgangsinstanser"]["2026-10-23"], [])
            self.assertEqual(len(result["avgangsinstanser"]["2026-10-24"]), 1)
            self.assertEqual(result["meta"]["source_refresh"]["DFDS"]["status"], "error")
            self.assertEqual(result["meta"]["source_refresh"]["Tallink Silja"]["status"], "ok")
            self.assertFalse(list(Path(directory).glob("*.tmp")))
            # A subsequent outage must not resurrect these officially empty
            # dates from the weekly fallback, nor erase retained exact rows.
            updater.tl.fetch_all.return_value = []
            with self.assertLogs(updater.log):
                updater.main()
            after_outage = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(after_outage["avgangsinstanser"]["2026-10-21"], [])
            self.assertEqual(after_outage["avgangsinstanser"]["2026-10-23"], [])
            self.assertEqual(len(after_outage["avgangsinstanser"]["2026-10-24"]), 1)
            self.assertTrue(after_outage["meta"]["source_coverage"]["Tallink Silja"])

    def test_retained_coverage_does_not_erase_cached_departures_during_outage(self):
        first = updater.retain_verified_coverage({}, {"source": {"coverage": [coverage()], "checked_at": "2026-10-21T10:00:00Z"}}, ANCHOR, date(2026, 10, 23))
        second = updater.retain_verified_coverage({"meta": {"source_coverage": first}}, {"source": {"status": "error"}}, ANCHOR, date(2026, 10, 23))
        self.assertEqual(second, first)
        # Only fresh coverage is passed to cache replacement; retained periods
        # clear weekly templates separately, preserving known exact departures.
        self.assertEqual(updater.combine_cached_and_fresh_sailings([sailing()], [], set()), [sailing()])


if __name__ == "__main__":
    unittest.main()
