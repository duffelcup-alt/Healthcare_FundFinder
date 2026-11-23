"""Writes data/applications.json: what each application pack contains.

Sections map to fields of the shared project file (see PROJECT_FIELDS).
Documents can have a condition: "starter" (company < 3 years),
"difficulty" (company in difficulty), "partners" (has partners).
Sources are the official pages listed per scheme. Run:  python data/make_applications.py
"""
import json
from pathlib import Path

PROJECT_FIELDS = [
    ("title", "Project title", "short"),
    ("summary", "Summary in 3-5 sentences", "long"),
    ("need", "Problem or unmet medical need", "long"),
    ("solution", "Your solution and what is new about it", "long"),
    ("state_of_art", "State of the art and competing solutions", "long"),
    ("risks", "Technical uncertainties and risks", "long"),
    ("workplan", "Work plan: work packages, milestones, deliverables", "long"),
    ("team", "Team and key expertise", "long"),
    ("partners", "Partners and subcontractors, and their role", "long"),
    ("market", "Market, customers and users", "long"),
    ("business_model", "Business model and route to market", "long"),
    ("valorisation", "Expected impact in the region: jobs, investment, revenue (5 years)", "long"),
    ("regulatory", "Regulatory and clinical path (e.g. MDR/IVDR class, CE marking, studies)", "long"),
    ("ip", "Intellectual property position", "long"),
    ("financing", "How you will finance your own share", "long"),
    ("sustainability", "Contribution to sustainable development", "long"),
    ("start_date", "Planned start date", "date"),
]
COST_LINES = [
    ("c_personnel", "Personnel"),
    ("c_subcontract", "Subcontracting and external services"),
    ("c_equipment", "Equipment and investment (or depreciation)"),
    ("c_operating", "Operating costs (materials, consumables)"),
    ("c_other", "Other costs and overheads"),
]

VLAIO_PORTAL = "VLAIO online application portal (log in with eID or another Flemish government login)"
VLAIO_DOCS = [
    {"t": "Form 'Bepaling grootte onderneming' (company size) with its annexes"},
    {"t": "Application template: the version for requested support up to EUR 500,000 or above"},
    {"t": "Project budget in VLAIO's Excel template, with evidence for external services"},
    {"t": "Annex for international or interregional projects", "if": "partners"},
    {"t": "Monthly cash-flow plan in VLAIO's template (SMEs under 3 years)", "if": "starter"},
    {"t": "Interim balance sheet and P&L for the last closed quarter", "if": "starter"},
    {"t": "Bank statement showing the balance on the cash-flow plan's start date", "if": "starter"},
    {"t": "Internal balance sheet and P&L for the last closed financial year", "if": "starter"},
    {"t": "Notarial deeds of capital operations after the last filed annual accounts", "if": "starter"},
    {"t": "Remediation plan (companies in difficulty)", "if": "difficulty"},
]
VLAIO_STEPS = [
    "Gather the documents and determine your company size with VLAIO's form.",
    "Register a pre-application in the VLAIO portal, complete it (with partners, if any) and submit. Nothing can be changed after submission, and choose Dutch or English at registration: it can't be changed later.",
    "VLAIO checks admissibility and invites you to an explanation meeting, usually within about 2 weeks. You must convince them of your business case here.",
    "The project is scored on the evaluation criteria. A 'critical' score on any criterion, or below -2 on an axis, means no support.",
    "Decision by the FIO committee by email and e-box. The legal maximum is 18 weeks after submission.",
    "If approved: support agreement, possibly with conditions, then reporting during the project.",
]

APPS = {
    "VL-01": {
        "portal": "Through a VLAIO partner, then the VLAIO online portal",
        "contact": "A VLAIO partner such as Agoria, Voka or Sirris (health and medtech)",
        "limits": "Fixed grant of EUR 50,000; project 6-12 months; effort of at least one person-year or EUR 70,000.",
        "steps": [
            "Contact one of the VLAIO partners and present your plan; ask how they select candidates.",
            "The partner decides whether to put you forward; each partner can nominate only a few starters.",
            "If selected, you get access to the online portal to complete the application.",
            "Pitch to a jury: at most 15 minutes plus Q&A, 45 minutes in total.",
            "Decision, then the 6-12 month project with a proof of business as deliverable.",
        ],
        "docs": [
            {"t": "Application in the VLAIO portal (after nomination)"},
            {"t": "Project plan with deliverables, including a proof of business"},
            {"t": "Budget showing at least one person-year or EUR 70,000 of effort"},
            {"t": "Pitch deck for the jury (max 15 minutes)"},
        ],
        "sections": [
            {"h": "The starter and team", "g": "Why this team can pull it off: skills, network, commitment.", "f": ["team"]},
            {"h": "Problem and innovation", "g": "The pioneering role you aim for in your market, and what's new.", "f": ["need", "solution", "state_of_art"]},
            {"h": "Proof of business: market and customers", "g": "Proof of business is required; a proof of concept alone isn't enough.", "f": ["market", "business_model"]},
            {"h": "6-12 month plan and deliverables", "g": "Concrete milestones and the uncertainties the project resolves.", "f": ["workplan", "risks"]},
            {"h": "Ambition and growth", "g": "High potential and matching ambition.", "f": ["valorisation"]},
            {"h": "Budget and financing", "g": "Effort of at least one person-year or EUR 70,000.", "f": ["financing"]},
        ],
        "calc": "vl01",
        "source": "https://vlaio.be/en/subsidies/support-innovative-starters/how-apply-support-innovative-starters",
    },
    "VL-02": {
        "portal": VLAIO_PORTAL,
        "contact": "VLAIO: bedrijfsinnovatiesteun@vlaio.be or 0800 20 555",
        "limits": "Max 30 pages for support up to EUR 500,000 (40 above), plus 5 per extra business partner. One language: Dutch or English.",
        "steps": VLAIO_STEPS,
        "docs": VLAIO_DOCS,
        "sections": [
            {"h": "Summary", "g": "What you will develop, for whom, and why now.", "f": ["title", "summary"]},
            {"h": "Business case: market analysis", "g": "A solid market analysis.", "f": ["market"]},
            {"h": "Business case: added value and market position", "g": "Clear added value for customers and the effect on your market position.", "f": ["solution", "business_model"]},
            {"h": "Business case: costs, benefits and fit with strategy", "g": "A realistic view of future costs and benefits, and how success strengthens your position in the short term.", "f": ["business_model", "financing"]},
            {"h": "Added value for Flanders", "g": "Valorisation in Flanders of at least 10x the subsidy within 5 years after the project: investment, jobs or productivity growth. Social impact can earn extra points.", "f": ["valorisation"]},
            {"h": "Innovation: new for company and sector", "g": "Clearly beyond routine renewal or incremental improvement of existing know-how.", "f": ["state_of_art", "solution"]},
            {"h": "Objectives, approach and work plan", "g": "Clear, verifiable objectives and an adequate approach with the right resources.", "f": ["workplan"]},
            {"h": "Challenges and risks", "g": "The real, identified challenges and how you'll address them.", "f": ["risks"]},
            {"h": "Team and expertise", "g": "Suitable people with the necessary expertise.", "f": ["team", "partners"]},
            {"h": "Regulatory and clinical path", "g": "Not a VLAIO heading, but assessors of health projects will ask about it.", "f": ["regulatory"]},
            {"h": "Intellectual property", "g": "Freedom to operate and how you protect results.", "f": ["ip"]},
        ],
        "calc": "vl02",
        "source": "https://www.vlaio.be/nl/subsidies-financiering/ontwikkelingsproject/wie-komt-aanmerking-en-onder-welke-voorwaarden",
    },
    "VL-03": {
        "portal": VLAIO_PORTAL,
        "contact": "VLAIO: bedrijfsinnovatiesteun@vlaio.be or 0800 20 555",
        "limits": "Same page limits and documents as a development project. Support EUR 100,000 to EUR 3,000,000; up to 36 months.",
        "steps": VLAIO_STEPS,
        "docs": VLAIO_DOCS,
        "sections": [
            {"h": "Summary", "g": "The knowledge you need and why the company needs it.", "f": ["title", "summary"]},
            {"h": "Research objectives and state of the art", "g": "The new knowledge the project builds, compared with the state of the art.", "f": ["state_of_art", "need"]},
            {"h": "Research approach and work plan", "g": "Methods, work packages, milestones and verifiable objectives.", "f": ["workplan"]},
            {"h": "Risks and challenges", "g": "Why the risk is too high for a development project. Any development activities must also be justified as beyond routine.", "f": ["risks"]},
            {"h": "Valorisation path", "g": "How the results lead to products or services, and the impact in Flanders.", "f": ["solution", "market", "valorisation"]},
            {"h": "Team, partners and expertise", "g": "Suitable people and research partners.", "f": ["team", "partners"]},
            {"h": "Regulatory and clinical path", "g": "Expected for health projects.", "f": ["regulatory"]},
            {"h": "Intellectual property", "g": "Protection and ownership of results.", "f": ["ip"]},
            {"h": "Financing", "g": "Your capacity to co-finance; VLAIO may ask for a cash-flow plan.", "f": ["financing"]},
        ],
        "calc": "vl03",
        "source": "https://www.vlaio.be/nl/subsidies-financiering/onderzoeksproject/voorwaarden-om-aanmerking-te-komen-voor-de-subsidie",
    },
    "VL-04": {
        "portal": "Biovia project call (intention and abstract), then the VLAIO instrument Biovia advises",
        "contact": "Biovia, via biovia.be; check the call regulations there",
        "limits": "Consortium of at least 3 partners including Biovia members. Call 2026.2: EUR 8 million in total.",
        "steps": [
            "Follow the info webinar and read the call regulations on biovia.be.",
            "Form a consortium of at least 3 partners (industry, research institutes, hospitals, care organisations).",
            "Submit the intention to submit (2026.2: by 15 September 2026).",
            "Submit the abstract (2026.2: by 12 November 2026).",
            "Receive written jury feedback (2026.2: 18 December 2026).",
            "Submit the full proposal under the VLAIO instrument Biovia advises (research, development, feasibility, ICON, cSBO...).",
        ],
        "docs": [
            {"t": "Intention to submit"},
            {"t": "Abstract"},
            {"t": "Full proposal in the format of the chosen VLAIO instrument"},
            {"t": "Budget per partner"},
            {"t": "Consortium agreement (before the project starts)", "if": "partners"},
        ],
        "sections": [
            {"h": "Unmet medical need", "g": "A clearly defined unmet need in healthcare.", "f": ["need"]},
            {"h": "Solution and innovation", "g": "A disruptive solution, compared with what exists.", "f": ["solution", "state_of_art"]},
            {"h": "Consortium and complementarity", "g": "Why these partners, and what each brings (sectors: medical biotech, medtech, digital health).", "f": ["partners", "team"]},
            {"h": "Work plan", "g": "Work packages per partner, milestones.", "f": ["workplan", "risks"]},
            {"h": "Regulatory and clinical path", "g": "Route to patients and payers.", "f": ["regulatory"]},
            {"h": "Impact in Flanders", "g": "A quantifiable increase in investment and jobs in Flanders.", "f": ["valorisation", "market"]},
            {"h": "Budget and financing per partner", "g": "Rates depend on the instrument and partner type.", "f": ["financing"]},
        ],
        "calc": "vl04",
        "source": "https://www.uhasselt.be/en/calls-research/detail/1770-vlaio-biovia-project-call-2026-2",
    },
    "WA-01": {
        "portal": "ONTIME platform of SPW Recherche (PROJECT axis, Win4Company)",
        "contact": "win4company.recherche@spw.wallonie.be, +32 81 77 86 73",
        "limits": "Open all year; decided by a selection committee that meets at set intervals.",
        "steps": [
            "Submit a declaration of intent and ask for a meeting with a technical officer (win4company.recherche@spw.wallonie.be).",
            "Present the project to the technical officer to discuss whether the requested funding fits.",
            "Submit the final proposal on ONTIME: the form plus the budget annexes.",
            "A technical officer reviews the project and a financial officer checks your financial capacity; they may ask for more information.",
            "The selection committee (administration and minister's office) decides.",
            "If approved: agreement and a first advance, then expense statements and reports.",
        ],
        "docs": [
            {"t": "Win4Company declaration of intent"},
            {"t": "Win4Company RD project description"},
            {"t": "Annex 1: aid received"},
            {"t": "Annex 2: RD Gantt chart"},
            {"t": "Annex 3: RD budget"},
            {"t": "ONTIME application form"},
            {"t": "Read the Win4Company vademecum before writing"},
        ],
        "sections": [
            {"h": "Innovative character", "g": "What is new compared with the state of the art.", "f": ["solution", "state_of_art"]},
            {"h": "Type of research", "g": "Say which parts are industrial research (grant) and which are experimental development (repayable advance). Routine changes are excluded.", "f": ["workplan"]},
            {"h": "Quality, feasibility and fit with Walloon needs", "g": "Technical feasibility and relevance to the Region's technical and economic needs.", "f": ["workplan", "team"]},
            {"h": "Ability to exploit the results", "g": "The product, process or service you'll sell, and how.", "f": ["market", "business_model", "valorisation"]},
            {"h": "Sustainable development", "g": "Contribution to sustainable development.", "f": ["sustainability"]},
            {"h": "Financial capacity", "g": "How you meet current and foreseeable needs or find complementary financing.", "f": ["financing"]},
            {"h": "Risk level", "g": "A clearly identifiable level of risk.", "f": ["risks"]},
            {"h": "Regulatory and clinical path", "g": "Useful context for health projects.", "f": ["regulatory"]},
        ],
        "calc": "wa01",
        "source": "https://www.wallonie.be/fr/demarches/144189",
    },
    "WA-02": {
        "portal": "ONTIME platform of SPW Recherche (Win4Expertise, technical support)",
        "contact": "win4expertise.recherche@spw.wallonie.be, 081 33 44 84",
        "limits": "75% of the subcontracting cost; at most EUR 200,000 per company over 3 calendar years together with Win4Expertise marketing advice. Study of 6-24 months. Preclinical and clinical tests are excluded.",
        "steps": [
            "Agree the work with an approved research centre, public research body or university/college unit, and get a quote.",
            "Submit the electronic application form on ONTIME (no deadline).",
            "Decision usually 3 to 6 months after submission.",
            "If approved and budget is available, sign the agreement with the Walloon Region.",
        ],
        "docs": [
            {"t": "ONTIME application form"},
            {"t": "Quote(s) from the research provider(s), at market prices"},
        ],
        "sections": [
            {"h": "Innovative character", "g": "The new knowledge the study brings.", "f": ["solution", "state_of_art"]},
            {"h": "The technical work and provider", "g": "Analyses, measurements or tests, and who does them. Not preclinical/clinical tests, not recurring tests, not bringing a product up to new standards.", "f": ["workplan", "partners"]},
            {"h": "Fit with your strategy and Walloon needs", "g": "", "f": ["business_model"]},
            {"h": "Economic and employment value", "g": "", "f": ["valorisation", "market"]},
            {"h": "Sustainable development", "g": "Must be favourable or neutral.", "f": ["sustainability"]},
            {"h": "Risk level", "g": "A clearly evident level of risk.", "f": ["risks"]},
            {"h": "Financing", "g": "How you finance current and foreseeable needs.", "f": ["financing"]},
        ],
        "calc": "wa02",
        "source": "https://www.wallonie.be/fr/demarches/144224",
    },
}

if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "applications.json"
    out.write_text(json.dumps({"fields": PROJECT_FIELDS, "costs": COST_LINES, "apps": APPS},
                              indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out} with {len(APPS)} application packs")
