"""Daily run: fetch every source, detect changes, propose/apply updates, write a report.

Usage:
    python -m scraper.run                # check and report, change nothing in data/
    python -m scraper.run --apply        # also apply high-confidence updates to data/schemes.json
    python -m scraper.run --only VL-04   # check one scheme (handy when testing)
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import sys
from datetime import date
from pathlib import Path

import yaml

from . import llm
from .extract import fingerprint, main_text
from .fetch import Fetcher
from .signals import analyse

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "schemes.json"
STATE_DIR = ROOT / "state"
SNAP_DIR = STATE_DIR / "snapshots"
INDEX = STATE_DIR / "index.json"
REPORTS = ROOT / "reports"
AUTO_APPLY_CONFIDENCE = float(os.environ.get("AUTO_APPLY_CONFIDENCE", "0.85"))
# Fields we let the scraper change on its own. Everything else stays human-edited.
AUTO_FIELDS = {"status", "status_note", "next_deadline"}


def _key(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:12]


def load_state() -> dict:
    return json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {}


def save_state(state: dict) -> None:
    STATE_DIR.mkdir(exist_ok=True)
    INDEX.write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")


def diff_text(old: str, new: str, limit: int = 120) -> str:
    lines = [l for l in difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="", n=0)
             if l[:1] in "+-" and not l.startswith(("+++", "---"))]
    more = len(lines) - limit
    return "\n".join(lines[:limit]) + (f"\n… {more} more changed lines" if more > 0 else "")


def check_url(fetcher, url: str, state: dict, today: str) -> dict:
    """Fetch one URL and compare with its last snapshot."""
    st = state.setdefault(url, {"failures": 0})
    res = fetcher.get(url)
    if not res.ok:
        st["failures"] = st.get("failures", 0) + 1
        st["last_error"] = res.error
        return {"url": url, "ok": False, "error": res.error, "failures": st["failures"]}
    text = main_text(res.html)
    h = fingerprint(text)
    snap = SNAP_DIR / f"{_key(url)}.txt"
    old = snap.read_text(encoding="utf-8") if snap.exists() else None
    st.update(failures=0, last_ok=today, last_error=None)
    out = {"url": url, "ok": True, "text": text, "changed": False, "baseline": old is None}
    if old is None or st.get("hash") != h:
        SNAP_DIR.mkdir(parents=True, exist_ok=True)
        snap.write_text(text, encoding="utf-8")
        st["hash"] = h
        if old is not None:
            st["last_changed"] = today
            out.update(changed=True, diff=diff_text(old, text))
    return out


def run(apply: bool, only: list[str] | None, today: date, fetcher=None) -> dict:
    cfg = yaml.safe_load((ROOT / "sources.yaml").read_text(encoding="utf-8"))
    d = cfg.get("defaults", {})
    fetcher = fetcher or Fetcher(d.get("user_agent", "HealthFundingFinderBot/0.1"),
                                 d.get("timeout_seconds", 30), d.get("delay_per_host_seconds", 3))
    max_fail = d.get("max_failures_before_alert", 3)
    schemes = json.loads(DATA.read_text(encoding="utf-8"))
    by_id = {s["id"]: s for s in schemes}
    state = load_state()
    t = today.isoformat()
    report = {"date": t, "applied": [], "review": [], "deadlines_passed": [], "discovery": [],
              "broken": [], "baselines": 0, "checked": 0, "llm": llm.enabled()}

    for sid, conf in (cfg.get("schemes") or {}).items():
        if only and sid not in only:
            continue
        rec = by_id.get(sid)
        if rec is None:
            report["review"].append({"id": sid, "title": sid, "why": ["In sources.yaml but not in data/schemes.json"]})
            continue
        conf = conf or {}
        urls = [conf.get("url") or rec["source_url"]] + list(conf.get("extra_urls", []))
        results = [check_url(fetcher, u, state, t) for u in urls]
        report["checked"] += len(results)
        report["baselines"] += sum(1 for r in results if r.get("baseline"))

        for r in results:
            if not r["ok"] and r["failures"] >= max_fail:
                report["broken"].append({"id": sid, "url": r["url"], "error": r["error"], "failures": r["failures"]})

        # Housekeeping that needs no page change: a deadline in the past.
        if rec.get("next_deadline") and rec["next_deadline"] < t:
            report["deadlines_passed"].append({"id": sid, "title": rec["scheme_name"], "deadline": rec["next_deadline"]})
            if apply:
                rec["next_deadline"] = None

        changed = [r for r in results if r.get("changed")]
        if not changed:
            if apply and all(r["ok"] for r in results):
                rec["last_verified"] = t   # source re-read and unchanged
            continue

        page_text = "\n\n".join(r["text"] for r in changed)
        diff = "\n\n".join(f"# {r['url']}\n{r['diff']}" for r in changed)
        sig = analyse(page_text, today)
        why = []
        hinted = sig.likely_status()
        current = rec.get("status")
        if hinted and not (hinted == current or (hinted == "Open" and current == "Call in progress")):
            why.append(f"Page wording suggests status **{hinted}** (now: {current}): “{sig.statuses[hinted][0]}”")
        nd = sig.next_deadline()
        if nd and nd.isoformat() != rec.get("next_deadline"):
            why.append(f"Future date near deadline wording: **{nd.isoformat()}** (“{sig.deadlines[0][1]}”)")

        proposal = llm.propose(rec, page_text, diff, t)
        fixes = []
        if hinted and hinted != current and not (hinted == "Open" and current == "Call in progress"):
            fixes.append(f'set_field.bat {sid} status="{hinted}"')
        if nd and nd.isoformat() != rec.get("next_deadline"):
            fixes.append(f"set_field.bat {sid} next_deadline={nd.isoformat()}")
        item = {"id": sid, "title": rec["scheme_name"], "urls": [r["url"] for r in changed],
                "why": why or ["Page text changed"], "diff": diff, "proposal": proposal, "fixes": fixes}

        if apply and proposal and proposal["confidence"] >= AUTO_APPLY_CONFIDENCE \
                and set(proposal["changes"]) <= AUTO_FIELDS:
            before = {k: rec.get(k) for k in proposal["changes"]}
            rec.update(proposal["changes"])
            rec["last_verified"] = t
            item["before"] = before
            report["applied"].append(item)
        else:
            report["review"].append(item)

    for src in cfg.get("discovery") or []:
        if only:
            break
        r = check_url(fetcher, src["url"], state, t)
        report["checked"] += 1
        if r.get("baseline"):
            report["baselines"] += 1
        if not r["ok"] and r["failures"] >= max_fail:
            report["broken"].append({"id": src["name"], "url": src["url"], "error": r["error"], "failures": r["failures"]})
        if r.get("changed"):
            added = [l[1:] for l in r["diff"].splitlines() if l.startswith("+")]
            report["discovery"].append({"name": src["name"], "url": src["url"], "added": added[:25]})

    save_state(state)
    if apply:
        DATA.write_text(json.dumps(schemes, indent=1, ensure_ascii=False), encoding="utf-8")
    write_report(report)
    return report


def has_news(rep: dict) -> bool:
    return any(rep[k] for k in ("applied", "review", "deadlines_passed", "discovery", "broken"))


def write_report(rep: dict) -> None:
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "latest.json").write_text(json.dumps(
        {k: rep[k] for k in ("date", "checked", "baselines", "llm")} |
        {k: len(rep[k]) for k in ("applied", "review", "deadlines_passed", "discovery", "broken")} |
        {"has_news": has_news(rep)}, indent=1), encoding="utf-8")
    if not has_news(rep):
        return
    L = [f"# Funding sources check – {rep['date']}", "",
         f"Checked {rep['checked']} pages. Claude extraction: {'on' if rep['llm'] else 'off (no API key)'}.", ""]
    if rep["applied"]:
        L += ["## Updated automatically", ""]
        for i in rep["applied"]:
            L.append(f"- **{i['id']} {i['title']}**: {i['proposal']['summary']}")
            for k, v in i["proposal"]["changes"].items():
                L.append(f"    - `{k}`: {i['before'].get(k)!r} → {v!r}  \n    evidence: “{i['proposal']['evidence'].get(k)}”")
        L.append("")
    if rep["review"]:
        L += ["## Needs a human look", ""]
        for i in rep["review"]:
            L.append(f"### {i['id']} {i['title']}")
            L += [f"- {w}" for w in i["why"]]
            for u in i.get("urls", []):
                L.append(f"- Source: {u}")
            if i.get("fixes"):
                L.append("- If the page confirms it, accept with:")
                L += [f"    - `{c}`" for c in i["fixes"]]
            L.append(f"- Checked and nothing to change? Run `set_field.bat {i['id']} --verified`")
            p = i.get("proposal")
            if p:
                L.append(f"- Claude suggests (confidence {p['confidence']:.2f}): {p['summary']}")
                L += [f"    - `{k}` → {v!r} (“{p['evidence'].get(k)}”)" for k, v in p["changes"].items()]
            if i.get("diff"):
                L += ["", "<details><summary>Text diff</summary>", "", "```diff", i["diff"], "```", "</details>"]
            L.append("")
    if rep["deadlines_passed"]:
        L += ["## Deadlines that have passed", ""]
        L += [f"- {d['id']} {d['title']}: {d['deadline']}" for d in rep["deadlines_passed"]] + [""]
    if rep["discovery"]:
        L += ["## Overview pages that changed (possible new calls)", ""]
        for d in rep["discovery"]:
            L.append(f"### {d['name']}\n{d['url']}\n")
            L += [f"- {a}" for a in d["added"]] + [""]
    if rep["broken"]:
        L += ["## Sources failing repeatedly", ""]
        L += [f"- {b['id']}: {b['url']} – {b['error']} ({b['failures']} runs in a row)" for b in rep["broken"]]
    (REPORTS / f"{rep['date']}.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write high-confidence updates to data/schemes.json")
    ap.add_argument("--only", nargs="*", help="scheme IDs to check")
    ap.add_argument("--today", help="override today's date (YYYY-MM-DD), for testing")
    a = ap.parse_args(argv)
    today = date.fromisoformat(a.today) if a.today else date.today()
    rep = run(a.apply, a.only, today)
    print(json.dumps(json.loads((REPORTS / "latest.json").read_text(encoding="utf-8")), indent=1))
    gh = os.environ.get("GITHUB_OUTPUT")
    if gh:
        with open(gh, "a") as f:
            f.write(f"has_news={'true' if has_news(rep) else 'false'}\n")
            f.write(f"report=reports/{rep['date']}.md\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
