# SeeWeeS Multi-Agent Dispatch System

A LangGraph multi-agent system that turns the SeeWeeS Specialty linear ops-reporting prototype into a robust, self-correcting dispatch planner for time-critical pharmaceutical logistics.

**UCLA MSBA AI Agents Project Challenge 2026 · House B Team 2**

---

## What this system does

Every morning, a fictional pharmaceutical distributor named SeeWeeS Specialty has to commit to a 48-hour dispatch plan covering two delivery corridors (Newark → Boston and Newark → Philadelphia). The plan must respect:

- **Cold-chain constraints** — biologics like Pembrolizumab, Insulin Lispro, and a clinical-trial drug must travel on temperature-controlled trucks
- **Resource scarcity** — only 6 drivers, 4 standard trucks, and 2 reefer (refrigerated) trucks per day
- **Per-corridor weather risk** — a nor'easter hitting Providence affects Boston shipments but not Philadelphia
- **Asymmetric penalties** — missing a Tier 1 SLA costs 100 points, breaking cold-chain costs an extra 80 points, and the goal is to minimize total penalty
- **Messy upstream data** — shipment files arrive with missing IDs, legacy codes, and name typos that must be reconciled against an Item Master Appendix

Our system ingests messy CSV shipment data, reconciles it against a canonical item master, evaluates per-corridor weather across nine route waypoints in parallel, computes an optimal resource allocation, has the plan automatically audited against playbook safety rules, loops back to revise if the audit fails, and produces a one-page executive HTML/PDF report.

---

## Quick start

### Prerequisites
- Python 3.11 or 3.12
- An OpenAI API key with billing enabled (~$5 of credits is more than enough)

### Setup

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd MSBA_AI_Agents_Demo-data-enhancement-seewees

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install the headless browser used for PDF export (one-time, ~150MB)
playwright install chromium

# 5. Configure secrets
cp .env.example .env
# Open .env and paste your OpenAI API key
```

### Run

From the project root, with the venv active:

```bash
# Normal mode — audit usually passes on the first try
python src/main.py

# Demo mode — engineered to trigger the audit-loop self-correction
python src/main.py --demo-loop
```

Outputs land in `outputs/`:
- `dispatch_report_<timestamp>.html` — view in any browser
- `dispatch_report_<timestamp>.pdf` — one-page letter portrait, ready to share

---

## What's new vs. the baseline prototype

The starter repo was a strictly linear LangGraph DAG: PDF → CSV → weather → planner → report → email. Our enhanced system adds:

| Enhancement | What it does |
|---|---|
| **Item Master reconciliation** | Cleans messy item IDs against playbook Appendix A (canonical, alias, and legacy ID tables). 124/129 rows kept, 29 fixes applied. |
| **Per-corridor weather** | Calls Open-Meteo for each of 9 waypoints in parallel, then aggregates to corridor-day risk scores with travel-buffer policy. |
| **Multi-region resource allocator** *(Enhancement #5)* | Greedy priority-weighted allocator that minimizes the playbook's penalty score across both corridors and both days. |
| **Self-correction audit loop** *(Enhancement #1)* | A new `AuditorAgent` runs five deterministic checks against every plan; failures route back to the planner with structured feedback. Cyclic edge in the LangGraph. |
| **Executive HTML/PDF report** | Hand-crafted report template with deterministic data binding and LLM-narrated prose blocks. Auto-exports to a one-page letter-portrait PDF. |

See [`TECHNICAL.md`](TECHNICAL.md) for the full architecture and design rationale.

---

## Project structure

```
.
├── data/                                  # Original baseline data (kept for reference)
│   └── SeeWeeS Specialty distribution.pdf
├── data-for-enhancement/                  # Augmented data the project is built around
│   ├── Incoming_shipments_14d_multi_corridor.csv   # 130 rows × 14 days × 2 corridors
│   ├── Resource_availability_48h.csv               # 6 drivers, 4 std trucks, 2 reefers
│   └── SeeWeeS Specialty Dispatch Playbook.md
├── src/
│   ├── agents.py                          # Five LLM agents (Context, Ops, Planner, Report, + revision)
│   ├── auditor.py                         # Deterministic audit checks (the "self-correction" engine)
│   ├── graph.py                           # LangGraph orchestration with the cyclic audit loop
│   ├── main.py                            # Entry point; saves HTML + PDF
│   ├── prompts.py                         # All prompt templates
│   ├── tracing.py                         # LangSmith integration
│   ├── tools/
│   │   ├── allocator.py                   # Priority-weighted greedy allocator + penalty math
│   │   ├── corridors.py                   # Corridor catalog (waypoints + lat/lon)
│   │   ├── csv_tools.py                   # Wraps reconciliation for the OpsDataAgent
│   │   ├── email_tools.py                 # SMTP sender (optional, off by default)
│   │   ├── item_master.py                 # Canonical item tables hard-coded from playbook Appendix A
│   │   ├── pdf_exporter.py                # HTML → PDF via headless Chromium (Playwright)
│   │   ├── pdf_tools.py                   # PDF chunking + Chroma vector store (RAG)
│   │   ├── reconciliation.py              # The Item Master reconciliation engine
│   │   ├── report_renderer.py             # HTML template (CSS + deterministic data binding)
│   │   ├── resources.py                   # Loads Resource_availability_48h.csv
│   │   └── weather_tools.py               # Open-Meteo per waypoint, parallel
│   ├── test_allocator.py                  # Standalone test (no OpenAI calls)
│   ├── test_auditor.py                    # Standalone test (no OpenAI calls)
│   ├── test_reconciliation.py             # Standalone test (no OpenAI calls)
│   └── test_weather.py                    # Standalone test (no OpenAI calls)
├── outputs/                               # Generated reports (gitignored)
├── chroma_db/                             # Vector store cache (gitignored)
├── .env                                   # Secrets (gitignored)
├── .env.example                           # Template for .env
├── .gitignore
├── README.md                              # This file
├── TECHNICAL.md                           # Full technical & business write-up
└── requirements.txt
```

---

## Standalone tests (no OpenAI cost)

Each major component has a test you can run for free:

```bash
python src/test_reconciliation.py     # Item Master reconciliation
python src/test_weather.py            # Per-corridor weather (hits Open-Meteo only)
python src/test_allocator.py          # Resource allocator with mocked weather
python src/test_auditor.py            # Auditor checks with mocked plans
```

Useful for verifying the project works end-to-end before burning API credits.

---

## License

Submitted for academic evaluation as part of UCLA MSBA Industry Seminar II (MGMTMSA413), Spring 2026.
