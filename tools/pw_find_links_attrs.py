from pathlib import Path
import sys
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))
import rental_watch as rw
from playwright.sync_api import sync_playwright

TARGETS = ["Homey Housing", "WoonCompany"]

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
        # find attributes containing '/woning' or '/aanbod' or 'woningaanbod'
        results = page.evaluate("() => { const out=[]; const els = Array.from(document.querySelectorAll('*')); for(const e of els){ for(const a of e.getAttributeNames()){ try{ const v = e.getAttribute(a); if(!v) continue; if(v.includes('/woning')||v.includes('/aanbod')||v.includes('woningaanbod')){ out.push({tag:e.tagName, attr:a, val:v, classes:e.className}); } }catch(e){ } } } return out; }")
        print('found attrs:', len(results))
        for r in results[:60]:
            print(r)
        ctx.close()
        browser.close()
