"""Stdlib parsing for biletall.com server-rendered SEO pages.

Verified live 2026-11-07 against real pages (fixtures in tests/):
- Bus route /otobus-bileti/<from>-<to>: a summary table (cheapest
  ticket, journey count, cheapest company, duration, most active
  company, route rating) with schema.org AggregateOffer meta
  (lowPrice + offerCount), plus 30 <li itemtype=".../BusTrip">
  journeys (company, seat layout 2+1, origin city + station,
  destination city + station, price data-price="598,0000",
  departure/arrival times). Today's departures.
- Flight route /ucak-bileti/<from>-<to>: AggregateOffer meta +
  <strong> labels (cheapest flight, cheapest/most-active airline,
  flight count, duration, distance) plus 10 .flight-list-container
  blocks (airline, Turkish date "10 Kasım 2026 - Salı", price
  data-price, origin/dest airport names + hours, data-departure
  ISO date, IATA codes). Cheapest flights across the coming days.
- Homepage /: "Popüler Rotalarda Ucuz Otobüs Seferleri" — .route-link
  blocks (route slug, route text, price data-price) — and the
  "Tüm Şehirlere" city list.
- /otobus-seferleri: same popular-routes list ("En Çok Seyahat
  Edilen Güzergahlar").
- Unknown routes return HTTP 404 ("Sayfa bulunamadı") — surfaced
  as a clear error by http.py.

Prices are Turkish format: thousands dots, comma decimals
("1.620,0000" -> 1620.0). All money in TRY.
"""
from __future__ import annotations

import html
import re
import statistics

from . import locations as _LOC

_TR_MONTHS = {
    "Ocak": 1, "Şubat": 2, "Mart": 3, "Nisan": 4, "Mayıs": 5,
    "Haziran": 6, "Temmuz": 7, "Ağustos": 8, "Eylül": 9,
    "Ekim": 10, "Kasım": 11, "Aralık": 12,
}

_TR_UPPER_TO_LOWER = str.maketrans({
    "İ": "i", "I": "ı", "Ş": "ş", "Ğ": "ğ",
    "Ü": "ü", "Ö": "ö", "Ç": "ç",
})
_TR_LOWER_TO_ASCII = str.maketrans({
    "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c", "ı": "i",
})


def _tr_lower(s: str) -> str:
    """Turkish-aware lowercase (str.lower() mangles İ -> i + dot)."""
    return s.translate(_TR_UPPER_TO_LOWER).lower()


def slugify(name: str) -> str:
    """Turkish city name -> biletall URL slug.

    "İstanbul" -> "istanbul", "Eskişehir" -> "eskisehir",
    "İstanbul Avrupa" -> "istanbul" (route pages use the base city;
    Avrupa/Anadolu are search-form variants only),
    "Antakya Hatay" -> "antakya_hatay" (site uses underscores for
    multi-word locations).
    """
    s = _tr_lower((name or "").strip()).translate(_TR_LOWER_TO_ASCII)
    s = re.sub(r"\b(avrupa|anadolu)\b", "", s)
    s = re.sub(r"[\s\-]+", "_", s)
    s = re.sub(r"[^a-z0-9_]+", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        raise ValueError(f"cannot slugify city name {name!r}")
    return s


def _clean(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_price(raw: str | None) -> float | None:
    """Turkish price string -> float TRY ("1.620,0000" -> 1620.0)."""
    if raw is None:
        return None
    s = str(raw).strip().replace("TL", "").strip()
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _offer_meta(html_text: str) -> dict:
    """schema.org AggregateOffer <meta> lowPrice / offerCount."""
    out: dict = {}
    m = re.search(r'itemprop="lowPrice" content="([\d.,]+)"', html_text)
    if m:
        out["low_price_try"] = parse_price(m.group(1))
    m = re.search(r'itemprop="offerCount" content="(\d+)"', html_text)
    if m:
        out["offer_count"] = int(m.group(1))
    return out


# ---------------------------------------------------------------- bus route

_BUS_LI_RE = re.compile(
    r'<li[^>]*itemtype="http://schema\.org/BusTrip".*?</li>', re.S | re.I
)


def _parse_bus_journey(block: str) -> dict:
    row: dict = {}
    m = re.search(r'itemprop="provider".*?<meta itemprop="name" content="([^"]+)"', block, re.S)
    if m:
        row["company"] = html.unescape(m.group(1))
    m = re.search(r'class="seat".*?</svg>\s*([^<]+)</div>', block, re.S)
    if not m:
        m = re.search(r"([12]\+\d)", block)
    if m:
        row["bus_type"] = _clean(m.group(1))
    m = re.search(
        r"<div>\s*([^<]+?)<br\s*/>\s*<span itemprop=\"departureBusStop\".*?"
        r"<span itemprop=\"name\">([^<]+)</span>",
        block, re.S,
    )
    if m:
        row["origin_city"] = _clean(m.group(1))
        row["origin_station"] = _clean(m.group(2))
    m = re.search(
        r"<div>\s*([^<]+?)<br\s*/>\s*<span itemprop=\"arrivalBusStop\".*?"
        r"<span itemprop=\"name\">([^<]+)</span>",
        block, re.S,
    )
    if m:
        row["destination_city"] = _clean(m.group(1))
        row["destination_station"] = _clean(m.group(2))
    m = re.search(r'itemprop="lowPrice"[^>]*data-price="([\d.,]+)"', block)
    if m:
        row["price_try"] = parse_price(m.group(1))
    m = re.search(r'itemprop="departureTime">([^<]+)</div>', block)
    if m:
        row["departure"] = m.group(1).strip()
    m = re.search(r'itemprop="arrivalTime">\s*([^<]+?)\s*</div>', block)
    if m:
        row["arrival"] = m.group(1).strip()
    return {k: v for k, v in row.items() if v not in (None, "")}


def _bus_summary(html_text: str) -> dict:
    """Label -> value pairs from the summary table + offer meta."""
    out: dict = {}
    labels = re.findall(
        r'<div class="table-inner-row">([^<]+)</div>.*?'
        r'<div class="right[^>]*>(.*?)</div>',
        html_text, re.S,
    )
    for label, value in labels:
        out[_clean(label)] = _clean(value)
    meta = _offer_meta(html_text)
    summary: dict = {}
    if meta.get("low_price_try") is not None:
        summary["cheapest_price_try"] = meta["low_price_try"]
    elif out.get("En Uygun Bilet"):
        summary["cheapest_price_try"] = parse_price(out["En Uygun Bilet"])
    count = out.get("Sefer Sayısı")
    if count and count.isdigit():
        summary["journey_count"] = int(count)
    elif meta.get("offer_count") is not None:
        summary["journey_count"] = meta["offer_count"]
    if out.get("En Ucuz Firma"):
        summary["cheapest_company"] = out["En Ucuz Firma"]
    if out.get("En Aktif Firma"):
        summary["most_active_company"] = out["En Aktif Firma"]
    dur = next((v for k, v in out.items() if "Kaç Saat" in k), None)
    if dur:
        summary["duration"] = dur
    rating = out.get("Rota Puanı")
    if rating:
        try:
            summary["route_rating_10"] = round(float(rating.replace(",", ".")), 1)
        except ValueError:
            summary["route_rating"] = rating
    return summary


def parse_bus_route(html_text: str, from_slug: str, to_slug: str) -> dict:
    journeys = [
        _parse_bus_journey(b) for b in _BUS_LI_RE.findall(html_text)
    ]
    journeys = [j for j in journeys if j.get("price_try") is not None]
    # The page order is not strictly by price; cheapest first is the
    # tool's promise.
    journeys.sort(key=lambda j: j["price_try"])
    return {
        "from": from_slug,
        "to": to_slug,
        "url": f"https://www.biletall.com/otobus-bileti/{from_slug}-{to_slug}",
        "summary": _bus_summary(html_text),
        "journeys": journeys,
    }


# ---------------------------------------------------------------- flight route

def _parse_tr_date(raw: str) -> str | None:
    """'10 Kasım 2026 - Salı' -> '2026-11-10' (None if unparseable)."""
    m = re.match(r"\s*(\d{1,2})\s+(\S+)\s+(\d{4})", raw or "")
    if not m:
        return None
    month = _TR_MONTHS.get(m.group(2))
    if not month:
        return None
    return f"{int(m.group(3)):04d}-{month:02d}-{int(m.group(1)):02d}"


def _flight_summary(html_text: str) -> dict:
    # Labels live inside the info-graph area (before the "En Uygun" list);
    # take the text between each <strong> label and the next label.
    region_start = html_text.find('<div class="info-graph-content">')
    region_end = html_text.find("<h2>En Uygun", region_start)
    region = html_text[region_start:region_end if region_end > 0 else len(html_text)]
    strongs = list(re.finditer(r"<strong>([^<]+)</strong>", region))
    out: dict = {}
    for i, m in enumerate(strongs):
        label = _clean(m.group(1)).rstrip(":")
        seg_end = strongs[i + 1].start() if i + 1 < len(strongs) else len(region)
        value = _clean(region[m.end():seg_end]).lstrip(":").strip()
        if label and value:
            out[label] = value
    meta = _offer_meta(html_text)
    summary: dict = {}
    if meta.get("low_price_try") is not None:
        summary["cheapest_price_try"] = meta["low_price_try"]
    elif out.get("Biletall'daki En Ucuz Seyahat"):
        summary["cheapest_price_try"] = parse_price(
            out["Biletall'daki En Ucuz Seyahat"]
        )
    if out.get("En Ucuz Havayolu"):
        summary["cheapest_airline"] = out["En Ucuz Havayolu"]
    if out.get("En Aktif Havayolu"):
        summary["most_active_airline"] = out["En Aktif Havayolu"]
    if out.get("Uçuş Sayısı") and out["Uçuş Sayısı"].isdigit():
        summary["flight_count"] = int(out["Uçuş Sayısı"])
    elif meta.get("offer_count") is not None:
        summary["flight_count"] = meta["offer_count"]
    if out.get("Uçuş Süresi"):
        summary["duration"] = out["Uçuş Süresi"]
    if out.get("Uzaklık"):
        summary["distance"] = out["Uzaklık"]
    return summary


def _parse_flight(container: str) -> dict:
    row: dict = {}
    m = re.search(r'class="partner-info".*?<span class="text">([^<]+)</span>', container, re.S)
    if m:
        row["airline"] = _clean(m.group(1))
    m = re.search(r'class="date".*?>([^<]+)</div>', container, re.S)
    if m:
        raw_date = _clean(m.group(1))
        row["date_tr"] = raw_date
        iso = _parse_tr_date(raw_date)
        if iso:
            row["date"] = iso
    m = re.search(r'data-price="([\d.,]+)"', container)
    if m:
        row["price_try"] = parse_price(m.group(1))
    m = re.search(r'data-departure="(\d{4}-\d{2}-\d{2})"', container)
    if m:
        row.setdefault("date", m.group(1))
    m = re.search(r'data-origin-code="([A-Z]{3})"', container)
    if m:
        row["origin_code"] = m.group(1)
    m = re.search(r'data-destination-code="([A-Z]{3})"', container)
    if m:
        row["destination_code"] = m.group(1)
    # all route-element blocks in order (origin, destination)
    legs = re.findall(
        r'class="[^"]*route-element[^"]*".*?<span class="name">([^<]+)</span>'
        r'.*?<span class="min">([^<]+)</span>.*?<span class="hour">([^<]+)</span>',
        container, re.S,
    )
    if len(legs) >= 1:
        row["origin_airport"] = _clean(legs[0][0]) + " — " + _clean(legs[0][1])
        row["departure"] = legs[0][2].strip()
    if len(legs) >= 2:
        row["destination_airport"] = _clean(legs[1][0]) + " — " + _clean(legs[1][1])
        row["arrival"] = legs[1][2].strip()
    return {k: v for k, v in row.items() if v not in (None, "")}


def parse_flight_route(html_text: str, from_slug: str, to_slug: str) -> dict:
    containers = re.split(
        r'<div class="flight-list-container">', html_text
    )[1:]
    flights = [_parse_flight(c) for c in containers]
    flights = [f for f in flights if f.get("price_try") is not None]
    # Cheapest first (the page order mixes dates).
    flights.sort(key=lambda f: f["price_try"])
    return {
        "from": from_slug,
        "to": to_slug,
        "url": f"https://www.biletall.com/ucak-bileti/{from_slug}-{to_slug}",
        "summary": _flight_summary(html_text),
        "flights": flights,
    }


# ---------------------------------------------------------------- popular routes

_ROUTE_LINK_RE = re.compile(
    r'<div class="route-link">.*?<a href="/otobus-bileti/([^"]+)"[^>]*>'
    r'.*?<span class="route-text[^"]*"[^>]*>([^<]+)</span>'
    r'.*?<span class="[^"]*no-cache-price"[^>]*data-price="([\d.,]+)"',
    re.S,
)


def parse_popular_routes(html_text: str) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for href, text, price in _ROUTE_LINK_RE.findall(html_text):
        if href in seen:
            continue
        seen.add(href)
        parts = href.split("-")
        row = {
            "route": _clean(text),
            "from": parts[0] if parts else href,
            "to": parts[-1] if len(parts) > 1 else "",
            "price_try": parse_price(price),
            "url": f"https://www.biletall.com/otobus-bileti/{href}",
        }
        out.append(row)
    return out


# ---------------------------------------------------------------- locations

def display_name(slug: str) -> str:
    """Correct Turkish name for major cities, title-cased slug otherwise."""
    if slug in _LOC.PROPER_NAMES:
        return _LOC.PROPER_NAMES[slug]
    return " ".join(w.capitalize() for w in slug.replace("_", " ").split())


def search_locations(query: str, limit: int = 20) -> list[dict]:
    """Offline substring search over the platform location inventory.

    Matches on the slug and on the display name; exact matches first,
    then prefix, then substring. The route tools accept any Turkish
    city name (they slugify it) — this list is for discovery.
    """
    q = (query or "").strip()
    if not q:
        return []
    q_slug = slugify(q)
    q_low = _tr_lower(q)
    exact, prefix, sub = [], [], []
    for slug in _LOC.SLUGS:
        name = display_name(slug)
        name_low = _tr_lower(name)
        if slug == q_slug or name_low == q_low:
            exact.append(slug)
        elif slug.startswith(q_slug) or name_low.startswith(q_low):
            prefix.append(slug)
        elif q_slug in slug or q_low in name_low:
            sub.append(slug)
    rows = []
    for slug in exact + prefix + sub:
        rows.append({
            "slug": slug,
            "name": display_name(slug),
            "url": f"https://www.biletall.com/otobus-bileti/{slug}",
        })
        if len(rows) >= limit:
            break
    return rows


# ---------------------------------------------------------------- stats

def price_stats(journeys: list[dict]) -> dict:
    prices = sorted(j["price_try"] for j in journeys if j.get("price_try") is not None)
    if not prices:
        return {"count": 0}
    companies: dict[str, float] = {}
    for j in journeys:
        c = j.get("company")
        p = j.get("price_try")
        if c and p is not None and (c not in companies or p < companies[c]):
            companies[c] = p
    return {
        "count": len(prices),
        "min_try": prices[0],
        "median_try": round(statistics.median(prices), 2),
        "mean_try": round(sum(prices) / len(prices), 2),
        "max_try": prices[-1],
        "companies": len(companies),
        "cheapest_by_company": [
            {"company": c, "cheapest_try": p}
            for c, p in sorted(companies.items(), key=lambda kv: kv[1])
        ],
    }
