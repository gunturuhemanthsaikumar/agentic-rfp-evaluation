# Agentic RFP Evaluation and Supplier Ranking

This project follows the supplied classroom brief with a minimal modular Python structure.

## Structure

```text
agentic_rfp_evaluation/
├── app.py                 # Streamlit UI
├── orchestrator.py        # controls workflow and tool order
├── document_tool.py       # PDF text extraction
├── evaluator.py           # REAL JSON-capable LLM call
├── validation.py          # schema validation + normalization
├── ranking.py             # deterministic scoring + benchmark + PPI + ranking
├── db.py                  # SQLite schema, criteria and persistence
├── seed_db.py             # create/seed SQLite database
├── requirements.txt
├── .env.example
├── sample_result.json
├── README.md
├── data/rfps/             # 4 artificial supplier PDFs
└── tests/test_core.py
```

## Setup

Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python seed_db.py
streamlit run app.py
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python seed_db.py
streamlit run app.py
```

## REAL LLM ONLY

There is no fake/demo scoring path.

This project uses Cohere as the real JSON-capable LLM.

For local development, create a `.env` file:

```env
COHERE_API_KEY=your_cohere_api_key
COHERE_MODEL=command-a-plus-05-2026

The endpoint is configurable for a compatible JSON-capable LLM. The request uses temperature 0 and JSON response format. Do not commit API keys. For Streamlit Community Cloud, use Streamlit Secrets.

## Criteria

Technical Capability 30%, Implementation Plan 20%, Commercial Value 20%, Security & Compliance 20%, Support & Experience 10%. Active weights must total 100%.

## Required formulas

```text
Absolute weighted score = Σ (criterion score / maximum score) × criterion weight
Criterion benchmark = highest valid score observed for that criterion
Criterion gap = supplier score - benchmark score
Relative performance % = (supplier score / benchmark score) × 100
PPI = weighted average of criterion relative-performance percentages
```

Zero benchmark handling is implemented defensively.

Tie-break order: higher PPI → earlier submission date → higher historical experience rating → supplier name ascending. Rank is assigned only after this sort.

## Workflow

```text
Setup → Input → Batch → Evaluate → Validate → Score → Benchmark → Rank → Persist → Present
```

The LLM judges proposal content and returns criterion-wise score, justification, supporting evidence, risks and summary. Python performs validation, all arithmetic, benchmarks, PPI, tie-breaks and final rank.

## Validation and testing

Missing criteria are filled with zero; malformed scores are handled; out-of-range scores are clipped; unknown/malformed criterion records generate warnings.

Run:

```bash
pytest -q
```

## Synthetic proposals

The four included fictional proposals are:

- Apex Systems — strong technical design and security; higher price; moderate delivery schedule.
- BrightPath Tech — lowest price and fast timeline; weak compliance detail and limited experience.
- NexaWorks — balanced proposal; strongest implementation plan and support model.
- Orbit Digital — strong experience and references; vague integration plan; medium pricing.

Each is 2–4 pages and contains the requested executive summary, solution, implementation/timeline/team, pricing assumptions, security/compliance/risk controls, support, experience and references.

## Streamlit screens

- Criteria: active criteria, weights and maximum scores.
- Supplier input: multiple PDF upload plus supplier name, submission date and historical experience rating.
- Leaderboard: rank, supplier, absolute score, PPI, submission date and experience.
- Detailed scorecard: criterion score, benchmark, gap, relative %, weight, evidence and justification.
- Run details: RFP_RUN_ID, warnings, tie-break explanation and JSON download.

## Deployment

Push the project to GitHub and deploy `app.py` on Streamlit Community Cloud. Add the three LLM settings as Streamlit Secrets. Do not commit secrets.
