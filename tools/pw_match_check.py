from pathlib import Path
import sys
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))
import rental_watch as rw
from playwright.sync_api import sync_playwright

TARGETS = ["Homey Housing", "WoonCompany"]
OUT = Path(__file__).resolve().parents[1] / 'tools_output'
OUT.mkdir(exist_ok=True)

for s in rw.SOURCES:
    if s.name not in TARGETS:
        continue
    print('---', s.name)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        ctx = browser.new_context(user_agent=rw.USER_AGENT, locale='en-US', viewport={'width':1366,'height':768})
        page = ctx.new_page()
        page.goto(s.url, wait_until='networkidle', timeout=120000)
        page.wait_for_timeout(3000)
        anchors = page.evaluate("() => Array.from(document.querySelectorAll('a')).map(a => a.href)")
        matches = []
        for a in anchors:
            try:
                if s.listing_href_pattern.search(a):
                    matches.append(a)
            except Exception:
                pass
        print('total anchors:', len(anchors))
        print('pattern matches:', len(matches))
        for m in matches[:40]:
            print('  ', m)
        ctx.close()
        browser.close()
