# Confidential Document Analyst

A local-first forensic analysis tool that scans sensitive communications — chat logs, emails, PDFs — for indicators of trafficking, abuse, scams, and coercion. All inference runs entirely on-device using a 1.2B parameter language model via the [Cactus Compute Engine](https://github.com/cactus-compute). No data ever leaves the machine.

Users create a case, upload files, and the system produces a structured forensic report based on the [Sheffield STIM Matrix](https://www.sheffield.ac.uk/research/new-tool-protecting-individuals-risk-human-trafficking) — ready to hand to a legal representative or safeguarding professional.

Built for the Cactus x DeepMind Hackathon (February 2026).

## How It Works

```
Upload files ──> Parse & chunk ──> On-device LLM ──> STIM scoring ──> Forensic report
  (chat, email,     (6-message        (LFM2.5-1.2B      (4-pillar        (Markdown +
   PDF, text)        windows)          via Cactus)        0-10 scores)     evidence)
```

1. **Parse** — Auto-detects format (WhatsApp, iMessage, email, PDF, plain text) and normalizes into message sequences
2. **Chunk** — Splits into overlapping windows of 6 messages for focused analysis
3. **Analyse** — Each chunk is sent to the on-device LLM with a STIM-aligned forensic prompt
4. **Classify** — Keyword-based classification assigns category (threat, scam, abuse, pattern) and severity
5. **Score** — Findings are scored against the four STIM pillars: Language-Based Vulnerability, Third-Party Control, Psychological Isolation, Financial Coercion
6. **Report** — Generates a structured forensic report with evidence citations, pillar breakdown, chain of custody, and recommended actions

## Example Output

```
STIM Rating: 98% (CRITICAL RISK)

| # | Pillar                       | Score          | Rating   |
|---|------------------------------|----------------|----------|
| 1 | Language-Based Vulnerability | ██████████ 10  | CRITICAL |
| 2 | Third-Party Control          | ██████████ 10  | CRITICAL |
| 3 | Psychological Isolation      | █████████░ 9   | CRITICAL |
| 4 | Financial Coercion           | ██████████ 10  | CRITICAL |

Finding 1 — Abuse / Control | Risk: HIGH | Pillars: Vulnerability, Control, Isolation
> "I'm sending over a confidential briefing on the Helmand mineral investment
>  routes. J needs to see this before we meet his associates at the Raffles
>  in Singapore next month."
```

Full example reports are generated in `examples/output/` when running the test suite.

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| On-device model | LFM2.5-1.2B-Instruct via Cactus | Local inference (no cloud) |
| Backend | FastAPI + SQLite | API, file storage, analysis orchestration |
| Frontend | React 19 + TypeScript + Tailwind v4 + shadcn/ui | Case management UI |
| Desktop | pywebview | Native window wrapping |
| PDF parsing | pypdf | Extract text from PDF documents |

## Prerequisites

- Python 3.12 ([uv](https://docs.astral.sh/uv/) for environment management)
- [Bun](https://bun.sh/) (frontend package manager)
- Cactus SDK with `libcactus.dylib` built (see `cactus/` submodule)
- LFM2.5-1.2B-Instruct model weights in one of:
  - `.venv/lib/python3.12/weights/lfm2.5-1.2b-instruct/`
  - `cactus/weights/lfm2.5-1.2b-instruct/`
  - `~/.cactus/models/lfm2.5-1.2b-instruct/`

## Getting Started

```bash
# Clone with submodules
git clone --recursive <repo-url>
cd cactusxdeepmind-app

# Install Python dependencies
uv sync

# Install frontend dependencies
cd frontend && bun install && cd ..

# Build the frontend
cd frontend && bun run build && cd ..

# Run the app (production mode — pywebview + uvicorn)
uv run python app.py
```

### Development Mode

Run three processes:

```bash
# Terminal 1: Vite dev server (hot reload)
cd frontend && bun run dev

# Terminal 2: FastAPI backend (auto-reload)
uv run uvicorn api:app --reload

# Terminal 3: pywebview window pointing at Vite
uv run python dev.py
```

### Running the Test Suite

The test suite processes example cases through the full pipeline and generates forensic reports.

```bash
# Run all 4 example cases
uv run python tests/run_examples.py

# Quick run (case_01 only, verbose output)
uv run python tests/run_examples.py --quick

# Run a specific case
uv run python tests/run_examples.py case_04 -v
```

Reports are saved to `examples/output/<case_name>/report.md`.

## Project Structure

```
.
├── api.py                  # FastAPI endpoints: cases, files, analysis, reports
├── analyzer.py             # Pipeline: parse -> chunk -> LLM -> classify -> store
├── hybrid.py               # Local inference wrapper with STIM system prompt
├── inference.py            # Cactus SDK interface (model load, complete, reset)
├── models.py               # Pydantic models and enums
├── db.py                   # SQLite schema + CRUD
├── parsers.py              # Format detection + parsing (WhatsApp, email, PDF, etc.)
├── report.py               # STIM forensic report generator (Markdown)
├── analysis_tools.py       # Tool schemas for structured analysis
├── app.py                  # Production entry (pywebview + uvicorn)
├── dev.py                  # Dev entry (pywebview -> Vite)
├── main.py                 # Benchmark-compatible inference wrapper
├── frontend/               # React + TypeScript + Tailwind v4 + shadcn/ui
│   └── src/components/     # CaseSidebar, FileDropZone, FindingCard, ReportPreview, etc.
├── examples/
│   ├── case_01/            # Agency scouting / trafficking scenario
│   ├── case_02/            # Domestic abuse (WhatsApp logs)
│   ├── case_03/            # Investment scam (emails + victim notes)
│   ├── case_04/            # Institutional misconduct (comms + restricted PDF)
│   └── output/             # Generated forensic reports
├── tests/
│   └── run_examples.py     # Test scaffold: process example cases end-to-end
├── cactus/                 # Cactus SDK (submodule)
└── data/                   # Runtime SQLite DB + uploads (gitignored)
```

## Supported File Formats

| Format | Extensions | Detection |
|--------|-----------|-----------|
| WhatsApp export | `.txt` | Timestamp pattern (`1/15/24, 2:30 PM - Sender: ...`) |
| Email | `.eml` | MIME headers (From, To, Subject, Content-Type) |
| iMessage export | `.txt` | Structured From/To/Date headers |
| PDF | `.pdf` | File extension; text extracted via pypdf |
| Plain text | `.txt`, any | Fallback; parses `Name: message` patterns or line-by-line |

## STIM Matrix

The report format is based on the [Sheffield STIM (Sexual Trafficking Identification Matrix)](https://www.sheffield.ac.uk/research/new-tool-protecting-individuals-risk-human-trafficking), developed by Dr. Xavier L'Hoiry at the University of Sheffield and adopted as national best practice by UK police forces including Thames Valley Police (Operation Yale).

The system evaluates communications across four risk pillars:

| Pillar | What it detects |
|--------|----------------|
| **Language-Based Vulnerability** | Grooming, flattery, false promises, emotional manipulation |
| **Third-Party Control** | Instructions, demands, restricting movement, authority abuse |
| **Psychological Isolation** | Cutting off support networks, enforcing secrecy, gaslighting |
| **Financial Coercion** | Debt traps, withholding pay, threats over money |

Each pillar is scored 0-10 based on keyword matching and finding severity. The combined score produces a STIM probability rating:

- **70-100%** — CRITICAL RISK
- **50-69%** — HIGH RISK
- **30-49%** — MEDIUM RISK
- **0-29%** — LOW RISK

## Report Structure

Generated reports follow a legal dossier format:

1. **Executive Summary** — Case overview with STIM probability rating
2. **STIM Analysis** — Four-pillar score table with visual bars
3. **Key Findings** — Each finding with quoted evidence, risk level, and triggered pillars
4. **Chain of Custody** — Source files, processing method, finding count
5. **Recommended Actions** — Context-sensitive next steps based on risk level
6. **Appendix** — Full on-device model elaborations per finding
7. **Integrity Hash** — SHA-256 hash for tamper-evidence

## Privacy

- All analysis runs 100% on-device. No data is sent to any cloud service.
- The model (LFM2.5-1.2B-Instruct) runs locally via the Cactus Compute Engine.
- Runtime data (SQLite DB, uploaded files) is stored in `data/` and never transmitted.
- The privacy indicator in the UI confirms local-only processing throughout.

## License

Hackathon project. See individual dependencies for their respective licenses.
