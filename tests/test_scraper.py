import json
import shutil
from datetime import date
from pathlib import Path

import pytest

from scraper import llm, run as runmod
from scraper.extract import main_text
from scraper.fetch import FetchResult
from scraper.signals import analyse

TODAY = date(2026, 11, 23)

PAGE_OPEN = """<html><body><nav>Home | Subsidies</nav><main>
<h1>R&amp;D projects</h1><p>We finance 15% to 70% of the cost.</p>
<p>Submit your project at any time.</p><p>Page age: 3 days ago</p></main>
<footer>© 2026 Innoviris</footer></body></html>"""

PAGE_SUSPENDED = """<html><body><nav>Home | Subsidies</nav><main>
<h1>R&amp;D projects</h1><p>We finance 15% to 70% of the cost.</p>
<p>No new calls will be launched in 2026, and all programs will be suspended in 2026.</p>
<p>Page age: 9 days ago</p></main><footer>© 2026 Innoviris</footer></body></html>"""

PAGE_NL_DEADLINE = """<main><h1>Projectoproep 2027.1</h1>
<p>De oproep is open. Uiterste datum voor het indienen van abstracts: 15 maart 2027.</p>
<p>Gepubliceerd op 2 november 2026.</p></main>"""

PAGE_FR = """<main><p>L'appel est ouvert. Date limite de dépôt : 2 février 2027 à 12h00.</p>
<p>Ce subside est temporairement suspendu à partir du 12 août 2026.</p></main>"""


def test_main_text_strips_navigation_and_volatile_lines():
    t = main_text(PAGE_OPEN)
    assert "Home | Subsidies" not in t
    assert "Page age" not in t and "©" not in t
    assert "We finance 15% to 70% of the cost." in t


def test_volatile_lines_do_not_count_as_a_change():
    a = main_text(PAGE_OPEN)
    b = main_text(PAGE_OPEN.replace("3 days ago", "40 days ago"))
    assert a == b


def test_status_signals_english():
    s = analyse(main_text(PAGE_SUSPENDED), TODAY)
    assert s.likely_status() == "Suspended"


def test_dutch_deadline_detected_and_past_publication_date_ignored():
    s = analyse(main_text(PAGE_NL_DEADLINE), TODAY)
    assert s.next_deadline() == date(2027, 3, 15)
    assert s.likely_status() == "Open"
    assert all(d != date(2026, 11, 2) for d, _ in s.deadlines)


def test_french_suspension_beats_open():
    s = analyse(main_text(PAGE_FR), TODAY)
    assert s.likely_status() == "Suspended"
    assert s.next_deadline() == date(2027, 2, 2)


def test_llm_validation_rejects_unverifiable_evidence():
    page = "No new calls will be launched in 2026, and all programs will be suspended in 2026."
    good = {"changes": {"status": "Suspended"}, "evidence": {"status": "all programs will be suspended in 2026"}, "confidence": 0.9}
    bad = {"changes": {"status": "Suspended", "amount_max_eur": 999},
           "evidence": {"status": "this sentence is not on the page", "amount_max_eur": "nope"}, "confidence": 0.9}
    weird = {"changes": {"status": "Paused"}, "evidence": {"status": "all programs will be suspended"}, "confidence": 0.9}
    assert llm.validate(good, page)["changes"] == {"status": "Suspended"}
    assert llm.validate(bad, page) is None
    assert llm.validate(weird, page) is None


class FakeFetcher:
    def __init__(self, pages):
        self.pages = pages

    def get(self, url):
        html = self.pages.get(url)
        if html is None:
            return FetchResult(url, False, 404, "", "HTTP 404")
        return FetchResult(url, True, 200, html)


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parent.parent
    (tmp_path / "data").mkdir()
    shutil.copy(root / "data" / "schemes.json", tmp_path / "data" / "schemes.json")
    (tmp_path / "sources.yaml").write_text(
        "defaults: {max_failures_before_alert: 2}\n"
        "schemes:\n  BR-02: {}\n  VL-04: {}\n"
        "discovery:\n  - {name: Calendar, url: 'https://example.org/calendar'}\n")
    monkeypatch.setattr(runmod, "ROOT", tmp_path)
    monkeypatch.setattr(runmod, "DATA", tmp_path / "data" / "schemes.json")
    monkeypatch.setattr(runmod, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(runmod, "SNAP_DIR", tmp_path / "state" / "snapshots")
    monkeypatch.setattr(runmod, "INDEX", tmp_path / "state" / "index.json")
    monkeypatch.setattr(runmod, "REPORTS", tmp_path / "reports")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return tmp_path


def test_full_run_baseline_then_change(project):
    data = json.loads((project / "data" / "schemes.json").read_text())
    br02 = next(s for s in data if s["id"] == "BR-02")
    vl04 = next(s for s in data if s["id"] == "VL-04")
    # Pretend BR-02 is still open in our data, so the suspension is news.
    br02["status"] = "Open"
    (project / "data" / "schemes.json").write_text(json.dumps(data))

    pages = {br02["source_url"]: PAGE_OPEN, "https://example.org/calendar": "<main><p>Calls 2026</p></main>"}
    # VL-04's pages are missing -> failures

    rep1 = runmod.run(apply=True, only=None, today=TODAY, fetcher=FakeFetcher(pages))
    assert rep1["baselines"] == 2 and not rep1["review"]

    pages[br02["source_url"]] = PAGE_SUSPENDED
    pages["https://example.org/calendar"] = "<main><p>Calls 2026</p><p>New: Health call 2027</p></main>"
    rep2 = runmod.run(apply=True, only=None, today=TODAY, fetcher=FakeFetcher(pages))

    review = {i["id"]: i for i in rep2["review"]}
    assert "BR-02" in review
    assert any("Suspended" in w for w in review["BR-02"]["why"])
    assert rep2["discovery"][0]["added"] == ["New: Health call 2027"]
    assert {b["id"] for b in rep2["broken"]} == {"VL-04"}          # failed twice in a row
    assert (project / "reports" / f"{TODAY}.md").exists()
    # Without a Claude proposal nothing is changed automatically.
    after = {s["id"]: s for s in json.loads((project / "data" / "schemes.json").read_text())}
    assert after["BR-02"]["status"] == "Open"


def test_high_confidence_proposal_is_applied(project, monkeypatch):
    data = json.loads((project / "data" / "schemes.json").read_text())
    br02 = next(s for s in data if s["id"] == "BR-02")
    br02["status"] = "Open"
    (project / "data" / "schemes.json").write_text(json.dumps(data))
    pages = {br02["source_url"]: PAGE_OPEN, "https://example.org/calendar": "<main>x</main>"}
    runmod.run(apply=True, only=["BR-02"], today=TODAY, fetcher=FakeFetcher(pages))

    monkeypatch.setattr(llm, "enabled", lambda: True)
    monkeypatch.setattr(llm, "propose", lambda rec, text, diff, today: {
        "changes": {"status": "Suspended", "status_note": "No new calls in 2026."},
        "evidence": {"status": "all programs will be suspended in 2026"}, "confidence": 0.95,
        "summary": "Innoviris suspended the programme for 2026."})
    pages[br02["source_url"]] = PAGE_SUSPENDED
    rep = runmod.run(apply=True, only=["BR-02"], today=TODAY, fetcher=FakeFetcher(pages))
    assert [i["id"] for i in rep["applied"]] == ["BR-02"]
    after = {s["id"]: s for s in json.loads((project / "data" / "schemes.json").read_text())}
    assert after["BR-02"]["status"] == "Suspended"
    assert after["BR-02"]["last_verified"] == TODAY.isoformat()


def test_passed_deadline_is_cleared(project):
    data = json.loads((project / "data" / "schemes.json").read_text())
    next(s for s in data if s["id"] == "BR-02")["next_deadline"] = "2026-10-01"
    (project / "data" / "schemes.json").write_text(json.dumps(data))
    rep = runmod.run(apply=True, only=["BR-02"], today=TODAY, fetcher=FakeFetcher({}))
    assert rep["deadlines_passed"][0]["id"] == "BR-02"
    after = {s["id"]: s for s in json.loads((project / "data" / "schemes.json").read_text())}
    assert after["BR-02"]["next_deadline"] is None
