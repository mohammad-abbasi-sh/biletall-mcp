# biletall-mcp 🇹🇷

mcp-name: io.github.mohammad-abbasi-sh/biletall-mcp

Unofficial **read-only** MCP server for biletall.com, Türkiye's bus & flight ticket search — cheapest bus journeys for any route (today's departures, company, seat layout, stations, times, prices), cheapest flights (airline, airports + IATA codes, dates, times, prices), price statistics per route, most-travelled routes, and location search over 1,726 Turkish and international locations.

> Built by Mohammad Abbasi as part of the "Turkey MCP factory" (Sepehr-style pipeline). Not affiliated with biletall.com.

## For AI agents

Add to your MCP client config (stdio):

```json
{
  "mcpServers": {
    "biletall": {
      "command": "uvx",
      "args": ["biletall-mcp"]
    }
  }
}
```

Or run locally: `python -m biletall_mcp.server` (needs `mcp<2`, `curl-cffi`).

## Tools

| Tool | Description |
|------|-------------|
| `biletall_search_locations` | Search locations by name — `query` ("Ankara", "İstanbul", "Bodrum"); returns slug, Turkish name and biletall.com URL per match (offline search over the 1,726-location platform inventory) |
| `biletall_bus_route` | Cheapest bus journeys for one route, today — `from_city`, `to_city` (Turkish names or slugs, e.g. "İstanbul" → "Ankara"), `limit` 1..30; returns summary (cheapest price, journey count, cheapest/most-active company, duration, route rating) + journeys (company, bus type, origin city + station, destination city + station, price in TRY, departure/arrival times) |
| `biletall_flight_route` | Cheapest flights for one route — `from_city`, `to_city`, `limit` 1..10; returns summary (cheapest price, cheapest/most-active airline, flight count, duration, distance) + flights, each with its own date (ISO + Turkish), airline, origin/destination airports with IATA codes, times, price in TRY |
| `biletall_price_stats` | Price statistics for a bus route (today): count, min / median / mean / max ticket price in TRY across the 30 cheapest journeys, company count, cheapest price per company |
| `biletall_popular_routes` | Most-travelled bus routes with prices: route name, from/to slugs, cheapest price in TRY, route URL; `limit` 1..30 |

Example output (`biletall_bus_route` / İstanbul → Ankara):

```json
{"from_city": "İstanbul", "to_city": "Ankara", "summary":
 {"cheapest_price_try": 539.0, "journey_count": 719,
  "cheapest_company": "Yeşil Malatya Turizm",
  "most_active_company": "Metro Turizm", "duration": "6s 35dk",
  "route_rating_10": 3.9},
 "count": 2, "journeys": [
  {"company": "Niğde Aydoğanlar", "bus_type": "2+1",
   "origin_city": "İstanbul Avrupa", "origin_station": "Alibeyköy Otogarı",
   "destination_city": "Ankara", "destination_station": "Ankara (Aşti) Otogarı",
   "price_try": 598.0, "departure": "00:19", "arrival": "06:34"}, …]}
```

Example output (`biletall_flight_route` / İstanbul → Ankara):

```json
{"summary": {"cheapest_price_try": 1464.0, "cheapest_airline": "Pegasus",
  "most_active_airline": "THY", "flight_count": 14,
  "duration": "1Saat", "distance": "349 KM"},
 "flights": [{"airline": "Pegasus", "date": "2026-11-10",
  "date_tr": "10 Kasım 2026 - Salı", "price_try": 1459.99,
  "origin_code": "SAW", "destination_code": "ESB",
  "origin_airport": "İstanbul Anadolu — Sabiha Gökçen Havalimanı",
  "departure": "18:15",
  "destination_airport": "Ankara — Ankara Esenboğa Havalimanı",
  "arrival": "19:15"}, …]}
```

## How it works

biletall.com (an Obilet white-label) serves its SEO route pages fully server-rendered — no login, no API key, no session cookies. Bus route pages carry a summary table (cheapest ticket, journey count, cheapest company, duration, most active company, route rating) with a schema.org AggregateOffer meta block, plus 30 `<li itemtype="…/BusTrip">` journeys. Flight route pages carry the same summary shape plus 10 cheapest-flight blocks (airline, Turkish date, price `data-price`, airports + IATA codes, times). The homepage carries the 15 most-travelled routes with prices. City names are slugified (İstanbul → istanbul, Eskişehir → eskisehir; "İstanbul Avrupa" → istanbul since route pages use the base city; multi-word locations use underscores, e.g. Antakya Hatay → antakya_hatay). Unknown routes return HTTP 404 ("Sayfa bulunamadı"), surfaced as a clear error. Transport uses Chrome TLS impersonation (`curl-cffi`, `chrome120`); requests are spaced ~0.8s apart; everything is read-only.

Note: the two sibling lanes (teknosa.com, hepsiemlak.com) went behind a Cloudflare JS challenge on the same day this server was built (2026-11-07) and were skipped per factory rules — biletall.com answers cleanly, which is why it is the build.

## Install

```bash
uvx biletall-mcp        # run directly (needs uv)
# or
pip install biletall-mcp
biletall-mcp    # starts the MCP server on stdio
```

## Tests

```bash
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

Offline tests run on recorded fixtures (real pages fetched 2026-11-07); live tests hit biletall.com. 34/34 green at build time (26 offline + 8 live) plus an MCP stdio smoke test.

## Roadmap

- Date-specific bus search (the SEO pages show today's departures; a dated search needs the session-gated JSON API)
- Bus company pages (`/otobus-firmalari/<slug>`: company routes + ratings)
- Hotel search (the site has an Otel section)

## License

MIT — see [LICENSE](LICENSE).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
