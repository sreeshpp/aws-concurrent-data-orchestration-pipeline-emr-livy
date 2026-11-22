"""The desk serves the note and does not invent a feed."""

from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request

from stock_analysis.server import DeskHandler, ThreadingHTTPServer


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), DeskHandler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def test_home_and_health(self) -> None:
        with urllib.request.urlopen(self.url("/")) as response:
            page = response.read().decode("utf-8")
        self.assertIn("Fact Desk", page)
        self.assertIn("data not connected", page.lower())
        with urllib.request.urlopen(self.url("/api/health")) as response:
            health = json.load(response)
        self.assertEqual(health["market_data"], "not_connected")
        self.assertEqual(health["llm"], "not_called")

    def test_report_for_nse_has_no_connected_flow(self) -> None:
        payload = json.dumps(
            {
                "ticker": "RELIANCE",
                "exchange": "NSE",
                "horizon": "medium",
                "risk_tolerance": "conservative",
                "last_price": None,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.url("/api/report"),
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request) as response:
            note = json.load(response)
        self.assertEqual(note["identity"]["venue_group"], "india")
        self.assertEqual(note["sources_called"], [])
        connected = [
            figure["value"]
            for pillar in note["pillars"]
            if "figures" in pillar
            for figure in pillar["figures"]
            if figure["status"] == "data_not_connected"
        ]
        self.assertTrue(connected)
        self.assertTrue(all(value == "unavailable" for value in connected))

    def test_bad_input_is_a_client_error(self) -> None:
        payload = b'{"ticker": "", "exchange": "NYSE"}'
        request = urllib.request.Request(
            self.url("/api/report"),
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request)
        self.assertEqual(caught.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
