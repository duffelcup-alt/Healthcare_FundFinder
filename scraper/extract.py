"""Turn a page into stable, comparable text.

Government pages carry a lot of noise (menus, cookie banners, "page age",
related-news blocks). We keep the main content so a change in the text
means a change in the content, not in the navigation.
"""
from __future__ import annotations

import hashlib
import re

from bs4 import BeautifulSoup

NOISE_TAGS = ["script", "style", "noscript", "nav", "header", "footer", "aside", "form", "svg", "iframe"]
NOISE_HINTS = re.compile(r"cookie|breadcrumb|menu|navbar|footer|share|social|newsletter|related|skip", re.I)
# Lines that change without the content changing.
VOLATILE = [
    re.compile(r"^(page age|laatst gewijzigd|last updated|mis à jour|updated on)\b.*$", re.I),
    re.compile(r"^©.*$"),
]


def main_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(NOISE_TAGS):
        tag.decompose()
    for el in soup.find_all(True):
        if el.attrs is None:
            continue
        attrs = " ".join([el.get("id") or "", " ".join(el.get("class") or []), el.get("role") or ""])
        if attrs.strip() and NOISE_HINTS.search(attrs) and el.name not in ("main", "article", "body"):
            el.decompose()
    root = soup.find("main") or soup.find("article") or soup.body or soup
    lines = []
    for raw in root.get_text("\n").splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if not line or any(p.match(line) for p in VOLATILE):
            continue
        lines.append(line)
    # Drop exact duplicate consecutive lines (menus rendered twice, etc.)
    out = [l for i, l in enumerate(lines) if i == 0 or l != lines[i - 1]]
    return "\n".join(out)


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
