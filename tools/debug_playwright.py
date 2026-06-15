from pathlib import Path
import sys
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))
import rental_watch as rw

from playwright.sync_api import sync_playwright

TARGETS = [
    'Homey Housing',
    'Frisiamakelaars',
    'WoonCompany',
]

for s in rw.SOURCES:
    if s.name not in TARGETS:
        continue
    print('---', s.name, s.url)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        ctx = browser.new_context(user_agent=rw.USER_AGENT, locale='en-US', viewport={'width':1366,'height':768})
        page = ctx.new_page()
        page.goto(s.url, wait_until='networkidle', timeout=120000)
        page.wait_for_timeout(4000)
        # scroll to bottom slowly to trigger lazy loads
        page.evaluate("() => {window.scrollTo(0, document.body.scrollHeight);}")
        page.wait_for_timeout(2000)
        anchors = page.evaluate("() => Array.from(document.querySelectorAll('a')).map(a => a.href)")
        print('anchors total:', len(anchors))
        # find potential listing containers
        containers = page.evaluate("() => Array.from(document.querySelectorAll('*')).filter(e=> (e.className||'').toString().toLowerCase().includes('aanbod') || (e.className||'').toString().toLowerCase().includes('listing') || (e.id||'').toString().toLowerCase().includes('aanbod') ).slice(0,10).map(e=>({tag:e.tagName, cls: e.className, id: e.id, html: e.innerHTML.slice(0,200)}))")
        print('containers sample:', containers)
        ctx.close()
        browser.close()
