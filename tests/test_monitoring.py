import unittest
from datetime import datetime, timezone

from audit_source_links import check_url, classify_status, replace_data_urls, safe_redirect
from check_site_health import LIVE_SOURCE_NAMES, check_data, check_published, live_source_issues


class Response:
    def __init__(self, status=200, url="https://ferry.example/schedule/", history=()):
        self.status_code, self.url = status, url
        self.history = [Response(item) for item in history]
        self.headers = {"Content-Type": "text/html"}

    def close(self):
        pass


class LinkTests(unittest.TestCase):
    def test_blocks_and_api_method_are_not_dead_links(self):
        self.assertEqual(classify_status(403), "blocked_or_limited")
        self.assertEqual(classify_status(429), "blocked_or_limited")
        self.assertEqual(classify_status(404, api=True), "api_requires_request")
        self.assertEqual(classify_status(405, api=True), "api_requires_request")
        self.assertEqual(classify_status(500, api=True), "api_request_or_server_error")
        self.assertEqual(classify_status(404), "broken")

    def test_dead_link_requires_confirmation(self):
        responses = iter([Response(404), Response(200)])
        result = check_url("https://ferry.example/old/", get=lambda *a, **kw: next(responses), pause=lambda _: None)
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["confirmation_status"], 200)

    def test_safe_redirect_is_narrow(self):
        old = "https://ferry.example/schedule-old/"
        new = "https://ferry.example/schedule/"
        self.assertTrue(safe_redirect(old, new, [301], "text/html"))
        for target, chain in [(new, [302]), ("https://other.example/schedule/", [301]), ("https://ferry.example/en/", [301]), (new + "?session=x", [301]), ("http://ferry.example/schedule/", [301])]:
            self.assertFalse(safe_redirect(old, target, chain, "text/html"))
        self.assertFalse(safe_redirect(old + ".pdf", new, [301], "text/html"))
        self.assertFalse(safe_redirect("https://ferry.example/api/old", new, [301], "text/html"))
        self.assertFalse(safe_redirect(old + "?signature=abc", new + "?signature=abc", [301], "text/html"))
        self.assertFalse(safe_redirect(old, "https://ferry.example:8443/schedule/", [301], "text/html"))
        self.assertFalse(safe_redirect(old, "https://user@ferry.example/schedule/", [301], "text/html"))

    def test_construction_page_is_not_a_verified_timetable_replacement(self):
        old = "https://ferry.example/timetable"
        target = "https://ferry.example/en/route-network-page-under-construction"
        self.assertFalse(safe_redirect(old, target, [301], "text/html"))
        result = check_url(old, get=lambda *a, **kw: Response(200, target, [301]))
        self.assertEqual(result["status"], "needs_review")
        self.assertFalse(result["safe_redirect"])

    def test_link_replacement_never_alters_times_or_free_text(self):
        old, new = "https://ferry.example/old", "https://ferry.example/new"
        data = {"datum": "2026-10-21", "avgtid": "09:00", "kalla": old, "note": old, "nested": [{"source_url": old}]}
        result = replace_data_urls(data, {old: new})
        self.assertEqual(result["avgtid"], "09:00")
        self.assertEqual(result["kalla"], new)
        self.assertEqual(result["note"], old)
        self.assertEqual(result["nested"][0]["source_url"], new)


class PublicationTests(unittest.TestCase):
    now = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)

    def data(self, count=20):
        row = {"rederi": "DFDS", "avghamn": "Klaipėda", "ankhamn": "Karlshamn"}
        return {"meta": {"uppdaterad": "2026-10-21T11:00:00Z", "publiceringsfonster": "2026-09-21 till 2027-01-21"}, "avgangsinstanser": {"2026-10-22": [row.copy() for _ in range(count)]}}

    def test_stale_data_and_expired_window_stop_publication(self):
        data = self.data()
        self.assertEqual(check_data(data, self.now)[0], [])
        data["meta"]["uppdaterad"] = "2026-07-21T11:00:00Z"
        data["meta"]["publiceringsfonster"] = "2026-06-21 till 2026-08-21"
        self.assertEqual(len(check_data(data, self.now)[0]), 2)

    def test_large_loss_is_gated_against_actual_same_date_baseline(self):
        errors, _ = check_data(self.data(4), self.now, self.data(20))
        self.assertTrue(any("Kraftigt tapp" in error for error in errors))

    def test_even_a_single_removed_low_frequency_departure_is_gated(self):
        data = self.data(1)
        baseline = self.data(1)
        data["avgangsinstanser"]["2026-10-22"][0]["rederi"] = "Other"
        self.assertTrue(any("Kraftigt tapp" in error for error in check_data(data, self.now, baseline)[0]))

    def test_window_uses_the_swedish_date_at_utc_midnight_boundary(self):
        data = self.data()
        data["meta"]["uppdaterad"] = "2026-10-21T22:00:00Z"
        data["meta"]["publiceringsfonster"] = "2026-09-21 till 2026-11-04"
        now = datetime(2026, 10, 21, 23, tzinfo=timezone.utc)
        self.assertTrue(any("Publiceringsfönstret" in error for error in check_data(data, now)[0]))

    def test_all_source_failures_stop_publication_but_one_partial_can_publish(self):
        data = self.data()
        data["meta"]["source_refresh"] = {"DFDS": {"status": "error", "received_rows": 0}}
        self.assertTrue(check_data(data, self.now)[0])
        data["meta"]["source_refresh"]["TT-Line"] = {"status": "partial", "received_rows": 5, "accepted_rows": 4}
        self.assertFalse(check_data(data, self.now)[0])


if __name__ == "__main__":
    unittest.main()


class LiveSourceTests(unittest.TestCase):
    now = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)

    def healthy(self):
        return {"meta": {"source_refresh": {name: {"status": "ok", "accepted_rows": 10, "checked_at": "2026-10-21T11:00:00Z"} for name in LIVE_SOURCE_NAMES}}}

    def test_fallback_does_not_close_failed_or_disabled_live_collection(self):
        data = self.healthy()
        data["meta"]["source_refresh"]["TT-Line"]["status"] = "empty"
        data["meta"]["source_refresh"]["Viking Line"]["status"] = "disabled"
        self.assertEqual({row["source"] for row in live_source_issues(data, self.now)}, {"TT-Line", "Viking Line"})

    def test_fresh_success_closes_the_followup(self):
        self.assertEqual(live_source_issues(self.healthy(), self.now), [])

    def test_stale_or_unchecked_collection_remains_open(self):
        data = self.healthy()
        data["meta"]["source_refresh"]["Finnlines"]["checked_at"] = "2026-10-19T11:00:00Z"
        del data["meta"]["source_refresh"]["DFDS"]
        self.assertEqual({row["source"] for row in live_source_issues(data, self.now)}, {"Finnlines", "DFDS"})
