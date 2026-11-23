"""Rule-based signals in Dutch, French and English.

These run without any API key. They don't decide anything on their own:
they flag pages for review and give the optional Claude step hints.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

STATUS_PATTERNS: dict[str, list[str]] = {
    "Suspended": [
        r"temporarily suspended", r"\bsuspended\b", r"no new calls? will be launched",
        r"no new projects can be funded",
        r"tijdelijk (?:opgeschort|geschorst)", r"\bopgeschort\b", r"\bgeschorst\b", r"geen nieuwe oproepen",
        r"temporairement suspendu", r"\bsuspendu(?:e|s)?\b", r"aucun nouvel appel",
    ],
    "Closed": [
        r"no longer possible to (?:apply|submit)", r"\bdiscontinued\b", r"no new applications",
        r"geen aanvraag meer mogelijk", r"geen nieuwe (?:indieningen|aanvragen)", r"\bstopgezet\b", r"\bafgeschaft\b",
        r"n'est plus possible", r"plus aucune demande", r"\bsupprimée?\b",
    ],
    "Closing": [
        r"budget (?:is|was) (?:fully )?(?:used|exhausted)", r"budget (?:is )?uitgeput", r"budget épuisé",
        r"ends on \d", r"verdwijnt", r"loopt af",
    ],
    "Open": [
        r"permanently open", r"\bcall (?:is )?(?:now )?open\b", r"apply now", r"\bopen call\b",
        r"permanent open", r"doorlopend", r"oproep (?:is )?open", r"kan je (?:nu )?indienen",
        r"appel (?:est )?ouvert", r"en continu", r"appel à projets (?:est )?lancé",
    ],
}

DEADLINE_WORDS = re.compile(
    r"deadline|closing date|submission|submit|apply before|until|"
    r"uiterste|deadline|indien|tot en met|ten laatste|sluit|"
    r"date limite|clôture|cloture|dépôt|avant le|jusqu'au",
    re.I,
)

MONTHS = {
    # en
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7,
    "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    # nl
    "januari": 1, "februari": 2, "maart": 3, "mei": 5, "juni": 6, "juli": 7, "augustus": 8,
    "oktober": 10,
    # fr
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "juin": 6, "juillet": 7,
    "août": 8, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
}
_month_alt = "|".join(sorted(MONTHS, key=len, reverse=True))
DATE_WORDS = re.compile(rf"\b(\d{{1,2}})(?:er|st|nd|rd|th)?\s+({_month_alt})\.?,?\s+(20\d\d)\b", re.I)
DATE_WORDS_EN = re.compile(rf"\b({_month_alt})\s+(\d{{1,2}}),?\s+(20\d\d)\b", re.I)
DATE_NUM = re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](20\d\d)\b")
DATE_ISO = re.compile(r"\b(20\d\d)-(\d{2})-(\d{2})\b")


@dataclass
class Signals:
    statuses: dict[str, list[str]] = field(default_factory=dict)   # status -> matched snippets
    deadlines: list[tuple[date, str]] = field(default_factory=list)  # future dates near deadline words

    def likely_status(self) -> str | None:
        # The most restrictive signal wins: a page that says both "open" and
        # "suspended" is almost always announcing a suspension.
        for s in ("Closed", "Suspended", "Closing", "Open"):
            if self.statuses.get(s):
                return s
        return None

    def next_deadline(self) -> date | None:
        return min((d for d, _ in self.deadlines), default=None)


def _snippet(text: str, start: int, end: int, pad: int = 70) -> str:
    return re.sub(r"\s+", " ", text[max(0, start - pad): end + pad]).strip()


def find_dates(text: str) -> list[tuple[date, int, int]]:
    found = []
    for m in DATE_WORDS.finditer(text):
        d, mo, y = int(m.group(1)), MONTHS[m.group(2).lower()], int(m.group(3))
        found.append((d, mo, y, m.start(), m.end()))
    for m in DATE_WORDS_EN.finditer(text):
        mo, d, y = MONTHS[m.group(1).lower()], int(m.group(2)), int(m.group(3))
        found.append((d, mo, y, m.start(), m.end()))
    for m in DATE_NUM.finditer(text):
        found.append((int(m.group(1)), int(m.group(2)), int(m.group(3)), m.start(), m.end()))
    for m in DATE_ISO.finditer(text):
        found.append((int(m.group(3)), int(m.group(2)), int(m.group(1)), m.start(), m.end()))
    out = []
    for d, mo, y, s, e in found:
        try:
            out.append((date(y, mo, d), s, e))
        except ValueError:
            continue
    return out


def analyse(text: str, today: date) -> Signals:
    sig = Signals()
    low = text.lower()
    for status, pats in STATUS_PATTERNS.items():
        for p in pats:
            for m in re.finditer(p, low):
                sig.statuses.setdefault(status, []).append(_snippet(text, m.start(), m.end()))
    seen = set()
    for dt, s, e in find_dates(text):
        if dt <= today or dt in seen:
            continue
        window = text[max(0, s - 90): e + 30]
        if DEADLINE_WORDS.search(window):
            seen.add(dt)
            sig.deadlines.append((dt, _snippet(text, s, e)))
    sig.deadlines.sort()
    return sig
