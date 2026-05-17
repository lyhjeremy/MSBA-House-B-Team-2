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

## Quick Start

### Prerequisites

| Requirement | Windows | macOS |
|---|---|---|
| Python version | 3.11 or 3.12 | 3.11 or 3.12 |
| OpenAI API key | Required (billing enabled, ~$5 credits) | Required (billing enabled, ~$5 credits) |

**Check your Python version:**

- **Windows (PowerShell):** `python --version`
- **macOS (Terminal):** `python3 --version`

If Python is not installed:
- **Windows:** Download from [python.org](https://www.python.org/downloads/) — check "Add Python to PATH" during installation
- **macOS:** Install via Homebrew: `brew install python@3.11` or download from [python.org](https://www.python.org/downloads/)

---

### Step 1 — Clone the repo

**Windows (PowerShell):**
```powershell
git clone https://github.com/lyhjeremy/MSBA-B2
cd MSBA-B2\SeeWeeS_Multi_Agent
```

**macOS (Terminal):**
```bash
git clone https://github.com/lyhjeremy/MSBA-B2
cd MSBA-B2/SeeWeeS_Multi_Agent
```

---

### Step 2 — Create and activate a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

> **Windows note:** If you get an error like *"running scripts is disabled on this system"*, run this first, then try again:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

**macOS (Terminal):**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Once activated, your terminal prompt should start with `(.venv)`.

---

### Step 3 — Install dependencies

**Windows & macOS (same command):**
```bash
pip install -r requirements.txt
```

> **macOS note:** If `pip` isn't found, use `pip3` instead.

---

### Step 4 — Install the headless browser for PDF export

This is a one-time install (~150 MB) used to export the HTML report to PDF.

**Windows & macOS (same command):**
```bash
playwright install chromium
```

> **macOS note:** If you see a permissions error, try: `python3 -m playwright install chromium`

---

### Step 5 — Configure your API key

**Windows (PowerShell):**
```powershell
copy .env.example .env
notepad .env
```

**macOS (Terminal):**
```bash
cp .env.example .env
open -e .env
```

In the `.env` file, replace the placeholder with your actual OpenAI API key:
```
OPENAI_API_KEY=sk-your-key-here
```

Save and close the file.

---

### Step 6 — Run the system

Make sure your virtual environment is active (you should see `(.venv)` in your prompt). Then:

**Windows (PowerShell):**
```powershell
python src/main.py
```

**macOS (Terminal):**
```bash
python src/main.py
```

**Demo mode** — engineered to trigger the audit-loop self-correction:

**Windows:**
```powershell
python src/main.py --demo-loop
```

**macOS:**
```bash
python src/main.py --demo-loop
```

Outputs land in `outputs/`:
- `dispatch_report_<timestamp>.html` — view in any browser
- `dispatch_report_<timestamp>.pdf` — one-page letter portrait, ready to share

---

## Standalone Tests (no OpenAI cost)

Each major component has a free test you can run to verify everything works before burning API credits.

**Windows (PowerShell):**
```powershell
python src/test_reconciliation.py
python src/test_weather.py
python src/test_allocator.py
python src/test_auditor.py
```

**macOS (Terminal):**
```bash
python src/test_reconciliation.py
python src/test_weather.py
python src/test_allocator.py
python src/test_auditor.py
```

What each test covers:
- `test_reconciliation.py` — Item Master reconciliation
- `test_weather.py` — Per-corridor weather (hits Open-Meteo only, no OpenAI)
- `test_allocator.py` — Resource allocator with mocked weather
- `test_auditor.py` — Auditor checks with mocked plans

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

## Project Structure

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
│   │   └── weather_tools.py              # Open-Meteo per waypoint, parallel
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

## License

Submitted for academic evaluation as part of UCLA MSBA Industry Seminar II (MGMTMSA413), Spring 2026.
