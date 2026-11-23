"""Change one scheme in data/schemes.json without editing JSON by hand.

Examples (on Windows, use set_field.bat with the same arguments):
    python -m scraper.set_field BR-02 status="Suspended"
    python -m scraper.set_field VL-04 next_deadline=2027-03-15 status="Call in progress"
    python -m scraper.set_field VL-04 next_deadline=        # clear a field
    python -m scraper.set_field BR-02 --verified            # checked, nothing changed
    python -m scraper.set_field BR-02                       # show the current record

Every change also sets last_verified to today. Run rebuild_site.bat (or
python site/build_site.py) afterwards to see it on the site.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "schemes.json"
STATUSES = ["Open", "Call in progress", "Suspended", "Closing", "Closed", "Under reform", "No current call"]
NUMBER_FIELDS = {"amount_min_eur", "amount_max_eur", "max_duration_months", "max_company_age_years"}


def parse_value(field: str, raw: str):
    raw = raw.strip().strip('"').strip("'")
    if raw == "":
        return None
    if field in NUMBER_FIELDS:
        return int(raw.replace(".", "").replace(",", "").replace("€", ""))
    if field == "status":
        match = [s for s in STATUSES if s.lower() == raw.lower()]
        if not match:
            raise ValueError(f"status must be one of: {', '.join(STATUSES)}")
        return match[0]
    if field in ("next_deadline", "last_verified"):
        try:
            date.fromisoformat(raw)
        except ValueError:
            raise ValueError("write the date as YYYY-MM-DD, e.g. 2027-03-15") from None
    return raw


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    sid, rest = argv[0].upper(), argv[1:]
    data = json.loads(DATA.read_text(encoding="utf-8"))
    rec = next((s for s in data if s["id"] == sid), None)
    if rec is None:
        print(f"No scheme with ID {sid}. IDs look like VL-02, BR-01, WA-03, FED-01.")
        return 1
    if not rest:
        print(json.dumps(rec, indent=1, ensure_ascii=False))
        return 0
    changes = {}
    for arg in rest:
        if arg == "--verified":
            continue
        if "=" not in arg:
            print(f"Don't understand '{arg}'. Use field=value, e.g. status=Suspended")
            return 1
        field, raw = arg.split("=", 1)
        if field not in rec and field not in ("next_deadline",):
            print(f"Unknown field '{field}'. Fields: {', '.join(rec)}")
            return 1
        try:
            changes[field] = parse_value(field, raw)
        except ValueError as e:
            print(f"Can't set {field}: {e}")
            return 1
    for k, v in changes.items():
        print(f"{sid} {k}: {rec.get(k)!r} -> {v!r}")
        rec[k] = v
    rec["last_verified"] = date.today().isoformat()
    DATA.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Saved. {sid} marked as checked today.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
