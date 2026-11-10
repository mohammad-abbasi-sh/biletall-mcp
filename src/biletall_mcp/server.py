"""MCP server: unofficial read-only access to biletall.com bus & flight tickets."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from . import http as _http
from . import routes as _R

mcp = FastMCP("biletall-mcp")

INSTRUCTIONS = """\
Unofficial read-only MCP server for biletall.com, Türkiye's bus &
flight ticket search (an Obilet white-label). Data comes from the
site's server-rendered SEO pages — no login, no API key, no session
cookies. City names are slugified (İstanbul -> istanbul, Eskişehir
-> eskisehir, "İstanbul Avrupa" -> istanbul; multi-word locations
use underscores, e.g. Antakya Hatay -> antakya_hatay); use
biletall_search_locations to discover slugs (1,726 platform
locations). Bus route: /otobus-bileti/<from>-<to> — today's
departures (30 cheapest journeys listed) with a summary (cheapest
price, journey count, cheapest/most-active company, duration,
route rating 0-10). Flight route: /ucak-bileti/<from>-<to> —
cheapest flights across the coming days (10 listed, each with its
own date, airline, airports + IATA codes, times, price). Popular
routes: the homepage / most-travelled list with from/to slugs and
prices. Prices are in Turkish Lira (TRY). Read-only; transport
uses Chrome TLS impersonation; requests are spaced ~0.8s apart.
Built by Mohammad Abbasi (mohammad-abbasi-sh) — https://almanibama.ir · https://mabbasi.ir — Turkey MCP
factory.\
"""


_SOURCE = "biletall.com"
_DISCLAIMER = "Unofficial read-only data from biletall.com; verify on the site before acting on it."


def _envelope() -> dict:
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": _SOURCE,
        "disclaimer": _DISCLAIMER,
    }


def _ok(payload: dict) -> str:
    return json.dumps({**_envelope(), **payload}, ensure_ascii=False)


def _err(e: Exception) -> str:
    return _ok({"error": str(e)})


def _validate_limit(limit: int, lo: int = 1, hi: int = 30) -> int:
    if not lo <= limit <= hi:
        raise ValueError(f"limit must be between {lo} and {hi}")
    return limit


def _slugs(from_city: str, to_city: str) -> tuple[str, str]:
    a, b = _R.slugify(from_city), _R.slugify(to_city)
    if a == b:
        raise ValueError("from_city and to_city must be different cities")
    return a, b


@mcp.tool()
def biletall_search_locations(query: str, limit: int = 20) -> str:
    """Search biletall.com locations (cities, towns) by name.
    query: e.g. "Ankara", "İstanbul", "İzmir", "Bodrum". Searches the
    platform location inventory offline (1,726 slugs from the site's
    sitemap; major cities carry correct Turkish spelling). Returns
    slug, name and the location's biletall.com URL per match. Use the
    slug (or the city name) in the bus/flight route tools."""
    try:
        if not query or not query.strip():
            raise ValueError("query must not be empty")
        _validate_limit(limit, 1, 50)
        rows = _R.search_locations(query.strip(), limit=limit)
    except (ValueError, _http.BiletallError) as e:
        return _err(e)
    return _ok({"query": query.strip(), "count": len(rows), "locations": rows})


@mcp.tool()
def biletall_bus_route(from_city: str, to_city: str, limit: int = 10) -> str:
    """Cheapest bus journeys for one route, today. from_city / to_city:
    Turkish city names (e.g. "İstanbul" -> "Ankara") or slugs.
    limit 1..30. Returns the route summary (cheapest price in TRY,
    journey count, cheapest/most-active company, duration, route
    rating) plus the cheapest journeys (company, bus type, origin
    city + station, destination city + station, price in TRY,
    departure/arrival times). The page lists today's departures."""
    try:
        _validate_limit(limit)
        a, b = _slugs(from_city, to_city)
        html_text = _http.fetch_bus_route_html(a, b)
        data = _R.parse_bus_route(html_text, a, b)
    except (ValueError, _http.BiletallError) as e:
        return _err(e)
    return _ok({
            "from_city": from_city,
            "to_city": to_city,
            "from_slug": a,
            "to_slug": b,
            "summary": data["summary"],
            "total_listed": len(data["journeys"]),
            "count": min(limit, len(data["journeys"])),
            "journeys": data["journeys"][:limit],
        })


@mcp.tool()
def biletall_flight_route(from_city: str, to_city: str, limit: int = 10) -> str:
    """Cheapest flights for one route. from_city / to_city: Turkish
    city names (e.g. "İstanbul" -> "Ankara") or slugs. limit 1..10.
    Returns the route summary (cheapest price in TRY, cheapest/most-
    active airline, flight count, duration, distance) plus the
    cheapest flights, each with its own date (ISO + Turkish),
    airline, origin/destination airports with IATA codes,
    departure/arrival times and price in TRY. Dates span the coming
    days — the page lists the cheapest per day."""
    try:
        _validate_limit(limit, 1, 10)
        a, b = _slugs(from_city, to_city)
        html_text = _http.fetch_flight_route_html(a, b)
        data = _R.parse_flight_route(html_text, a, b)
    except (ValueError, _http.BiletallError) as e:
        return _err(e)
    return _ok({
            "from_city": from_city,
            "to_city": to_city,
            "from_slug": a,
            "to_slug": b,
            "summary": data["summary"],
            "total_listed": len(data["flights"]),
            "count": min(limit, len(data["flights"])),
            "flights": data["flights"][:limit],
        })


@mcp.tool()
def biletall_price_stats(from_city: str, to_city: str) -> str:
    """Price statistics for a bus route (today): journey count, min /
    median / mean / max ticket price in TRY across the 30 cheapest
    journeys the site lists, company count, and the cheapest price
    per company. from_city / to_city: Turkish city names or slugs."""
    try:
        a, b = _slugs(from_city, to_city)
        html_text = _http.fetch_bus_route_html(a, b)
        data = _R.parse_bus_route(html_text, a, b)
        stats = _R.price_stats(data["journeys"])
    except (ValueError, _http.BiletallError) as e:
        return _err(e)
    return _ok({
            "from_city": from_city,
            "to_city": to_city,
            "from_slug": a,
            "to_slug": b,
            "summary": data["summary"],
            **stats,
        })


@mcp.tool()
def biletall_popular_routes(limit: int = 15) -> str:
    """Most-travelled bus routes on biletall.com with prices:
    route name, from/to slugs, cheapest price in TRY and the route
    URL. limit 1..30. Source: the homepage / /otobus-seferleri
    most-travelled list."""
    try:
        _validate_limit(limit)
        html_text = _http.fetch_home_html()
        rows = _R.parse_popular_routes(html_text)
    except (ValueError, _http.BiletallError) as e:
        return _err(e)
    return _ok({"count": min(limit, len(rows)), "routes": rows[:limit]})


@mcp.tool()
def biletall_health() -> str:
    """Check whether biletall.com is reachable right now.

    Returns status ok (HTTP 200), blocked (HTTP 403/429 — bot wall or
    rate limit) or error, plus the HTTP status and the probed URL.
    One polite request; it does not fetch any listings."""
    return _ok(_http.health_check())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
