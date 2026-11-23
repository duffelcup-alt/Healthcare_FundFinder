"""Optional: ask Claude to propose field updates for a changed page.

Runs only when ANTHROPIC_API_KEY is set. The answer is a proposal with a
confidence and a verbatim evidence quote; run.py decides whether to apply it.
"""
from __future__ import annotations

import json
import os
import re

EDITABLE = ["status", "status_note", "next_deadline", "funding_rate", "amount_min_eur",
            "amount_max_eur", "max_duration_months", "key_conditions"]
STATUSES = ["Open", "Call in progress", "Suspended", "Closing", "Closed", "Under reform", "No current call"]

PROMPT = """You maintain a dataset of Belgian funding schemes for healthcare startups.
Today is {today}. Below is the current record for one scheme, and the text of its
official page, which has changed since the last check.

Decide whether the page changes any of these fields: {fields}.
Rules:
- Only use what the page says. If the page doesn't state a value, leave the field out.
- status must be one of: {statuses}.
- next_deadline is the next future deadline for applicants, as YYYY-MM-DD, or null if none.
- status_note: one or two plain sentences on what the status means for an applicant.
- For every changed field give a short verbatim quote from the page as evidence.
- confidence: 0.0-1.0 that your changes are correct and current.

Reply with JSON only, in this shape:
{{"changes": {{"<field>": <new value>, ...}}, "evidence": {{"<field>": "<quote>"}}, "confidence": 0.0, "summary": "<one sentence>"}}

CURRENT RECORD:
{record}

WHAT CHANGED ON THE PAGE (unified diff, may be truncated):
{diff}

FULL PAGE TEXT (may be truncated):
{text}
"""


def enabled() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def propose(record: dict, page_text: str, diff: str, today: str) -> dict | None:
    if not enabled():
        return None
    import anthropic  # imported lazily so the scraper runs without it

    client = anthropic.Anthropic()
    model = os.environ.get("SCRAPER_MODEL", "claude-sonnet-5-5")
    keep = {k: record.get(k) for k in ["id", "scheme_name", "level", "agency"] + EDITABLE}
    msg = client.messages.create(
        model=model,
        max_tokens=1200,
        messages=[{"role": "user", "content": PROMPT.format(
            today=today, fields=", ".join(EDITABLE), statuses=", ".join(STATUSES),
            record=json.dumps(keep, ensure_ascii=False, indent=1),
            diff=diff[:6000], text=page_text[:14000])}],
    )
    raw = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return None
    try:
        out = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return validate(out, page_text)


def validate(out: dict, page_text: str) -> dict | None:
    """Drop anything we can't trust: unknown fields, bad statuses, quotes not on the page."""
    changes = {k: v for k, v in (out.get("changes") or {}).items() if k in EDITABLE}
    evidence = out.get("evidence") or {}
    page_norm = re.sub(r"\s+", " ", page_text).lower()
    clean = {}
    for k, v in changes.items():
        if k == "status" and v not in STATUSES:
            continue
        if k == "next_deadline" and v is not None and not re.fullmatch(r"20\d\d-\d\d-\d\d", str(v)):
            continue
        quote = re.sub(r"\s+", " ", str(evidence.get(k, ""))).lower().strip()
        if k != "status_note" and (len(quote) < 8 or quote[:120] not in page_norm):
            continue  # no verifiable evidence on the page -> don't accept
        clean[k] = v
    if not clean:
        return None
    return {"changes": clean, "evidence": {k: evidence.get(k) for k in clean},
            "confidence": float(out.get("confidence") or 0), "summary": out.get("summary", "")}
