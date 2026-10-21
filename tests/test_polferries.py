"""Regression cases for two-digit Polferries section ids and cancelled dates."""
import unittest
from calendar import monthrange
from types import SimpleNamespace
from unittest.mock import patch

import requests
import polferries_scraper as scraper


def table(section, month, year, route, vessel='MAZ', dep='20:30 - 03:00*'):
    ident = f'r{section}{month}{year}'
    month_name = ('January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November', 'December')[month - 1]
    days = monthrange(year, month)[1]
    headers = ''.join(f'<th>{day}</th>' for day in range(1, days + 1))
    cells = '<td>' + vessel + '</td>' + '<td></td>' * (days - 1)
    return (
        f"<a href='#{ident}'>{month_name}<br>{year}</a>"
        f'<div id="{ident}" class="tab-pane fade"><table class="rozklad-tabela">'
        f'<tr><th>Departure - Arrival</th>{headers}</tr>'
        f'<tr><th>{route}</th>' + '<td>Mo</td>' * days + '</tr>'
        f'<tr><td>{dep}</td>{cells}</tr></table></div>'
    )


class PolferriesTests(unittest.TestCase):
    def test_two_digit_section_id_keeps_october_and_january(self):
        page = table(10, 10, 2026, 'Trelleborg - Świnoujście') + table(10, 1, 2027, 'Trelleborg - Świnoujście')
        blocks = scraper._table_blocks(page)
        self.assertEqual([(month, year) for month, year, _ in blocks], [(10, 2026), (1, 2027)])
        rows = [row for month, year, body in blocks for row in scraper._parse_table(month, year, body, 'url', 'detail')]
        self.assertEqual([row['date'] for row in rows], ['2026-10-01', '2027-01-01'])
        self.assertEqual(rows[0]['ankomstdatum'], '2026-10-02')
        self.assertEqual(rows[0]['fartyg'], 'Mazovia')

    def test_karlshamn_and_nynashamn_use_actual_published_vessel(self):
        for section, route, code, vessel in (
            (11, 'Gdańsk - Karlshamn', 'SKA', 'Skania'),
            (12, 'Karlshamn - Gdańsk', 'COP', 'Copernicus'),
            (1, 'Gdańsk - Nynäshamn', 'NS', 'Nova Star'),
            (2, 'Nynäshamn - Gdańsk', 'WAW', 'Wawel'),
        ):
            page = table(section, 10, 2026, route, code)
            month, year, body = scraper._table_blocks(page)[0]
            rows = scraper._parse_table(month, year, body, 'url', 'detail')
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['fartyg'], vessel)
            self.assertEqual((rows[0]['avghamn'], rows[0]['ankhamn']), tuple(route.split(' - ')))

    def test_complete_empty_month_declares_authoritative_coverage(self):
        response = SimpleNamespace(text=table(12, 10, 2026, 'Karlshamn - Gdańsk', ''), raise_for_status=lambda: None)
        with patch.object(scraper.requests, 'get', return_value=response):
            batch = scraper._fetch_timetable(scraper.SOURCE_URL_GH, scraper.SOURCE_DETAIL_GH)
        self.assertEqual(batch, [])
        self.assertEqual(batch.coverage[0]['date_from'], '2026-10-01')
        self.assertEqual(batch.coverage[0]['date_to'], '2026-10-31')
        self.assertEqual(batch.coverage[0]['avghamn'], 'Karlshamn')

    def test_network_failure_and_malformed_page_never_clear_published_data(self):
        with patch.object(scraper.requests, 'get', side_effect=requests.Timeout('unavailable')):
            batch = scraper._fetch_timetable('url', 'detail')
        self.assertEqual(batch.coverage, [])

    def test_truncated_or_unrecognised_data_rows_never_declare_empty_coverage(self):
        valid = table(12, 10, 2026, 'Karlshamn - Gdańsk', '')
        for page in (valid.replace('<td></td></tr></table>', '</tr></table>'),
                     valid.replace('20:30 - 03:00*', 'Temporarily unavailable')):
            response = SimpleNamespace(text=page, raise_for_status=lambda: None)
            with patch.object(scraper.requests, 'get', return_value=response):
                batch = scraper._fetch_timetable('url', 'detail')
            self.assertEqual(batch, [])
            self.assertEqual(batch.coverage, [])
        response = SimpleNamespace(text='<html>Maintenance</html>', raise_for_status=lambda: None)
        with patch.object(scraper.requests, 'get', return_value=response):
            batch = scraper._fetch_timetable('url', 'detail')
        self.assertEqual(batch.coverage, [])

    def test_full_fetch_retains_coverage_from_every_source(self):
        batch = scraper.SailingBatch([{'date': '2026-10-01'}], [{'date_from': '2026-10-01'}])
        with patch.object(scraper, '_fetch_timetable', return_value=batch):
            combined = scraper.fetch_all()
        self.assertEqual(len(combined), 4)
        self.assertEqual(len(combined.coverage), 4)


if __name__ == '__main__':
    unittest.main()
