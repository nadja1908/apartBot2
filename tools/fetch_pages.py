import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))
import rental_watch as rw
from bs4 import BeautifulSoup

OUT = Path(__file__).resolve().parents[1] / 'tools_output'
OUT.mkdir(exist_ok=True)
PROBLEMATIC = [
    "Immovita",
    "Homey Housing",
    "Frisiamakelaars",
    "Karens Real Estate",
    "WoonCompany",
    "BW Housing",
    "Riemersma Real Estate",
    "Expata",
]

for s in rw.SOURCES:
    if s.name not in PROBLEMATIC:
        continue
    print('---', s.name)
    try:
        # try simple HTTP fetch first
        html = rw.fetch_html(s.url)
        method = 'http'
    except Exception as e:
        print('http fetch failed:', e)
        try:
            html = rw.fetch_playwright_html(s.url)
            method = 'playwright'
        except Exception as e2:
            print('playwright fetch failed:', e2)
            continue
    out_file = OUT / (s.name.replace(' ', '_') + f'_{method}.html')
    out_file.write_text(html, encoding='utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    anchors = {a.get('href') for a in soup.find_all('a') if a.get('href')}
    print(f'method={method} anchors={len(anchors)} sample={list(sorted(anchors))[:20]}')
    print('saved to', out_file)
