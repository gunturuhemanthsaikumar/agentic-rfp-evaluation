# Agentic RFP Evaluation & Supplier Ranking — Modular Streamlit Application

This project implements the supplied classroom brief and aligns the Streamlit application with the Cohere + LangGraph Colab reference.

The code separates **orchestration, LLM reasoning, deterministic tools, persistence, and UI**.

```text
app.py
  └── ui/dashboard.py
        └── agents/orchestrator_agent.py   ← LangGraph orchestrator
              ├── agents/evaluation_agent.py   ← REAL Cohere LLM only
              ├── tools/document_tool.py       ← PDF extraction
              ├── tools/validation_tool.py     ← schema/score normalization
              ├── tools/scoring_tool.py        ← deterministic weighted score
              ├── tools/ranking_tool.py        ← benchmark/PPI/tie-break/rank
              └── tools/persistence_tool.py    ← SQLite persistence
                         ↓
                  services/database_service.py
```

### Responsibility boundary

| Component | Responsibility | LLM? |
|---|---|---|
| `RFPOrchestrator` | Controls graph order/state flow | No |
| `EvaluationAgent` | Judges proposal content and returns evidence-grounded JSON | **Yes — Cohere** |
| `Document Tool` | Extracts PDF text page-by-page | No |
| `Validation Tool` | Validates, clips, fills missing criterion records and records warnings | No |
| `Scoring Tool` | Calculates absolute weighted score | No |
| `Ranking Tool` | Benchmarks, gaps, relative %, PPI, tie-break and rank | No |
| `Persistence Tool` | Writes complete run/results | No |
| Streamlit UI | Presentation/input only | No |

This satisfies the brief's rule that the LLM may judge proposal content but must not decide final arithmetic, benchmarks, tie-breaks or rank.

## Folder structure

```text
agentic_rfp_streamlit/
├── app.py
├── config.py
├── requirements.txt
├── README.md
├── .gitignore
├── .streamlit/
│   └── config.toml
├── agents/
│   ├── __init__.py
│   ├── evaluation_agent.py
│   └── orchestrator_agent.py
├── tools/
│   ├── __init__.py
│   ├── document_tool.py
│   ├── validation_tool.py
│   ├── scoring_tool.py
│   ├── ranking_tool.py
│   └── persistence_tool.py
├── services/
│   ├── __init__.py
│   └── database_service.py
├── models/
│   ├── __init__.py
│   └── schemas.py
├── ui/
│   ├── __init__.py
│   └── dashboard.py
├── scripts/
│   ├── init_db.py
│   └── generate_sample_pdfs.py
├── tests/
│   └── test_tools.py
└── sample_data/
    ├── apex_systems.pdf
    ├── brightpath_tech.pdf
    ├── nexaworks.pdf
    └── orbit_digital.pdf
```

## Workflow

`START → load_criteria → extract_documents → evaluate_suppliers → validate_outputs → calculate_scores → benchmark_and_rank → persist_results → END`

## Run locally

```bash
pip install -r requirements.txt
python scripts/init_db.py
streamlit run app.py
```

Enter a real Cohere API key in the sidebar. The production path is **real Cohere → validation → deterministic scoring/ranking**.

## Criteria and formulas

Default active criteria: Technical Capability 30%, Implementation Plan 20%, Commercial Value 20%, Security & Compliance 20%, Support & Experience 10%.

Absolute score:

`Σ ((criterion score / maximum score) × criterion weight)`

Benchmark = highest valid supplier score for a criterion.

Gap = supplier score − benchmark.

Relative performance = `(supplier score / benchmark) × 100`, with zero-safe handling.

PPI = weighted average of relative-performance percentages.

Tie-break order: **higher PPI → earlier submission date → higher historical experience rating → supplier name ascending**.

## Streamlit dashboard

- 🚀 Evaluate RFP — multiple PDF upload and metadata
- 🏆 Results Explorer — leaderboard, scorecards, evidence, PPI and JSON download
- 🎯 Criteria Studio — database-backed configurable criteria
- 🧪 Validation Lab — malformed-output demonstration
- 🧭 Architecture — visible separation of agents and tools for rubric demonstration

## Testing

```bash
pytest -q
```

The validation test demonstrates out-of-range and missing criteria handling. Ranking tests demonstrate deterministic ordering.
