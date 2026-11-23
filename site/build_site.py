"""Build the site into site/public/:

- index.html    the finder, with data/schemes.json built in (opens straight from disk)
- updates.html  every scraper report, newest first
- schemes.json  a copy of the data
"""
import html as h
import json
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "public"


def build() -> Path:
    data = json.loads((ROOT / "data" / "schemes.json").read_text(encoding="utf-8"))
    tpl = (ROOT / "site" / "template.html").read_text(encoding="utf-8")
    assert "__DATA__" in tpl, "template.html must contain the __DATA__ placeholder"
    data_sorted = sorted(data, key=lambda s: s["last_verified"], reverse=True)  # page shows newest check date
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(tpl.replace("__DATA__", json.dumps(data_sorted, ensure_ascii=False)), encoding="utf-8")
    (OUT / "schemes.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "updates.html").write_text(updates_page(), encoding="utf-8")
    print(f"Built {OUT / 'index.html'} with {len(data)} schemes")
    return OUT / "index.html"


def updates_page() -> str:
    reports = sorted((ROOT / "reports").glob("20*.md"), reverse=True)
    latest = {}
    lj = ROOT / "reports" / "latest.json"
    if lj.exists():
        latest = json.loads(lj.read_text(encoding="utf-8"))
    if latest:
        status = (f"Last check: {h.escape(latest['date'])} · {latest['checked']} pages · "
                  f"{latest['review']} to review · {latest['broken']} failing sources")
    else:
        status = "The scraper hasn't run yet. Double-click update_data.bat."
    body = "".join(
        f'<article><div class="md">{markdown.markdown(r.read_text(encoding="utf-8"), extensions=["fenced_code", "sane_lists"])}</div></article>'
        for r in reports[:30]) or '<p class="empty">No changes reported yet. The first run only saves a copy of each page; reports start from the second run.</p>'
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Funding Finder Data Updates</title>
<style>
:root {{ --ink:#14232b; --muted:#5a6b74; --paper:#f5f7f7; --surface:#fff; --line:#d9e1e3; --accent:#0b6e6e; color-scheme: light; }}
@media (prefers-color-scheme: dark) {{ :root {{ --ink:#e4ecee; --muted:#9aabb2; --paper:#10191d; --surface:#172328; --line:#2a3a40; --accent:#4fc0b8; color-scheme: dark; }} }}
body {{ margin:0; background:var(--paper); color:var(--ink); font:15px/1.55 "Segoe UI", system-ui, sans-serif; }}
.wrap {{ max-width: 900px; margin: 0 auto; padding: 20px; }}
a {{ color: var(--accent); }}
header {{ display:flex; justify-content:space-between; align-items:baseline; gap:12px; flex-wrap:wrap; }}
h1 {{ font-size:1.5rem; margin:0; }}
.status {{ color:var(--muted); margin:6px 0 20px; }}
article {{ background:var(--surface); border:1px solid var(--line); border-radius:10px; padding:4px 20px 12px; margin-bottom:16px; }}
.md h1 {{ font-size:1.2rem; }} .md h2 {{ font-size:1.05rem; border-top:1px solid var(--line); padding-top:12px; }} .md h3 {{ font-size:.98rem; }}
code {{ background:var(--paper); padding:1px 5px; border-radius:4px; font-size:.9em; }}
pre {{ background:var(--paper); padding:10px; border-radius:6px; overflow-x:auto; font-size:.82rem; }}
.empty {{ color:var(--muted); border:1px dashed var(--line); border-radius:10px; padding:16px; }}
</style></head>
<body><div class="wrap">
<header><h1>Data updates</h1><a href="index.html">Back to the finder</a></header>
<p class="status">{status}</p>
{body}
</div></body></html>"""


if __name__ == "__main__":
    build()
