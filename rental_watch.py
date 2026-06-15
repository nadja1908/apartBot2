#!/usr/bin/env python3
"""
Monitor za nove stanove na listama agencija.
- Čuva vidljene ID-jeve u state.json
- Na novi oglas: konzola + opciono e-pošta (SMTP) + opciono Telegram

Instalacija: pip install -r requirements.txt
  zatim (za Woonzeker): python -m playwright install chromium
Pokretanje: python rental_watch.py
  probni mejl: python rental_watch.py --test-email
  probni Telegram: python rental_watch.py --test-telegram
  dijagnostika: python rental_watch.py --diagnose
  ili kontinuirano: python rental_watch.py --watch 300
"""

from __future__ import annotations

import argparse
import json
import os
import re
import smtplib
import sys
import time
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

_ROOT = Path(__file__).resolve().parent
try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")
except ImportError:
    pass

STATE_FILE = _ROOT / "state.json"
LAST_STATE_FILE = _ROOT / "last_state.json"
STATE_VERSION = 2
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_NO_HREF: re.Pattern[str] = re.compile("$^")


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    listing_href_pattern: re.Pattern[str]
    list_container_selector: str = ""
    fetch_mode: str = "http"
    # Predak-kartica (npr. "object" ili "item-listing-wrap") + filteri ispod
    listing_card_class: str = ""
    skip_if_card_contains_class: str = ""
    skip_if_label_status_equals: str = ""
    # If True, keep query string when normalizing listing URLs for this source
    preserve_query: bool = False


SOURCES: list[Source] = [
    Source(
        name="Rent Valley",
        url="https://rentvalley.nl/en/listings/",
        listing_href_pattern=re.compile(r"/en/listings/.+-den-haag\.html$", re.I),
    ),
    Source(
        name="Woonzeker Den Haag (filter)",
        url="https://woonzeker.com/aanbod/s-gravenhage?order=stage&page=1&filter=location:Den+Haag|price:428-1522|living_area:11-61",
        listing_href_pattern=_NO_HREF,
        fetch_mode="woonzeker_nuxt",
    ),
    Source(
        name="Woonzeker Den Haag (filter page 2)",
        url="https://woonzeker.com/aanbod/s-gravenhage?order=stage&page=2&filter=location:Den+Haag",
        listing_href_pattern=_NO_HREF,
        fetch_mode="woonzeker_nuxt",
    ),
    Source(
        name="Rental Rotterdam Den Haag (max €1500)",
        url=(
            "https://www.rentalrotterdam.nl/woningaanbod/huur/den-haag"
            "?locationofinterest=Den%20Haag"
            "&moveunavailablelistingstothebottom=true"
            "&pricerange.maxprice=1500"
        ),
        listing_href_pattern=re.compile(
            r"/woningaanbod/huur/den-haag/[^/]+/[^/]+$", re.I
        ),
        listing_card_class="object",
        skip_if_card_contains_class="rented",
    ),
    Source(
        name="HAYMAN Rentals",
        url="https://haymanrentals.nl/woningaanbod/",
        listing_href_pattern=re.compile(r"/aanbod/[^/]+/?$", re.I),
        listing_card_class="item-listing-wrap",
        skip_if_label_status_equals="verhuurd",
    ),
    Source(
        name="Trechousing Rent",
        url="https://www.trechousing.nl/en-gb/residential-listings/rent",
        listing_href_pattern=re.compile(r"/en-gb/residential-listings/rent/.+/.+", re.I),
    ),
    Source(
        name="Kamernet Den Haag",
        url="https://kamernet.nl/en/for-rent/apartment-den-haag?radius=5&minSize=0&maxRent=15",
        listing_href_pattern=re.compile(r"^/en/for-rent/.*", re.I),
    ),
    Source(
        name="Immovita",
        url="https://immovita.nl/en/aanbod/#",
        listing_href_pattern=re.compile(r"/aanbod/.*", re.I),
        fetch_mode="playwright",
        preserve_query=True,
    ),
    Source(
        name="Rotterdam Apartments",
        url="https://rotterdamapartments.com/en/for-rent",
        listing_href_pattern=re.compile(r"/en/for-rent/.+", re.I),
    ),
    Source(
        name="Avenir Vastgoed",
        url="https://www.avenirvastgoed.com/aanbod/huurwoningen",
        listing_href_pattern=re.compile(r"/aanbod/.*", re.I),
    ),
    Source(
        name="Expat Rentals Holland",
        url="https://www.expatrentalsholland.com/offer/in/den+haag",
        listing_href_pattern=re.compile(r"/offer/in/den\+haag.*", re.I),
    ),
    Source(
        name="Homey Housing",
        url="https://homeyhousing.com/woningaanbod/",
        listing_href_pattern=re.compile(r"/woningaanbod.*", re.I),
        fetch_mode="playwright",
    ),
    Source(
        name="Frisiamakelaars",
        url="https://frisiamakelaars.nl/wonen/aanbod?buy_rent=rent&order_by=created_at-desc&page=1",
        listing_href_pattern=re.compile(r"/wonen/aanbod.*", re.I),
        fetch_mode="playwright",
    ),
    Source(
        name="Karens Real Estate",
        url="https://www.karensrealestate.nl/woningaanbod?offer=any",
        listing_href_pattern=re.compile(r"/woningaanbod.*", re.I),
        fetch_mode="playwright",
    ),
    Source(
        name="WoonCompany",
        url="https://wooncompany.nl/woningen/?type=huur&plaats%5B%5D=denhaag&view=list&orderby=datumAangemaakt%3Adesc&isCommercieel=particulier",
        listing_href_pattern=re.compile(r"/woning(?:en)?/.*|/woningen/.*", re.I),
        fetch_mode="playwright",
    ),
    Source(
        name="BW Housing",
        url="https://www.bwhousing.nl/en/rental-listings",
        listing_href_pattern=re.compile(r"/en/rental-listings.*", re.I),
        fetch_mode="playwright",
    ),
    Source(
        name="Riemersma Real Estate",
        url="https://www.riemersmarealestate.nl/aanbod?offer=any&location=Den+Haag",
        listing_href_pattern=re.compile(r"/aanbod.*", re.I),
        fetch_mode="playwright",
    ),
    # Pararius and Funda sources removed per user request
    Source(
        name="Expata",
        url="https://www.expata.nl/woning-aanbod?type=huur",
        listing_href_pattern=re.compile(r"/woning-aanbod.*", re.I),
        fetch_mode="playwright",
    ),
]

# Blocklist substrings for sources (match against URL or source name)
BLOCKED_SOURCE_SUBSTRINGS = [
    # Block specific sources to stop Telegram notifications for them
    "verra",
    "lutya",
]


def _is_blocked_source(src: Source) -> bool:
    s = (src.url or "").lower()
    n = (src.name or "").lower()
    for sub in BLOCKED_SOURCE_SUBSTRINGS:
        if sub and (sub in s or sub in n):
            return True
    return False


# Note: keep the configured blocklist above; do not overwrite it here.

# Ensure SOURCES contains all originally configured sources
_orig_sources = SOURCES
SOURCES = list(_orig_sources)


def _purge_blocked_states() -> None:
    # Keep for compatibility but does nothing when BLOCKED_SOURCE_SUBSTRINGS is empty
    try:
        st = load_state()
        ls = load_last_state()
    except Exception:
        return
    changed = False
    for k in list(st.keys()):
        lk = k.lower()
        if any(sub in lk for sub in BLOCKED_SOURCE_SUBSTRINGS):
            try:
                del st[k]
                changed = True
            except Exception:
                pass
    for k in list(ls.keys()):
        lk = k.lower()
        if any(sub in lk for sub in BLOCKED_SOURCE_SUBSTRINGS):
            try:
                del ls[k]
                changed = True
            except Exception:
                pass
    if changed:
        try:
            save_state(st)
        except Exception:
            pass
        try:
            save_last_state(ls)
        except Exception:
            pass


# Purge blocked entries on startup
_purge_blocked_states()


def listing_key(href: str) -> str:
    """Stabilan ključ oglasa — čuva se u state.json (ne hash, da ne puca pri promeni koda)."""
    # Normalize obvious artifacts (backslashes, stray whitespace)
    href = (href or "").strip()
    href = href.replace("\\", "/")
    # Preserve explicit slug keys already stored in state (e.g. 'slug:bee...')
    if href.lower().startswith("slug:"):
        return href.lower()
    parsed = urlparse(href)
    if parsed.netloc.endswith("woonzeker.com"):
        from urllib.parse import parse_qs

        slug = parse_qs(parsed.query).get("slug", [""])[0]
        if slug:
            return f"slug:{slug}"
    path = (parsed.path or "").rstrip("/").lower()
    # Normalize path: remove common 'rented' markers that cause duplicates across checks
    # e.g. segments like 'verhuurd', 'verhuurd-xyz' — strip them before returning key
    try:
        segs = [s for s in path.split("/") if s]
        segs = [s for s in segs if not re.match(r'(?i)^(verhuurd|verhuur|verhuurd[-_]?.*)$', s)]
        path = ("/" + "/".join(segs)) if segs else ""
    except Exception:
        pass
    if path:
        return path
    return href.split("#")[0].split("?")[0].rstrip("/").lower()


def _is_legacy_hash_entry(value: str) -> bool:
    """Stari state je čuvao 16-char SHA skraćenice — više ih ne koristimo."""
    return len(value) == 16 and all(c in "0123456789abcdef" for c in value)


def _clean_state_keys(keys: set[str]) -> set[str]:
    out: set[str] = set()
    for k in keys:
        if _is_legacy_hash_entry(k):
            continue
        try:
            # Normalize stored keys: convert backslashes to slashes and
            # re-run listing_key normalizer so old variants match new ones.
            nk = listing_key(k.replace("\\", "/"))
            out.add(nk)
        except Exception:
            out.add(k.replace("\\", "/"))
    return out


def load_state() -> dict[str, list[str]]:
    if not STATE_FILE.is_file():
        return {}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        print(
            "state.json oštećen — ne šaljem poruke dok ne pokreneš: python rental_watch.py --sync-state",
            file=sys.stderr,
        )
        return {}

    if isinstance(data.get("sources"), dict):
        return {k: list(v) for k, v in data["sources"].items()}
    # stari format: { "Rent Valley": [...], ... }
    return {k: list(v) for k, v in data.items() if k != "version"}


def load_last_state() -> dict[str, list[str]]:
    if not LAST_STATE_FILE.is_file():
        return {}
    try:
        data = json.loads(LAST_STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if isinstance(data.get("sources"), dict):
        return {k: list(v) for k, v in data["sources"].items()}
    return {k: list(v) for k, v in data.items() if k != "version"}


def save_last_state(state: dict[str, list[str]]) -> None:
    tmp = LAST_STATE_FILE.with_suffix(".json.tmp")
    payload = json.dumps({"version": STATE_VERSION, "sources": state}, indent=2, ensure_ascii=False)
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(LAST_STATE_FILE)


def save_state(state: dict[str, list[str]]) -> None:
    tmp = STATE_FILE.with_suffix(".json.tmp")
    payload = json.dumps(
        {"version": STATE_VERSION, "sources": state},
        indent=2,
        ensure_ascii=False,
    )
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(STATE_FILE)


def _seen_keys_for_source(state: dict[str, list[str]], source_name: str) -> set[str]:
    return _clean_state_keys(set(state.get(source_name, [])))


def _source_has_only_legacy_hashes(state: dict[str, list[str]], source_name: str) -> bool:
    raw = state.get(source_name, [])
    return bool(raw) and all(_is_legacy_hash_entry(k) for k in raw)


def fetch_html(url: str, headers_override: dict | None = None) -> str:
    headers = {"User-Agent": USER_AGENT}
    if headers_override:
        headers.update(headers_override)
    with httpx.Client(
        headers=headers,
        follow_redirects=True,
        timeout=30.0,
    ) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.text


def extract_listing_hrefs(page_url: str, html: str, source: Source) -> set[str]:
    soup = BeautifulSoup(html, "html.parser")
    root = soup
    if source.list_container_selector:
        node = soup.select_one(source.list_container_selector)
        if node:
            root = node

    found: set[str] = set()

    # Extract URLs from JSON-LD structured data (some sites embed listing URLs here)
    try:
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
            except Exception:
                continue

            def walk(obj):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if isinstance(v, str) and (v.startswith("http") or v.startswith("/")):
                            full = urljoin(page_url, v)
                            if source.listing_href_pattern.search(urlparse(full).path) or source.listing_href_pattern.search(full):
                                if source.preserve_query:
                                    found.add(full.split("#")[0].rstrip("/"))
                                else:
                                    found.add(full.split("#")[0].split("?")[0].rstrip("/"))
                        else:
                            walk(v)
                elif isinstance(obj, list):
                    for it in obj:
                        walk(it)

            walk(data)
    except Exception:
        pass
    for a in root.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#"):
            continue
        if (
            source.listing_card_class
            and (
                source.skip_if_card_contains_class
                or source.skip_if_label_status_equals
            )
        ):
            card = None
            parent = a
            for _ in range(20):
                if parent is None:
                    break
                classes = parent.get("class") or []
                if source.listing_card_class in classes:
                    card = parent
                    break
                parent = parent.parent
            if card:
                skip_card = False
                if source.skip_if_card_contains_class and card.find(
                    class_=lambda c, needle=source.skip_if_card_contains_class: c
                    and needle in c
                ):
                    skip_card = True
                if source.skip_if_label_status_equals:
                    want = source.skip_if_label_status_equals.lower()
                    for el in card.select(".label-status"):
                        if el.get_text(strip=True).lower() == want:
                            skip_card = True
                            break
                if skip_card:
                    continue
        full = urljoin(page_url, href)
        path = urlparse(full).path or ""
        if source.listing_href_pattern.search(path) or source.listing_href_pattern.search(full):
            # Normalize but optionally preserve query string for sources that encode IDs in query params
            clean = full.split("#")[0]
            if source.preserve_query:
                norm = clean.rstrip("/")
            else:
                norm = clean.split("?")[0].rstrip("/")
            found.add(norm)
    return found


def _scan_html_for_urls(page_url: str, html: str, source: Source) -> set[str]:
    import itertools

    out: set[str] = set()
    # find absolute URLs
    for m in re.finditer(r"https?://[^\s\"'<>]+", html):
        try:
            full = m.group(0).strip().rstrip('.,;')
            if source.listing_href_pattern.search(urlparse(full).path) or source.listing_href_pattern.search(full):
                if source.preserve_query:
                    out.add(full.split('#')[0].rstrip('/'))
                else:
                    out.add(full.split('#')[0].split('?')[0].rstrip('/'))
        except Exception:
            pass

    # find path-like tokens starting with '/'
    for m in re.finditer(r"/[-A-Za-z0-9_@:%./~+?=&,#]+", html):
        try:
            token = re.sub(r"[.,;\"'()]+$", "", m.group(0))
            full = urljoin(page_url, token)
            path = urlparse(full).path or ''
            if source.listing_href_pattern.search(path) or source.listing_href_pattern.search(full):
                if source.preserve_query:
                    out.add(full.split('#')[0].rstrip('/'))
                else:
                    out.add(full.split('#')[0].split('?')[0].rstrip('/'))
        except Exception:
            pass

    return out


def _woonzeker_slugs_from_nuxt(data: object) -> set[str]:
    out: set[str] = set()

    def walk(obj: object, depth: int = 0) -> None:
        if depth > 28:
            return
        if isinstance(obj, dict):
            sid = obj.get("id")
            slug = obj.get("slug")
            title = obj.get("title")
            if (
                isinstance(slug, str)
                and slug
                and isinstance(sid, int)
                and slug != "woonzeker-relet"
                and title != "Woonzeker Relet"
            ):
                out.add(slug)
            for v in obj.values():
                walk(v, depth + 1)
        elif isinstance(obj, list):
            for it in obj:
                walk(it, depth + 1)

    walk(data)
    return out


def fetch_woonzeker_listing_urls(list_page_url: str) -> set[str]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise RuntimeError(
            "Za Woonzeker treba: pip install playwright && playwright install chromium"
        ) from e

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(list_page_url, wait_until="networkidle", timeout=120_000)
        page.wait_for_timeout(2500)
        raw = page.evaluate(
            "() => { try { return JSON.stringify(window.__NUXT__ ?? {}); } catch (e) { return '{}'; } }"
        )
        browser.close()

    data = json.loads(raw)
    slugs = _woonzeker_slugs_from_nuxt(data)
    parsed = urlparse(list_page_url)
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
    return {f"{base}?slug={quote(slug, safe='')}" for slug in slugs}


def fetch_playwright_html(url: str) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise RuntimeError(
            "Za Playwright treba: pip install playwright && python -m playwright install chromium"
        ) from e

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        # create a context that more closely resembles a real browser
        context = browser.new_context(
            user_agent=USER_AGENT,
            locale="en-US",
            viewport={"width": 1366, "height": 768},
        )
        # hide webdriver flag to reduce bot detection
        try:
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => false})")
        except Exception:
            pass
        # add common headers similar to a real browser
        try:
            context.set_extra_http_headers(
                {
                    "Referer": "https://www.pararius.com/",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                }
            )
        except Exception:
            pass

        page = context.new_page()
        page.goto(url, wait_until="networkidle", timeout=120_000)
        # small pause to let additional JS run
        page.wait_for_timeout(2000)
        content = page.content()
        try:
            context.close()
        except Exception:
            pass
        browser.close()
    return content


def fetch_bwhousing_urls(src: Source) -> set[str]:
    parsed = urlparse(src.url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    api = base + "/en/realtime-listings/consumer"
    try:
        txt = fetch_html(api)
        data = json.loads(txt)
    except Exception:
        return set()
    out = set()
    for item in data:
        u = item.get("url") or item.get("link") or item.get("slug")
        if not u:
            continue
        full = urljoin(base, u)
        out.add(full.split("#")[0].split("?")[0].rstrip("/"))
    return out


def _find_rts_query_url(html: str) -> str | None:
    m = re.search(r'(/rts/collections/public/[^"\']+/runtime/collection/[^"\']+/query-data[^"\']*)', html)
    if m:
        return m.group(1)
    return None


def fetch_rts_collection_urls(src: Source) -> set[str]:
    # Multiscreensite RTS: capture XHR responses while loading the page and parse any
    # JSON responses whose URL contains 'query-data'. This handles cases where the
    # endpoint is generated dynamically by client JS.
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return set()

    out = set()
    parsed = urlparse(src.url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"]) 
        ctx = browser.new_context(user_agent=USER_AGENT, locale="en-US")
        page = ctx.new_page()

        collected = []
        req_urls = set()

        def _on_response(resp):
            try:
                if "query-data" in resp.url and resp.headers.get("content-type", "").startswith("application/json"):
                    txt = resp.text()
                    collected.append((resp.url, txt))
            except Exception:
                pass

        def _on_request(req):
            try:
                if "query-data" in req.url:
                    req_urls.add(req.url)
            except Exception:
                pass

        page.on("response", _on_response)
        page.on("request", _on_request)
        try:
            page.goto(src.url, wait_until="networkidle", timeout=180_000)
            # longer wait to let deferred XHRs run
            page.wait_for_timeout(8000)
            page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(4000)
        except Exception:
            pass

        try:
            ctx.close()
        except Exception:
            pass
        browser.close()

    for url in sorted(req_urls):
        try:
            txt = fetch_html(url)
            collected.append((url, txt))
        except Exception:
            pass

    for url, txt in collected:
        try:
            data = json.loads(txt)
        except Exception:
            continue
        vals = data.get("values") if isinstance(data, dict) else None
        if not vals and isinstance(data, list):
            vals = data
        if not vals:
            continue
        for it in vals:
            if isinstance(it, dict):
                url_candidate = None
                if "data" in it and isinstance(it["data"], dict):
                    url_candidate = it["data"].get("url") or it["data"].get("link")
                url_candidate = url_candidate or it.get("url") or it.get("link")
                if url_candidate:
                    out.add(urljoin(base, url_candidate).split("#")[0].split("?")[0].rstrip("/"))
    return out


def listing_hrefs_for_source(src: Source) -> set[str]:
    parsed = urlparse(src.url)
    # Woonzeker special mode
    if src.fetch_mode == "woonzeker_nuxt":
        return fetch_woonzeker_listing_urls(src.url)

    # BW Housing exposes a JSON endpoint with listings — handle before generic Playwright/http
    if parsed.netloc.endswith("bwhousing.nl"):
        urls = fetch_bwhousing_urls(src)
        if urls:
            return urls

    # Multiscreensite RTS-based sites (Karens, Riemersma) use runtime collection query-data
    if "rts/collections/public" in src.url or "karensrealestate" in src.url or "riemersmarealestate" in src.url:
        urls = fetch_rts_collection_urls(src)
        if urls:
            return urls

    # If source explicitly requests Playwright, use it (after host-specific special cases)
    if src.fetch_mode == "playwright":
        html = fetch_playwright_html(src.url)
        found = extract_listing_hrefs(src.url, html, src)
        try:
            found |= _scan_html_for_urls(src.url, html, src)
        except Exception:
            pass
        return found

    # Pararius sometimes blocks non-browser clients; try with extra headers for that host
    if parsed.netloc.endswith("pararius.com"):
        extra = {
            "Referer": "https://www.pararius.com/",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        html = fetch_html(src.url, headers_override=extra)
    else:
        html = fetch_html(src.url)
    found = extract_listing_hrefs(src.url, html, src)
    try:
        found |= _scan_html_for_urls(src.url, html, src)
    except Exception:
        pass
    return found


def notify_console(source_name: str, hrefs: list[str]) -> None:
    print(f"\n*** NOVO na [{source_name}] ***")
    for h in hrefs:
        print(f"  {h}")


def _smtp_env_strip(value: str) -> str:
    return value.strip().strip('"').strip("'")


def _smtp_password_clean(value: str) -> str:
    return "".join(_smtp_env_strip(value).split())


def notify_telegram(text: str) -> bool:
    token = _smtp_env_strip(os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    chat_id = _smtp_env_strip(os.environ.get("TELEGRAM_CHAT_ID", ""))
    if not token or not chat_id:
        print(
            "Telegram nije poslat: u .env dodaj TELEGRAM_BOT_TOKEN i TELEGRAM_CHAT_ID.",
            file=sys.stderr,
        )
        return False
    api = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(
                api,
                json={
                    "chat_id": chat_id,
                    "text": text[:4000],
                    "disable_web_page_preview": False,
                },
            )
        if r.status_code >= 400:
            print(f"Telegram HTTP {r.status_code}: {r.text}", file=sys.stderr)
            return False
        print(f"Telegram poslat (chat_id {chat_id}).", flush=True)
        return True
    except Exception as e:
        print(f"Telegram greška: {e}", file=sys.stderr)
        return False


def _notify_email_resend(subject: str, body: str, api_key: str) -> bool:
    to_raw = _smtp_env_strip(os.environ.get("EMAIL_TO", ""))
    if not to_raw:
        print("Resend: u .env dodaj EMAIL_TO.", file=sys.stderr)
        return False
    from_addr = _smtp_env_strip(
        os.environ.get("RESEND_FROM", "Rent monitor <onboarding@resend.dev>")
    ) or "Rent monitor <onboarding@resend.dev>"
    try:
        with httpx.Client(timeout=45.0) as client:
            r = client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": from_addr,
                    "to": [to_raw],
                    "subject": subject,
                    "text": body.strip()[:500_000],
                },
            )
        if r.status_code >= 400:
            print(f"Resend HTTP {r.status_code}: {r.text}", file=sys.stderr)
            return False
        print(f"Mejl poslat (Resend) na: {to_raw}", flush=True)
        return True
    except Exception as e:
        print(f"Resend greška: {e}", file=sys.stderr)
        return False


def notify_email(subject: str, body: str) -> bool:
    resend_key = _smtp_env_strip(os.environ.get("RESEND_API_KEY", ""))
    if resend_key:
        return _notify_email_resend(subject, body, resend_key)

    to_raw = _smtp_env_strip(os.environ.get("EMAIL_TO", ""))
    host = _smtp_env_strip(os.environ.get("SMTP_HOST", ""))
    user = _smtp_env_strip(os.environ.get("SMTP_USER", ""))
    password = _smtp_password_clean(os.environ.get("SMTP_PASSWORD", ""))
    if not (to_raw and host and user and password):
        print("Mejl nije poslat: SMTP ili RESEND nije podešen u .env.", file=sys.stderr)
        return False

    port = int(os.environ.get("SMTP_PORT", "587"))
    from_addr = _smtp_env_strip(os.environ.get("EMAIL_FROM", user)) or user
    use_ssl = os.environ.get("SMTP_SSL", "").strip().lower() in ("1", "true", "yes")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_raw
    msg.set_content(body.strip()[:500_000])

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=60) as smtp:
                smtp.login(user, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=60) as smtp:
                smtp.starttls()
                smtp.login(user, password)
                smtp.send_message(msg)
        print(f"Mejl poslat na: {to_raw}", flush=True)
        return True
    except Exception as e:
        print(f"Greška pri slanju e-pošte: {e}", file=sys.stderr)
        return False


def run_once(*, verbose: bool = False, notify_no_new: bool = False) -> int:
    if not SOURCES:
        print("Dodaj bar jedan Source u SOURCES.", file=sys.stderr)
        return 2

    state = load_state()
    last_state = load_last_state()
    # Global set of seen keys across all sources to avoid duplicate notifications
    all_vals = [v for v in state.values()]
    global_seen: set[str] = _clean_state_keys(set().union(*map(set, all_vals))) if all_vals else set()
    any_new = False
    lines: list[str] = []

    for src in SOURCES:
        # Skip blocked sources (user asked to ignore 'verra')
        if _is_blocked_source(src):
            # purge any existing state entries for this source
            if src.name in state:
                try:
                    del state[src.name]
                except Exception:
                    pass
            if src.name in last_state:
                try:
                    del last_state[src.name]
                except Exception:
                    pass
            continue
        try:
            hrefs = listing_hrefs_for_source(src)
        except Exception as e:
            print(f"[{src.name}] greška pri učitavanju: {e}", file=sys.stderr)
            continue

        keys = {listing_key(h) for h in hrefs}
        prev = _seen_keys_for_source(state, src.name)

        # Stari state.json sa hash-evima — jednom prebaci na ključeve BEZ poruka.
        if _source_has_only_legacy_hashes(state, src.name):
            state[src.name] = sorted(keys)
            try:
                save_state(state)
            except OSError as e:
                print(f"state.json nije sacuvan: {e}", file=sys.stderr)
                return 1
            continue

        if src.name not in state:
            state[src.name] = sorted(keys)
            try:
                save_state(state)
            except OSError as e:
                print(f"state.json nije sacuvan: {e}", file=sys.stderr)
                return 1
            continue

        # If we have a recorded ever-seen `state` but no `last_state` entry for
        # this source, treat this as an initial synchronization for the
        # "last check" and do NOT send notifications containing the entire
        # current listing (avoid mass first-run floods). Persist last_state
        # now so subsequent runs will diff against it.
        if src.name not in last_state:
            state[src.name] = sorted(prev | keys)
            last_state[src.name] = sorted(keys)
            try:
                save_state(state)
            except OSError as e:
                print(f"state.json nije sacuvan: {e}", file=sys.stderr)
                return 1
            try:
                save_last_state(last_state)
            except OSError:
                pass
            continue

        # Only notify if the listing key wasn't present in the previous check for this source
        # Treat "new" as not present in the ever-seen `state.json` so we only
        # notify for listings we've never seen before (not merely absent from
        # the last check). `prev` is the normalized seen keys from `state`.
        new_hrefs = [h for h in sorted(hrefs) if listing_key(h) not in prev and listing_key(h) not in global_seen]
        # Odmah označi sve trenutne oglase kao viđene (ever-seen) and update last check.
        state[src.name] = sorted(prev | keys)
        last_state[src.name] = sorted(keys)
        try:
            save_state(state)
        except OSError as e:
            print(f"state.json nije sacuvan: {e}", file=sys.stderr)
            return 1

        if new_hrefs:
            any_new = True
            notify_console(src.name, new_hrefs)
            lines.append(f"{src.name} — novo:\n" + "\n".join(new_hrefs))
            # Mark these keys as globally seen to avoid duplicate notifications
            for h in new_hrefs:
                global_seen.add(listing_key(h))
            # Persist last_state immediately so these notified items won't be re-notified
            try:
                save_last_state(last_state)
            except OSError:
                pass
    # Save last_state so next run can diff against this check
    try:
        save_last_state(last_state)
    except OSError:
        pass

    if any_new and lines:
        plain = "\n\n".join(lines)
        subj = os.environ.get("EMAIL_SUBJECT", "Rent monitor: novi oglasi").strip()
        notify_telegram(plain)
        notify_email(subj or "Rent monitor: novi oglasi", plain)
    else:
        # When running as a persistent watcher, optionally notify that nothing new was found.
        if notify_no_new:
            text = "Rent monitor: nema novih oglasa ni za jednu praćenu agenciju."
            print(text, flush=True)
            notify_telegram(text)
            subj_none = os.environ.get("EMAIL_SUBJECT", "Rent monitor: nema novih oglasa").strip()
            notify_email(subj_none or "Rent monitor: nema novih oglasa", text)

    # Default: no console/email/telegram output when nothing is new (unless notify_no_new=True).

    return 0


def run_sync_state() -> int:
    """Upiši sve trenutne oglase u state.json bez Telegrama/mejla."""
    state = load_state()
    last_state = load_last_state()
    for src in SOURCES:
        # Skip blocked sources and remove their state entries
        if _is_blocked_source(src):
            if src.name in state:
                try:
                    del state[src.name]
                except Exception:
                    pass
            if src.name in last_state:
                try:
                    del last_state[src.name]
                except Exception:
                    pass
            print(f"[{src.name}] preskoceno (blokirano)", flush=True)
            continue
        try:
            hrefs = listing_hrefs_for_source(src)
        except Exception as e:
            print(f"[{src.name}] preskoceno: {e}", file=sys.stderr)
            continue
        keys = {listing_key(h) for h in hrefs}
        prev = _seen_keys_for_source(state, src.name)
        state[src.name] = sorted(prev | keys)
        last_state[src.name] = sorted(keys)
        print(f"[{src.name}] {len(state[src.name])} oznaceno kao procitano", flush=True)
    try:
        save_state(state)
    except OSError as e:
        print(f"state.json nije sacuvan: {e}", file=sys.stderr)
        return 1
    try:
        save_last_state(last_state)
    except OSError as e:
        print(f"last_state.json nije sacuvan: {e}", file=sys.stderr)
        return 1
    print(f"Sacuvano u: {STATE_FILE}", flush=True)
    print("Sledeca provera salje SAMO za oglase koji nisu u ovom fajlu.", flush=True)
    return 0


def run_diagnose() -> int:
    env_path = _ROOT / ".env"
    print("=== rental_watch — dijagnostika ===", flush=True)
    print(f".env postoji: {env_path.is_file()}", flush=True)

    tg_tok = _smtp_env_strip(os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    tg_chat = _smtp_env_strip(os.environ.get("TELEGRAM_CHAT_ID", ""))
    print(f"TELEGRAM_BOT_TOKEN: {'da' if tg_tok else 'NEMA'}", flush=True)
    print(f"TELEGRAM_CHAT_ID: {tg_chat or 'NEMA'}", flush=True)

    if tg_tok and tg_chat:
        print("Pokusaj Telegram…", flush=True)
        if notify_telegram("Rent monitor — dijagnostika (Telegram radi)."):
            return 0
        return 1

    print("Dodaj TELEGRAM_BOT_TOKEN i TELEGRAM_CHAT_ID u .env", flush=True)
    return 1


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Monitor izdavanja.")
    p.add_argument("--watch", type=int, metavar="SEC", default=None)
    p.add_argument("--telegram-all", action="store_true", help="Send full current listings for every source to Telegram")
    p.add_argument("--test-email", action="store_true")
    p.add_argument("--test-telegram", action="store_true")
    p.add_argument("--diagnose", action="store_true")
    p.add_argument(
        "--sync-state",
        action="store_true",
        help="Snimi sve trenutne oglase u state.json bez obavestenja.",
    )
    p.add_argument("--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    args = _parse_args(argv)
    if args.telegram_all:
        # Send full current listings for every source to Telegram
        sent_any = False
        for src in SOURCES:
            try:
                hrefs = listing_hrefs_for_source(src)
            except Exception as e:
                print(f"[{src.name}] preskoceno: {e}", file=sys.stderr)
                continue
            if not hrefs:
                continue
            lines = [f"{src.name} — ukupno: {len(hrefs)}"] + sorted(hrefs)
            text = "\n".join(lines)
            if notify_telegram(text):
                sent_any = True
            else:
                print(f"Slanje Telegrama za {src.name} nije uspelo.", file=sys.stderr)
        return 0 if sent_any else 1
    if args.diagnose:
        return run_diagnose()
    if args.sync_state:
        return run_sync_state()
    if args.test_email:
        return 0 if notify_email("Rent monitor: test", "Probni mejl.") else 1
    if args.test_telegram:
        return (
            0
            if notify_telegram("Probna poruka — ako vidis ovo, Telegram radi.")
            else 1
        )

    interval = args.watch
    if interval is None:
        raw = os.environ.get("WATCH_INTERVAL_SECONDS", "").strip()
        if raw.isdigit():
            interval = int(raw)
    # Default to 10 minutes (600s) when no --watch and no env var provided
    if interval is None:
        interval = 600

    if interval is not None:
        interval = max(interval, 30)
        print(f"Praćenje svakih {interval}s. Ctrl+C za stop.", flush=True)
        try:
            while True:
                run_once(verbose=args.verbose, notify_no_new=True)
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nZaustavljeno.", flush=True)
            return 0

    return run_once(verbose=args.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
