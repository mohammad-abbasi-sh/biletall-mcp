"""Offline tests for biletall_mcp.routes — recorded real biletall.com pages.

Fixtures are real pages fetched 2026-11-07 (curl-cffi chrome120):
- bus-route-istanbul-ankara.html: /otobus-bileti/istanbul-ankara
  (30 BusTrip journeys, summary: cheapest 539 TL, 719 journeys).
- flight-route-istanbul-ankara.html: /ucak-bileti/istanbul-ankara
  (10 cheapest flights, summary: cheapest 1464 TL, 14 flights).
- home.html: homepage (15 popular routes, first Manisa-Finike 1620 TL).
- seferleri.html: /otobus-seferleri (most-travelled routes list).
"""
import asyncio
import os
import unittest

from biletall_mcp import routes as R

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _read(name: str) -> str:
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return f.read()


class TestSlugify(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(R.slugify("İstanbul"), "istanbul")
        self.assertEqual(R.slugify("Ankara"), "ankara")
        self.assertEqual(R.slugify("Eskişehir"), "eskisehir")
        self.assertEqual(R.slugify("Şanlıurfa"), "sanliurfa")
        self.assertEqual(R.slugify("Çanakkale"), "canakkale")

    def test_all_caps_turkish(self):
        self.assertEqual(R.slugify("IĞDIR"), "igdir")
        self.assertEqual(R.slugify("KÜTAHYA"), "kutahya")

    def test_istanbul_variants(self):
        # Route pages use the base city; Avrupa/Anadolu are form variants.
        self.assertEqual(R.slugify("İstanbul Avrupa"), "istanbul")
        self.assertEqual(R.slugify("İstanbul Anadolu"), "istanbul")

    def test_multiword_underscore(self):
        self.assertEqual(R.slugify("Antakya Hatay"), "antakya_hatay")

    def test_empty(self):
        with self.assertRaises(ValueError):
            R.slugify("   ")


class TestParsePrice(unittest.TestCase):
    def test_turkish_format(self):
        self.assertEqual(R.parse_price("598,0000"), 598.0)
        self.assertEqual(R.parse_price("1.620,0000"), 1620.0)
        self.assertEqual(R.parse_price("1.463,00 TL"), 1463.0)
        self.assertEqual(R.parse_price("1459,9900"), 1459.99)

    def test_bad(self):
        self.assertIsNone(R.parse_price("n/a"))
        self.assertIsNone(R.parse_price(None))


class TestBusRouteParse(unittest.TestCase):
    def setUp(self):
        self.data = R.parse_bus_route(
            _read("bus-route-istanbul-ankara.html"), "istanbul", "ankara"
        )

    def test_summary(self):
        s = self.data["summary"]
        self.assertEqual(s["cheapest_price_try"], 539.0)
        self.assertEqual(s["journey_count"], 719)
        self.assertEqual(s["cheapest_company"], "Yeşil Malatya Turizm")
        self.assertEqual(s["most_active_company"], "Metro Turizm")
        self.assertEqual(s["duration"], "6s 35dk")
        self.assertEqual(s["route_rating_10"], 3.9)

    def test_journey_count(self):
        self.assertEqual(len(self.data["journeys"]), 30)

    def test_first_journey(self):
        j = self.data["journeys"][0]
        self.assertEqual(j["company"], "Niğde Aydoğanlar")
        self.assertEqual(j["bus_type"], "2+1")
        self.assertEqual(j["origin_city"], "İstanbul Avrupa")
        self.assertEqual(j["origin_station"], "Alibeyköy Otogarı")
        self.assertEqual(j["destination_city"], "Ankara")
        self.assertEqual(j["destination_station"], "Ankara (Aşti) Otogarı")
        self.assertEqual(j["price_try"], 598.0)
        self.assertEqual(j["departure"], "00:19")
        self.assertEqual(j["arrival"], "06:34")

    def test_prices_sorted_ascending(self):
        prices = [j["price_try"] for j in self.data["journeys"]]
        self.assertEqual(prices, sorted(prices))
        # The site-wide cheapest (summary) can be below the listed min:
        # only the 30 cheapest of 719 are listed.
        self.assertLessEqual(
            self.data["summary"]["cheapest_price_try"], min(prices)
        )

    def test_url(self):
        self.assertEqual(
            self.data["url"],
            "https://www.biletall.com/otobus-bileti/istanbul-ankara",
        )


class TestFlightRouteParse(unittest.TestCase):
    def setUp(self):
        self.data = R.parse_flight_route(
            _read("flight-route-istanbul-ankara.html"), "istanbul", "ankara"
        )

    def test_summary(self):
        s = self.data["summary"]
        self.assertEqual(s["cheapest_price_try"], 1464.0)
        self.assertEqual(s["cheapest_airline"], "Pegasus")
        self.assertEqual(s["most_active_airline"], "THY")
        self.assertEqual(s["flight_count"], 14)
        self.assertEqual(s["duration"], "1Saat")
        self.assertEqual(s["distance"], "349 KM")

    def test_flight_count(self):
        self.assertEqual(len(self.data["flights"]), 10)

    def test_first_flight(self):
        f = self.data["flights"][0]
        self.assertEqual(f["airline"], "Pegasus")
        self.assertEqual(f["date"], "2026-11-10")
        self.assertEqual(f["date_tr"], "10 Kasım 2026 - Salı")
        self.assertEqual(f["price_try"], 1459.99)
        self.assertEqual(f["origin_code"], "SAW")
        self.assertEqual(f["destination_code"], "ESB")
        self.assertEqual(f["departure"], "18:15")
        self.assertEqual(f["arrival"], "19:15")
        self.assertIn("Sabiha Gökçen", f["origin_airport"])
        self.assertIn("Esenboğa", f["destination_airport"])

    def test_tr_date(self):
        self.assertEqual(R._parse_tr_date("10 Kasım 2026 - Salı"), "2026-11-10")
        self.assertEqual(R._parse_tr_date("1 Ocak 2027 - Perşembe"), "2027-01-01")
        self.assertIsNone(R._parse_tr_date("tomorrow"))


class TestPopularRoutesParse(unittest.TestCase):
    def test_home(self):
        rows = R.parse_popular_routes(_read("home.html"))
        self.assertEqual(len(rows), 15)
        self.assertEqual(rows[0]["route"], "Manisa - Finike")
        self.assertEqual(rows[0]["from"], "manisa")
        self.assertEqual(rows[0]["to"], "finike")
        self.assertEqual(rows[0]["price_try"], 1620.0)

    def test_seferleri_page(self):
        rows = R.parse_popular_routes(_read("seferleri.html"))
        self.assertGreaterEqual(len(rows), 10)
        self.assertEqual(rows[0]["route"], "Manisa - Finike")


class TestSearchLocations(unittest.TestCase):
    def test_exact(self):
        rows = R.search_locations("Ankara")
        self.assertEqual(rows[0]["slug"], "ankara")
        self.assertEqual(rows[0]["name"], "Ankara")

    def test_turkish_diacritics(self):
        rows = R.search_locations("Şanlıurfa")
        self.assertEqual(rows[0]["slug"], "sanliurfa")
        rows = R.search_locations("sanliurfa")
        self.assertEqual(rows[0]["slug"], "sanliurfa")

    def test_istanbul(self):
        slugs = [r["slug"] for r in R.search_locations("istanbul")]
        self.assertIn("istanbul", slugs)

    def test_empty_and_miss(self):
        self.assertEqual(R.search_locations(""), [])
        self.assertEqual(R.search_locations("zzzqqq"), [])

    def test_inventory_size(self):
        from biletall_mcp.locations import SLUGS

        self.assertEqual(len(SLUGS), 1726)


class TestPriceStats(unittest.TestCase):
    def test_stats(self):
        data = R.parse_bus_route(
            _read("bus-route-istanbul-ankara.html"), "istanbul", "ankara"
        )
        stats = R.price_stats(data["journeys"])
        self.assertEqual(stats["count"], 30)
        self.assertEqual(stats["min_try"], 598.0)
        self.assertEqual(stats["max_try"], 1150.0)
        self.assertEqual(stats["median_try"], 799.5)
        self.assertEqual(stats["cheapest_by_company"][0]["company"], "Niğde Aydoğanlar")

    def test_empty(self):
        self.assertEqual(R.price_stats([]), {"count": 0})


class TestServerToolsRegistered(unittest.TestCase):
    def test_five_tools(self):
        from biletall_mcp.server import mcp

        tools = asyncio.run(mcp.list_tools())
        names = sorted(t.name for t in tools)
        self.assertEqual(
            names,
            [
                "biletall_bus_route",
                "biletall_flight_route",
                "biletall_popular_routes",
                "biletall_price_stats",
                "biletall_search_locations",
            ],
        )


if __name__ == "__main__":
    unittest.main()
