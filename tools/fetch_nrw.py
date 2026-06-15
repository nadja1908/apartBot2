import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rental_watch import fetch_html
from bs4 import BeautifulSoup

OUT = Path(__file__).resolve().parents[1] / 'tools_output'
OUT.mkdir(exist_ok=True)

url = "https://nrw-wonen.nl/huur-aanbod/"

print('Fetching', url)
html = fetch_html(url)
out_file = OUT / 'nrw_wonen_huur.html'
out_file.write_text(html, encoding='utf-8')
print('Saved HTML to', out_file)

soup = BeautifulSoup(html, 'html.parser')
anchors = set()
for a in soup.find_all('a', href=True):
    h = a['href']
    if not h:
        continue
    anchors.add(h)

links_file = OUT / 'nrw_wonen_huur.links.txt'
links_file.write_text('\n'.join(sorted(anchors)), encoding='utf-8')
print(f'Found {len(anchors)} anchors, saved to', links_file)
