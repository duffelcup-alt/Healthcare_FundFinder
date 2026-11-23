"""Writes data/criteria.json: the eligibility checklist for every scheme.

Each criterion: {"t": text, "key": knock-out?, "r": rule}
Rules (evaluated in the browser against the profile):
  ["in", field, [values]]   field value must be one of the list
  ["is", field, "yes"|"no"] yes/no question with "unknown" allowed
  ["min", field, n] / ["max", field, n] / ["range", field, lo, hi]   numbers; 0/empty = unknown
  ["calc", name]            scheme-specific calculation (see template.html)
  ["manual"]                the applicant ticks it themselves after checking
Edit this file, then run:  python data/make_criteria.py
"""
import json
from pathlib import Path

FL, BR, WA = ["Flanders"], ["Brussels"], ["Wallonia"]
SME = ["micro", "small", "medium"]
HEALTH = ["medtech", "biotech", "digital"]


def c(t, r, key=True):
    return {"t": t, "key": key, "r": r}


def region(name):
    return c(f"Main site or operating activities in {name[0]}", ["in", "region", name])


NOT_DIFFICULTY = c("Not a company in difficulty (EU definition)", ["is", "in_difficulty", "no"])
LEGAL = c("A company with legal personality (e.g. BV/SRL, NV/SA)", ["is", "legal_entity", "yes"])
COFUND = c("Can finance its own share of the project costs", ["is", "cofund", "yes"])
NOT_STARTED = c("Project not started yet: costs made before the start date are not funded", ["is", "project_started", "no"])

CRITERIA = {
    # ---------------- FEDERAL ----------------
    "FED-01": [
        c("Employs researchers on a research or development project", ["is", "researchers", "yes"]),
        c("Researchers hold a qualifying master's or PhD (bachelor's diplomas count in a capped way)", ["manual"]),
        c("Project or programme registered with BELSPO before applying the exemption", ["manual"]),
        c("Young Innovative Company variant possible (small company under 10 years)", ["calc", "yic"], key=False),
    ],
    "FED-02": [
        c("Subject to Belgian corporate tax", ["is", "legal_entity", "yes"]),
        c("Earns income from qualifying IP (patent, SPC, copyrighted software from R&D, orphan drug)", ["is", "ip_income", "yes"]),
        c("Software was developed in an R&D project (if claiming for software)", ["manual"], key=False),
    ],
    "FED-03": [
        c("Company is at most 4 years old", ["max", "age", 4]),
        c("Micro company (45% for investors) or small company (30%)", ["in", "size", ["micro", "small"]]),
        LEGAL,
        c("Raises at most EUR 500,000 in total through the Tax Shelter", ["manual"], key=False),
        c("Investors are private persons who pay Belgian income tax and keep the shares 4 years", ["manual"], key=False),
    ],
    "FED-04": [
        c("Company is 5 to 10 years old", ["range", "age", 5, 10]),
        c("SME (not a large company)", ["in", "size", SME]),
        LEGAL,
    ],
    "FED-05": [
        c("Invests in patents or in environment-friendly R&D assets", ["manual"]),
        c("Has taxable profit to deduct from, or opts for the R&D tax credit", ["manual"], key=False),
    ],
    "FED-06": [
        c("Project about the use or governance of health data", ["manual"]),
        c("Works with at least one partner organisation", ["min", "partners", 1]),
    ],
    # ---------------- FLANDERS ----------------
    "VL-01": [
        region(FL),
        c("Small enterprise (micro or small)", ["in", "size", ["micro", "small"]]),
        c("Not listed on a stock exchange", ["is", "listed", "no"]),
        c("Has not distributed profits", ["is", "profits_distributed", "no"]),
        c("Did not take over another company's activity and did not come from a merger or acquisition", ["is", "from_merger", "no"]),
        c("No earlier VLAIO R&D subsidy (development/research project, feasibility study, ICON, Baekeland...)", ["is", "prior_vlaio_rd", "no"]),
        c("Project needs at least one person-year or EUR 70,000 of effort", ["min", "budget", 70000]),
        c("Project runs 6 to 12 months", ["range", "months", 6, 12]),
        c("Put forward by a VLAIO partner (e.g. Agoria, Voka, Sirris)", ["manual"]),
        c("Deliverables include a proof of business (proof of concept alone is not enough)", ["manual"], key=False),
    ],
    "VL-02": [
        region(FL), LEGAL, NOT_DIFFICULTY,
        c("Requested support between EUR 25,000 and EUR 3,000,000", ["calc", "vl02"]),
        NOT_STARTED,
        c("Duration up to 36 months on the conditions page (VLAIO's database says 24: confirm with VLAIO)", ["max", "months", 36]),
        COFUND,
        c("Valorisation in Flanders of at least 10x the subsidy within 5 years (jobs, investment or productivity)", ["manual"]),
        c("Development is new for the company and its sector, clearly beyond routine improvement", ["manual"]),
    ],
    "VL-03": [
        region(FL), LEGAL, NOT_DIFFICULTY,
        c("Requested support between EUR 100,000 and EUR 3,000,000", ["calc", "vl03"]),
        NOT_STARTED,
        c("Duration up to 36 months", ["max", "months", 36]),
        COFUND,
        c("Research builds new knowledge with risks too high for a development project", ["manual"]),
    ],
    "VL-04": [
        region(FL),
        c("Consortium of at least 3 partners (you plus 2 or more)", ["min", "partners", 2]),
        c("Consortium includes Biovia members", ["is", "biovia_member", "yes"]),
        c("Project in medical biotech, medtech or digital health", ["in", "focus", HEALTH]),
        c("Addresses a clearly defined unmet medical need", ["manual"]),
        c("Fits one of the Biovia roadmap topics", ["manual"], key=False),
    ],
    "VL-05": [
        region(FL),
        c("Works with a university or research institution", ["is", "uni", "yes"]),
        c("A PhD candidate admitted to a doctoral programme will do the research", ["manual"]),
        COFUND,
    ],
    "VL-06": [
        region(FL),
        c("Works with a university or research institution", ["is", "uni", "yes"]),
        c("A postdoctoral researcher (PhD) leads the transfer or spin-off", ["manual"]),
    ],
    "VL-07": [
        region(FL),
        c("SME (large companies only for investments in development zones)", ["in", "size", SME]),
        c("A strategic investment or training project (innovation, internationalisation, sustainability)", ["manual"]),
        c("The investment receives no other state aid", ["manual"]),
    ],
    "VL-08": [
        region(FL),
        c("SME", ["in", "size", SME]),
        c("Training, or cybersecurity advice, from a registered provider", ["manual"]),
    ],
    "VL-09": [region(FL), c("SME", ["in", "size", SME])],
    # ---------------- BRUSSELS ----------------
    "BR-01": [
        region(BR),
        c("Start-up (micro or small company)", ["in", "size", ["micro", "small"]]),
        NOT_DIFFICULTY,
        c("Has a Strategic Innovation Plan to fund", ["manual"]),
    ],
    "BR-02": [
        region(BR), COFUND,
        c("Develops an innovative product, process or service", ["manual"]),
    ],
    "BR-03": [
        region(BR),
        c("Partners with a Brussels research organisation", ["is", "uni", "yes"]),
        c("R&D activities of the company are in Brussels", ["manual"]),
    ],
    "BR-04": [region(BR), c("Needs a technical feasibility study before an R&D project", ["manual"])],
    "BR-05": [
        region(BR),
        c("Very small enterprise", ["in", "size", ["micro"]]),
        c("Applies before costs are made and before the assignment starts", ["is", "project_started", "no"]),
        c("Sector is not excluded", ["manual"]),
    ],
    # ---------------- WALLONIA ----------------
    "WA-01": [
        region(WA),
        c("Commercial company registered in the Crossroads Bank for Enterprises", ["is", "legal_entity", "yes"]),
        NOT_DIFFICULTY,
        c("Up to date with VAT, social security (ONSS) and the Region", ["is", "tax_compliant", "yes"]),
        c("The project has not already received public funding", ["is", "prior_public_funding", "no"]),
        c("Industrial research or experimental development towards a product, process or service you will sell", ["manual"]),
        c("Can meet current and foreseeable financial needs, or find complementary financing", ["is", "cofund", "yes"]),
    ],
    "WA-02": [
        region(WA),
        c("SME (EU definition)", ["in", "size", SME]),
        c("Commercial company registered in the Crossroads Bank for Enterprises", ["is", "legal_entity", "yes"]),
        NOT_DIFFICULTY,
        c("The work is not preclinical or clinical testing (excluded)", ["is", "clinical_tests", "no"]),
        c("Work done by an approved research centre, public research body or university/college unit", ["manual"]),
        c("Study runs 6 to 24 months", ["range", "months", 6, 24]),
        c("With Win4Expertise marketing advice: at most EUR 200,000 aid per company over 3 calendar years", ["calc", "wa02"], key=False),
    ],
    "WA-03": [
        region(WA),
        c("Led by a university or college research unit", ["is", "uni", "yes"]),
        c("Researcher works full-time on the project and had no earlier FIRST Spin-off/Win4SpinOff contract", ["manual"]),
    ],
    "WA-04": [
        region(WA),
        c("A university unit is the promoter", ["is", "uni", "yes"]),
        c("Supported by an existing company with a Walloon operating site", ["is", "legal_entity", "yes"]),
        c("Fits the call's theme (2026: DIS 2 'Innovations for stronger health')", ["manual"]),
    ],
    "WA-05": [
        region(WA),
        c("Collaborative project with at least one partner", ["min", "partners", 1]),
        c("Project in biopharma/biotech, medtech or e-health", ["in", "focus", HEALTH]),
        c("Coordinated by a company", ["manual"]),
    ],
    "WA-06": [
        region(WA),
        c("Early-stage start-up (micro or small)", ["in", "size", ["micro", "small"]]),
        c("Innovative tech start-up at an early stage", ["manual"]),
    ],
    "WA-07": [
        region(WA),
        c("Independent or SME, not a non-profit", ["in", "size", SME]),
        c("Stays under the de minimis ceiling for state aid", ["manual"], key=False),
    ],
}

if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "criteria.json"
    ids = {s["id"] for s in json.loads((out.parent / "schemes.json").read_text(encoding="utf-8"))}
    missing = ids - set(CRITERIA)
    assert not missing, f"no criteria for {missing}"
    out.write_text(json.dumps(CRITERIA, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out} for {len(CRITERIA)} schemes")
