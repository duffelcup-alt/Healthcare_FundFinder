"""Build site/public/index.html from site/template.html + data/schemes.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "data" / "schemes.json").read_text())
html = (ROOT / "site" / "template.html").read_text()
assert "__DATA__" in html, "template.html must contain the __DATA__ placeholder"
# The page shows the most recent check date across all schemes.
latest = max(s["last_verified"] for s in data)
data_sorted = sorted(data, key=lambda s: s["last_verified"], reverse=True)
out = ROOT / "site" / "public"
out.mkdir(parents=True, exist_ok=True)
(out / "index.html").write_text(html.replace("__DATA__", json.dumps(data_sorted, ensure_ascii=False)))
(out / "schemes.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
print(f"built site/public/index.html with {len(data)} schemes, latest check {latest}")
