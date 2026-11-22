"""Invariants for a daily note: no invented figures, venue branch, no verdict."""

from __future__ import annotations

import json
import re
import unittest
from datetime import datetime, timezone

from stock_analysis.report import ReportError, build_report

NUMBER = re.compile(r"\d")
FORBIDDEN_PHRASES = (
    "potential purchase",
    "supporting entry",
    "price target",
    "strong buy",
    "guaranteed return",
    "you should buy",
    "you should sell",
)


def _base(**overrides: object) -> dict:
    payload = {
        "ticker": "aapl",
        "exchange": "NASDAQ",
        "horizon": "swing",
        "risk_tolerance": "moderate",
        "last_price": "",
    }
    payload.update(overrides)
    return payload


def _figures(report: dict) -> list[dict]:
    found = []
    for pillar in report["pillars"]:
        found.extend(pillar.get("figures", []))
    return found


def _blob(report: dict) -> str:
    return json.dumps(report)


class ReportTests(unittest.TestCase):
    def test_us_branch_uses_13f_form4_and_short_interest(self) -> None:
        report = build_report(_base())
        labels = [figure["label"] for figure in report["pillars"][2]["figures"]]
        self.assertIn("13F buyer-to-seller ratio and dollar flows", labels)
        self.assertIn("Form 4 open-market buys versus sells", labels)
        self.assertIn("Short interest as a percent of float", labels)
        self.assertIn("Days to cover", labels)
        fii = next(
            figure
            for figure in report["pillars"][2]["figures"]
            if figure["label"] == "Shareholding pattern and FII/DII"
        )
        self.assertEqual(fii["status"], "not_applicable")
        self.assertEqual(fii["value"], "unavailable")

    def test_india_branch_does_not_apply_13f(self) -> None:
        report = build_report(_base(ticker="reliance", exchange="NSE"))
        labels = [figure["label"] for figure in report["pillars"][2]["figures"]]
        self.assertIn("Shareholding pattern and stock-level FII/DII", labels)
        self.assertIn("Bulk and block deals", labels)
        self.assertIn("Exchange short or SLB", labels)
        self.assertNotIn("Form 4 open-market buys versus sells", labels)
        filing = next(
            figure
            for figure in report["pillars"][2]["figures"]
            if figure["label"] == "13F institutional filings"
        )
        self.assertEqual(filing["status"], "not_applicable")
        self.assertEqual(filing["value"], "unavailable")
        self.assertIn("not used for NSE or BSE", filing["note"])
        self.assertNotIn("13F", report["pillars"][2]["kicker"])

    def test_bse_matches_india_branch(self) -> None:
        report = build_report(_base(ticker="500325", exchange="BSE", horizon="long"))
        self.assertEqual(report["identity"]["venue_group"], "india")
        self.assertEqual(report["identity"]["currency"], "INR")

    def test_no_invented_numbers_without_a_typed_price(self) -> None:
        report = build_report(_base())
        for figure in _figures(report):
            self.assertNotRegex(figure["value"], NUMBER)
            self.assertIn(figure["value"], {"unavailable", "unknown"})
            if figure["status"] == "data_not_connected":
                self.assertIsNone(figure["source"])
                self.assertIsNone(figure["as_of"])
        self.assertEqual(report["sources_called"], [])

    def test_typed_price_is_the_only_numeric_value_and_is_not_a_quote(self) -> None:
        report = build_report(_base(last_price="189.40"))
        numeric = [figure for figure in _figures(report) if NUMBER.search(figure["value"])]
        self.assertEqual(len(numeric), 1)
        price = numeric[0]
        self.assertEqual(price["value"], "189.40")
        self.assertEqual(price["source"], "User input")
        self.assertIsNone(price["as_of"])
        self.assertEqual(price["status"], "user_supplied")
        self.assertIn("not a quote", price["note"])
        trend = next(figure for figure in _figures(report) if figure["label"] == "Daily trend")
        self.assertEqual(trend["status"], "series_missing")
        self.assertIn("series missing", report["pillars"][1]["interpretation"].lower())

    def test_blank_price_stays_unconnected(self) -> None:
        report = build_report(_base(last_price="  "))
        price = next(figure for figure in _figures(report) if figure["label"] == "Last price")
        self.assertEqual(price["status"], "data_not_connected")
        self.assertEqual(price["value"], "unavailable")

    def test_catalyst_is_unknown_not_a_date(self) -> None:
        report = build_report(_base(exchange="NYSE"))
        catalyst = next(figure for figure in _figures(report) if figure["label"] == "Catalysts")
        self.assertEqual(catalyst["value"], "unknown")
        blob = _blob(report).lower()
        self.assertNotRegex(
            blob,
            r"earnings (on|scheduled|date is|release on) |"
            r"(january|february|march|april|may|june|july|august|september|october|november|december) \d",
        )

    def test_horizon_and_risk_change_weight_not_the_close(self) -> None:
        swing = build_report(_base(horizon="swing", risk_tolerance="aggressive"))
        long = build_report(
            _base(horizon="long", risk_tolerance="conservative", exchange="NYSE")
        )
        self.assertNotEqual(swing["weighting"], long["weighting"])
        self.assertIn("1–4 weeks", swing["weighting"])
        self.assertIn("1–5+ years", long["weighting"])
        for report in (swing, long):
            titles = [group["title"] for group in report["pillars"][4]["groups"]]
            self.assertEqual(
                titles,
                ["Bullish factors", "Bearish risks and traps", "What to watch next"],
            )
            self.assertIn("buy, sell, or hold", report["weighting"])
            self.assertIn("buy, sell, or hold", report["disclaimer"])

    def test_close_bullets_cite_a_fact_or_a_gap(self) -> None:
        report = build_report(_base(exchange="NSE", last_price="₹1,234.50"))
        for group in report["pillars"][4]["groups"]:
            self.assertGreaterEqual(len(group["bullets"]), 2)
            for bullet in group["bullets"]:
                self.assertTrue(bullet["cites"])
                self.assertTrue(
                    bullet["cites"].startswith("Fact missing")
                    or bullet["cites"].startswith("Sourced fact")
                )
        watch_text = " ".join(
            bullet["text"] for bullet in report["pillars"][4]["groups"][2]["bullets"]
        )
        self.assertIn("1234.50", watch_text)
        self.assertNotIn("1234.50", report["pillars"][4]["groups"][0]["bullets"][0]["text"])

    def test_opening_does_not_lean_toward_a_purchase(self) -> None:
        report = build_report(_base())
        blob = _blob(report).lower()
        self.assertNotIn("potential purchase", blob)
        self.assertIn("does not recommend a purchase or a sale", report["opening"])
        for phrase in FORBIDDEN_PHRASES:
            self.assertNotIn(phrase, blob)

    def test_data_quality_and_freshness_are_always_present(self) -> None:
        report = build_report(_base(exchange="BSE", horizon="medium"))
        titles = [item["title"] for item in report["data_quality"]]
        self.assertEqual(
            titles,
            [
                "Reporting lag",
                "Later revisions",
                "Corporate-action adjustments",
                "Volume distortion",
            ],
        )
        self.assertGreaterEqual(len(report["freshness_windows"]), 6)
        for figure in _figures(report):
            self.assertTrue(figure["freshness"])

    def test_rejects_bad_inputs(self) -> None:
        cases = [
            {"ticker": " "},
            {"ticker": "../etc"},
            {"exchange": "LSE"},
            {"horizon": "daytrade"},
            {"risk_tolerance": "yolo"},
            {"last_price": "0"},
            {"last_price": "-5"},
            {"last_price": "five"},
            {"last_price": "1e2"},
        ]
        for override in cases:
            with self.subTest(override=override):
                with self.assertRaises(ReportError):
                    build_report(_base(**override))

    def test_generated_clock_is_labeled_as_not_a_market_timestamp(self) -> None:
        moment = datetime(2026, 11, 22, 6, 40, tzinfo=timezone.utc)
        report = build_report(_base(), now=moment)
        self.assertEqual(report["generated_at"], "2026-11-22T06:40:00Z")
        self.assertEqual(report["generated_note"], "Not a market as-of.")


if __name__ == "__main__":
    unittest.main()
