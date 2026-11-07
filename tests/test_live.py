"""Live tests for biletall_mcp — real requests to biletall.com.

Requires network + Chrome TLS impersonation (curl-cffi). The server
is polite by design (~0.8s between requests), so this file takes
~10s. Run: python -m unittest discover -s tests -v

Prices change during the day; tests assert structure and sane ranges,
not exact prices. Bus route pages list today's departures; flight
pages list the cheapest flights across the coming days.
"""
import json
import unittest

from biletall_mcp import http as H
from biletall_mcp import routes as R


class TestLiveBusRoute(unittest.TestCase):
    def test_istanbul_ankara(self):
        html_text = H.fetch_bus_route_html("istanbul", "ankara")
        data = R.parse_bus_route(html_text, "istanbul", "ankara")
        self.assertGreater(len(data["journeys"]), 0)
        self.assertGreater(data["summary"]["cheapest_price_try"], 0)
        self.assertGreater(data["summary"]["journey_count"], 0)
        j = data["journeys"][0]
        self.assertIn("company", j)
        self.assertIn("price_try", j)
        self.assertIn("departure", j)
        self.assertIn("arrival", j)

    def test_unknown_route_404(self):
        with self.assertRaises(H.BiletallError):
            H.fetch_bus_route_html("xyzabc", "qwerty")


class TestLiveFlightRoute(unittest.TestCase):
    def test_istanbul_ankara(self):
        html_text = H.fetch_flight_route_html("istanbul", "ankara")
        data = R.parse_flight_route(html_text, "istanbul", "ankara")
        self.assertGreater(len(data["flights"]), 0)
        self.assertGreater(data["summary"]["cheapest_price_try"], 0)
        f = data["flights"][0]
        self.assertIn("airline", f)
        self.assertIn("date", f)
        self.assertIn("price_try", f)


class TestLivePopularRoutes(unittest.TestCase):
    def test_home(self):
        html_text = H.fetch_home_html()
        rows = R.parse_popular_routes(html_text)
        self.assertGreaterEqual(len(rows), 5)
        self.assertGreater(rows[0]["price_try"], 0)


class TestLiveServerTools(unittest.TestCase):
    """End-to-end: call the MCP tool functions and check JSON output."""

    def test_bus_route_tool(self):
        from biletall_mcp.server import biletall_bus_route

        out = json.loads(biletall_bus_route("İstanbul", "Ankara", limit=3))
        self.assertNotIn("error", out)
        self.assertEqual(out["count"], 3)
        self.assertEqual(len(out["journeys"]), 3)

    def test_flight_route_tool(self):
        from biletall_mcp.server import biletall_flight_route

        out = json.loads(biletall_flight_route("İstanbul", "Ankara", limit=2))
        self.assertNotIn("error", out)
        self.assertEqual(out["count"], 2)

    def test_price_stats_tool(self):
        from biletall_mcp.server import biletall_price_stats

        out = json.loads(biletall_price_stats("İstanbul", "Ankara"))
        self.assertNotIn("error", out)
        self.assertGreater(out["count"], 0)
        self.assertLessEqual(out["min_try"], out["max_try"])

    def test_same_city_error(self):
        from biletall_mcp.server import biletall_bus_route

        out = json.loads(biletall_bus_route("Ankara", "Ankara"))
        self.assertIn("error", out)


if __name__ == "__main__":
    unittest.main()
