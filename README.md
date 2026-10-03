# Agentic RFP Evaluation & Supplier Ranking — Streamlit

A modular implementation of the classroom **Agentic RFP Evaluation and Supplier Ranking** project.

> **Reference Colab Notebook:** `Agentic_RFP_Evaluation_Cohere_LangGraph.ipynb`  
> **Streamlit Community Cloud:** `https://agentic-rfp-evaluation-rcds3cmg4yxggwubk7awvg.streamlit.app/`

This Streamlit application is the modular deployment implementation aligned with the supplied Colab reference notebook...

## Architecture

```text
Streamlit UI
    |
    v
LangGraph Orchestrator
    |
    +--> Criteria Tool --------> SQLite
    +--> Document Tool --------> PDF text/page extraction
    +--> Evaluation Agent -----> REAL Cohere LLM
    +--> Validation Tool ------> deterministic normalization
    +--> Scoring Tool ---------> deterministic weighted score
    +--> Ranking Tool ---------> benchmark + gap + relative % + PPI + tie-breaks
    +--> Persistence Tool -----> SQLite
```

**Important:** the Cohere LLM evaluates proposal content only. Python owns arithmetic, benchmarking, PPI, tie-breaking and final rank.

## Folder structure

```text
agentic_rfp_streamlit_v2/
├── app.py
├── config.py
├── .env.example
├── .gitignore
├── requirements.txt
├── agents/
│   ├── evaluation_agent.py
│   └── orchestrator_agent.py
├── tools/
│   ├── criteria_tool.py
│   ├── document_tool.py
│   ├── validation_tool.py
│   ├── scoring_tool.py
│   ├── ranking_tool.py
│   └── persistence_tool.py
├── services/
│   └── database_service.py
├── models/
│   └── schemas.py
├── ui/
│   └── dashboard.py
├── scripts/
│   ├── init_db.py
│   └── generate_sample_pdfs.py
├── tests/
│   └── test_tools.py
├── sample_data/
└── .streamlit/
    └── config.toml
```
## Dashboard 
<img width="2876" height="1462" alt="image" src="https://github.com/user-attachments/assets/10be4bb4-5fee-4423-adfa-a2ed7b188d8f" />


## 1. Create and activate virtual environment — Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

You should see `(.venv)` in the terminal prompt.

## 2. Install dependencies

```powershell
pip install -r requirements.txt
```

## 3. Configure Cohere

Create `.env` in the project root, beside `app.py`:

```env
COHERE_API_KEY=your_actual_cohere_api_key
COHERE_MODEL=command-a-plus-05-2026
RFP_DB_PATH=data/rfp_evaluation.db
LLM_TEMPERATURE=0
LLM_SEED=42
LLM_TIMEOUT_SECONDS=180
```

`.env` is ignored by Git. Commit `.env.example`, never the real key.

### Streamlit Community Cloud

Do not upload `.env`. Put the same values in **App → Settings → Secrets**:

```toml
COHERE_API_KEY = "your_actual_cohere_api_key"
COHERE_MODEL = "command-a-plus-05-2026"
RFP_DB_PATH = "data/rfp_evaluation.db"
LLM_TEMPERATURE = "0"
LLM_SEED = "42"
LLM_TIMEOUT_SECONDS = "180"
```

`config.py` reads Streamlit secrets first and local `.env`/environment variables second.

## 4. Initialize SQLite

```powershell
python scripts\init_db.py
```

## 5. Generate the four artificial supplier PDFs

```powershell
python scripts\generate_sample_pdfs.py
```

## 6. Run Streamlit

```powershell
streamlit run app.py
```

Open `http://localhost:8501`.

## Why the screen no longer appears frozen during Cohere evaluation

LLM calls are blocking network operations. The application now runs the LangGraph workflow in a worker thread while the Streamlit main thread polls a progress queue. The UI displays:

- current workflow stage
- current supplier
- progress bar
- completed stages
- final run ID
- errors without hiding the exception

There is also an explicit Cohere timeout configured by `LLM_TIMEOUT_SECONDS`.

The production workflow remains synchronous from the orchestrator's business perspective; the worker only prevents the browser UI from looking dead while the network call is in progress.

## Dashboard sections

### 🏠 Overview
Shows the active criteria, total weight, architecture and LLM/Python responsibility split.

### 🚀 Evaluate RFP
- Multiple PDF upload
- Supplier name
- Submission date
- Historical experience rating
- Active criteria snapshot
- PDF extraction pre-flight summary
- Real Cohere evaluation
- Live workflow progress

### 📄 Proposal Viewer
Shows extracted PDF content page-by-page, plus scorecard evidence and source pages.

### 🏆 Results Explorer
Shows:

- winner
- absolute score
- PPI
- supplier count
- leaderboard
- comparison chart
- detailed scorecard
- criterion score
- maximum score
- weight
- weighted contribution
- benchmark
- gap
- relative performance
- justification
- evidence
- evidence page
- risks
- warnings
- deterministic tie-break rule
- complete JSON download

### 🎯 Criteria Studio
Shows and edits the SQLite-backed criteria. Active weights must equal 100% before an evaluation can start.

### 🧾 Run Details
Shows `RFP_RUN_ID`, status, creation time, criteria snapshot, warnings and ranking explanation.

### 🧪 Validation Lab
Demonstrates malformed/out-of-range/missing LLM output normalization.


## Default criteria

| Criterion | Weight | Max |
|---|---:|---:|
| Technical Capability | 30% | 10 |
| Implementation Plan | 20% | 10 |
| Commercial Value | 20% | 10 |
| Security & Compliance | 20% | 10 |
| Support & Experience | 10% | 10 |

## Deterministic formulas

**Absolute weighted score**

```text
Σ ((criterion score / maximum score) × criterion weight)
```

**Benchmark** = highest valid supplier score for the criterion.

**Gap** = supplier score − benchmark.

**Relative performance**

```text
(score / benchmark) × 100
```

If benchmark is zero, the implementation safely avoids division by zero.

**PPI** = weighted average of criterion relative-performance percentages.

**Tie-break order**

1. Higher PPI
2. Earlier submission date
3. Higher historical experience rating
4. Supplier name ascending

Ranks are assigned only after this stable sort.

## Tests

```powershell
pytest -q
```

## Important security note

Never hard-code the Cohere API key in Python and never commit `.env` or `secrets.toml`.
