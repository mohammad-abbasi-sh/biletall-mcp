"""HTTP layer for biletall_mcp.

biletall.com (an Obilet white-label) serves its SEO route pages fully
server-rendered — no login, no API key, no session cookies needed.
Plain HTTP 200 with a browser UA (verified live 2026-11-07: homepage,
bus route, flight route, city and /otobus-seferleri pages). The
transport still uses curl-cffi chrome120 impersonation, the same proven
pattern as the other Turkey-factory servers, so a stricter bot check
does not break the server overnight. Requests are kept gentle (one at
a time, ~0.8s apart) and read-only.

Note: the two sibling lanes (teknosa.com, hepsiemlak.com) went behind
a Cloudflare JS challenge on the same day (2026-11-07) — both were
skipped per factory rules. biletall.com answers cleanly, which is why
it is the build.
"""
from __future__ import annotations

import time
from urllib.parse import quote

from curl_cffi import requests as _r

BASE = "https://www.biletall.com"
TIMEOUT = 30.0
MIN_INTERVAL = 0.8  # seconds between requests — be polite

_HEADERS = {
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

_last_fetch = 0.0


class BiletallError(RuntimeError):
    pass


def _get(url: str) -> str:
    global _last_fetch
    wait = MIN_INTERVAL - (time.monotonic() - _last_fetch)
    if wait > 0:
        time.sleep(wait)
    try:
        resp = _r.get(url, impersonate="chrome120", headers=_HEADERS, timeout=TIMEOUT)
    except Exception as e:
        raise BiletallError(f"network error fetching {url}: {e}") from e
    finally:
        _last_fetch = time.monotonic()
    if resp.status_code == 403:
        raise BiletallError(
            "biletall.com refused the request (HTTP 403, bot wall) — try again later"
        )
    if resp.status_code == 429:
        raise BiletallError(
            "biletall.com rate-limited the request (HTTP 429) — try again later"
        )
    if resp.status_code == 404:
        raise BiletallError(
            f"page not found (HTTP 404): {url} — check the city names/slugs"
        )
    if resp.status_code != 200:
        raise BiletallError(f"unexpected HTTP {resp.status_code} fetching {url}")
    return resp.text


def fetch_bus_route_html(from_slug: str, to_slug: str) -> str:
    """SEO bus route page: /otobus-bileti/<from>-<to> (today's journeys)."""
    return _get(f"{BASE}/otobus-bileti/{quote(from_slug)}-{quote(to_slug)}")


def fetch_flight_route_html(from_slug: str, to_slug: str) -> str:
    """SEO flight route page: /ucak-bileti/<from>-<to> (cheapest flights)."""
    return _get(f"{BASE}/ucak-bileti/{quote(from_slug)}-{quote(to_slug)}")


def fetch_home_html() -> str:
    return _get(f"{BASE}/")


def fetch_seferleri_html() -> str:
    """All-routes page: /otobus-seferleri (most-travelled routes list)."""
    return _get(f"{BASE}/otobus-seferleri")
