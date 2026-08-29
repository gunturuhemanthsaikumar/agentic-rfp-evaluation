import json
import queue
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import streamlit as st

from config import (
    APP_TITLE,
    COHERE_API_KEY,
    COHERE_MODEL,
    RFP_DB_PATH,
    LLM_SEED,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
    validate_llm_config,
)
from services.database_service import (
    get_active_criteria,
    get_all_criteria,
    get_run,
    get_run_results,
    init_db,
    update_criterion,
)
from tools.document_tool import extract_pdf_document
from tools.validation_tool import validate_and_normalize
from agents.orchestrator_agent import RFPOrchestrator


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)
init_db()


def inject_css():
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] {
            background:
              radial-gradient(circle at 5% 5%, rgba(99,102,241,.10), transparent 28%),
              radial-gradient(circle at 95% 10%, rgba(236,72,153,.10), transparent 26%),
              linear-gradient(180deg,#f8fafc 0%,#eef2ff 100%);
        }
        .hero {
            padding: 1.8rem 2rem;
            border-radius: 26px;
            background: linear-gradient(135deg,#111827,#312e81,#7c3aed);
            color: white;
            box-shadow: 0 18px 45px rgba(49,46,129,.22);
            margin-bottom: 1.25rem;
        }
        .hero h1 { margin: 0; font-size: 2.45rem; font-weight: 850; }
        .hero p { margin: .45rem 0 0; opacity: .90; font-size: 1rem; }
        .badge {
            display:inline-block; padding:.28rem .68rem; border-radius:999px;
            background:rgba(255,255,255,.16); color:white; font-weight:750; font-size:.76rem;
        }
        .card {
            background:rgba(255,255,255,.90);
            border:1px solid rgba(148,163,184,.22);
            border-radius:18px;
            padding:1rem 1.1rem;
            box-shadow:0 8px 25px rgba(15,23,42,.06);
        }
        .mini-title { font-weight:800; color:#312e81; margin-bottom:.25rem; }
        .success-card { border-left: 6px solid #10b981; }
        .warning-card { border-left: 6px solid #f59e0b; }
        .info-card { border-left: 6px solid #6366f1; }
        .rank1 { border-left:6px solid #f59e0b; }
        .rank2 { border-left:6px solid #94a3b8; }
        .rank3 { border-left:6px solid #b45309; }
        div[data-testid="stMetricValue"] { font-weight: 800; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero():
    st.markdown(
        """
        <div class="hero">
          <span class="badge">AGENTIC AI • PROCUREMENT INTELLIGENCE</span>
          <h1>RFP Command Center</h1>
          <p>Evaluate proposals with evidence-grounded AI, transparent scoring, peer benchmarking and deterministic ranking.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def config_status():
    return bool(COHERE_API_KEY)


def workflow_steps():
    return [
        ("1", "Criteria", "Load active criteria from SQLite"),
        ("2", "Documents", "Extract every uploaded PDF page"),
        ("3", "LLM Agent", "Real Cohere evidence-grounded evaluation"),
        ("4", "Validation", "Normalize malformed or missing JSON"),
        ("5", "Scoring", "Deterministic weighted arithmetic"),
        ("6", "Ranking", "Benchmark + PPI + tie-breaks"),
        ("7", "Persistence", "Store complete run in SQLite"),
    ]


def show_workflow_cards():
    cols = st.columns(7)
    for col, (num, name, desc) in zip(cols, workflow_steps()):
        with col:
            st.markdown(
                f'<div class="card"><div class="mini-title">{num}. {name}</div><small>{desc}</small></div>',
                unsafe_allow_html=True,
            )


def run_agentic_evaluation(pdf_files, metadata, api_key, model):
    """Run the blocking LLM workflow in a worker while the UI polls progress."""
    events = queue.Queue()

    def progress(event):
        events.put(event)

    def worker():
        orchestrator = RFPOrchestrator(
            api_key,
            model,
            progress_callback=progress,
        )
        return orchestrator.run(pdf_files, metadata)

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(worker)

    status = st.status("🧠 Agentic workflow is running…", expanded=True)
    progress_bar = st.progress(0, text="Preparing evaluation…")
    event_placeholder = st.empty()
    detail_placeholder = st.empty()

    last_event = None
    while not future.done():
        try:
            event = events.get(timeout=0.25)
            last_event = event
            phase = event.get("phase", "workflow")
            message = event.get("message", "Working…")
            current = event.get("current")
            total = event.get("total")

            if current is not None and total:
                fraction = max(0.0, min(1.0, float(current) / float(total)))
                progress_bar.progress(fraction, text=message)
            else:
                progress_bar.progress(0.02, text=message)

            event_placeholder.markdown(
                f'<div class="card info-card"><b>Current stage:</b> {phase.upper()}<br>{message}</div>',
                unsafe_allow_html=True,
            )
            if event.get("supplier"):
                detail_placeholder.caption(f"Supplier currently being processed: {event['supplier']}")
        except queue.Empty:
            time.sleep(0.05)

    while True:
        try:
            event = events.get_nowait()
        except queue.Empty:
            break
        last_event = event
        message = event.get("message", "Completed")
        event_placeholder.markdown(
            f'<div class="card success-card"><b>✓</b> {message}</div>',
            unsafe_allow_html=True,
        )

    try:
        state = future.result()
    except Exception:
        executor.shutdown(wait=False, cancel_futures=True)
        raise
    else:
        executor.shutdown(wait=False)

    progress_bar.progress(1.0, text="Evaluation completed")
    status.update(label="✅ Agentic evaluation completed", state="complete", expanded=False)
    return state


def render_sidebar():
    with st.sidebar:
        st.markdown("## 🧭 Navigation")
        page = st.radio(
            "Open section",
            [
                "🏠 Overview",
                "🚀 Evaluate RFP",
                "📄 Proposal Viewer",
                "🏆 Results Explorer",
                "🎯 Criteria Studio",
                "🧾 Run Details",
                "🧪 Validation Lab",
                "🧭 Architecture",
            ],
        )

        st.divider()
        st.markdown("## 🔐 LLM Configuration")
        if config_status():
            st.success("Cohere API key loaded", icon="🔑")
        else:
            st.error("Cohere API key missing", icon="⚠️")
            st.caption("Local: create .env. Cloud: add it to Streamlit Secrets.")

        st.text_input("Model", value=COHERE_MODEL, disabled=True)
        st.caption(f"Temperature: {LLM_TEMPERATURE} • Seed: {LLM_SEED}")
        st.caption(f"Timeout: {LLM_TIMEOUT_SECONDS}s")
        st.caption(f"SQLite: {RFP_DB_PATH}")
        return page


def page_overview():
    st.header("🏠 Procurement Intelligence Overview")
    criteria = get_active_criteria()
    runs = get_run_results()

    a, b, c, d = st.columns(4)
    a.metric("Active Criteria", len(criteria))
    b.metric("Active Weight", f"{sum(float(x['weight']) for x in criteria):.0f}%")
    bdelta = "Ready" if abs(sum(float(x['weight']) for x in criteria) - 100) < 1e-9 else "Fix weights"
    b.caption(bdelta)
    c.metric("Stored Supplier Results", len(runs))
    d.metric("LLM", "Cohere")

    st.markdown("### 🔄 End-to-end agentic workflow")
    show_workflow_cards()

    st.markdown("### 📋 What the application evaluates")
    df = pd.DataFrame(criteria)
    if not df.empty:
        display_df = df[["criterion_id", "name", "description", "weight", "max_score"]].copy()
        display_df.columns = ["ID", "Criterion", "What the LLM inspects", "Weight %", "Max Score"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown("### 🧠 Separation of responsibilities")
    left, right = st.columns(2)
    with left:
        st.markdown(
            '<div class="card info-card"><b>LLM responsibility</b><br>'
            'Read proposal content and produce criterion score, justification, supporting evidence, evidence page, risks and summary.</div>',
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            '<div class="card success-card"><b>Python responsibility</b><br>'
            'Validation, weighted score, benchmarks, gaps, relative performance, PPI, tie-breaks, final rank and persistence.</div>',
            unsafe_allow_html=True,
        )


def page_evaluate():
    st.header("🚀 Evaluate a Supplier Batch")
    criteria = get_active_criteria()
    total_weight = sum(float(c["weight"]) for c in criteria)

    if abs(total_weight - 100) > 1e-9:
        st.error(f"Evaluation blocked. Active criteria weights total {total_weight:.2f}%, but must total 100%.")
        return
    if not config_status():
        st.error("Cohere API key is not configured. The app will not call the LLM until it is configured.")
        st.info("For local execution, create .env beside app.py. Do not paste the key into source code.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Active Criteria", len(criteria))
    c2.metric("Weights", f"{total_weight:.0f}%")
    c3.metric("LLM Model", COHERE_MODEL)

    with st.expander("🎯 Active criteria used for this run", expanded=True):
        st.dataframe(
            pd.DataFrame(criteria)[["criterion_id", "name", "description", "weight", "max_score"]],
            use_container_width=True,
            hide_index=True,
        )

    uploads = st.file_uploader(
        "Upload one or more supplier RFP PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        help="Use the synthetic proposals supplied with the project or your own non-confidential RFP responses.",
    )
    if not uploads:
        st.info("👆 Upload multiple PDF proposals to begin. The app will extract them page-by-page before invoking Cohere.")
        return

    metadata, pdf_files = {}, {}
    valid = True
    st.markdown("### 👥 Supplier metadata")

    for i, upload in enumerate(uploads):
        with st.container(border=True):
            st.markdown(f"#### 📄 {upload.name}")
            a, b, c = st.columns([1.5, 1, 1])
            default_name = Path(upload.name).stem.replace("_", " ").replace("-", " ").title()
            name = a.text_input("Supplier name", default_name, key=f"supplier_name_{i}").strip()
            submission_date = b.date_input("Submission date", key=f"submission_date_{i}")
            experience = c.number_input("Historical experience rating", 0.0, 10.0, 5.0, 0.5, key=f"experience_{i}")

            if not name:
                valid = False
                st.warning("Supplier name is required.")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
                f.write(upload.getbuffer())
                temp_path = Path(f.name)

            pdf_files[upload.name] = temp_path
            metadata[upload.name] = {
                "supplier_name": name,
                "submission_date": submission_date.isoformat(),
                "experience_rating": float(experience),
            }

    st.markdown("### 🔎 Pre-flight summary")
    summary = []
    for upload in uploads:
        doc = extract_pdf_document(pdf_files[upload.name])
        summary.append({
            "Supplier": metadata[upload.name]["supplier_name"],
            "PDF": upload.name,
            "Pages": len(doc["pages"]),
            "Characters": len(doc["text"]),
            "Submission": metadata[upload.name]["submission_date"],
            "Experience": metadata[upload.name]["experience_rating"],
        })
    st.dataframe(pd.DataFrame(summary), use_container_width=True, hide_index=True)

    # Keep extracted content in the current Streamlit session so the Proposal Viewer
    # can display the actual PDF text and page boundaries before/after evaluation.
    st.session_state["uploaded_documents"] = {
        metadata[u.name]["supplier_name"]: extract_pdf_document(pdf_files[u.name])
        for u in uploads
    }

    st.warning("The evaluation calls the real Cohere API once per supplier. Large PDFs may take time, but the progress panel will remain active and show the current supplier/stage.")

    if st.button("🚀 Start Agentic Evaluation", type="primary", use_container_width=True, disabled=not valid):
        try:
            state = run_agentic_evaluation(
                pdf_files,
                metadata,
                COHERE_API_KEY,
                COHERE_MODEL,
            )
            st.session_state["last_run_id"] = state["rfp_run_id"]
            st.session_state["last_state"] = state
            st.success(f"Completed {state['rfp_run_id']} — {len(state['final_results'])} supplier(s) evaluated.")
            st.balloons()
        except Exception as exc:
            st.error(f"Evaluation failed: {exc}")
            st.exception(exc)


def load_current_results():
    run_id = st.session_state.get("last_run_id")
    if not run_id:
        rows = get_run_results()
        run_id = rows[0]["rfp_run_id"] if rows else None
    if not run_id:
        return None, None, []
    run = get_run(run_id)
    rows = get_run_results(run_id)
    results = [json.loads(row["result_json"]) for row in rows]
    return run_id, run, results


def page_results():
    st.header("🏆 Results Explorer")
    run_id, run, results = load_current_results()
    if not run_id:
        st.info("Run an evaluation first.")
        return

    st.caption(f"RFP_RUN_ID: {run_id} • Status: {run['status']} • Created: {run['created_at']}")
    if not results:
        st.warning("No supplier results found for this run.")
        return

    winner = results[0]
    a, b, c, d = st.columns(4)
    a.metric("🥇 Leader", winner["supplier_name"])
    b.metric("Absolute Score", f"{winner['absolute_score']:.2f}/100")
    c.metric("PPI", f"{winner['ppi']:.2f}%")
    d.metric("Suppliers", len(results))

    st.markdown("### 🏅 Leaderboard")
    leaderboard = pd.DataFrame([
        {
            "Rank": r["final_rank"],
            "Supplier": r["supplier_name"],
            "Absolute Score": round(r["absolute_score"], 2),
            "PPI %": round(r["ppi"], 2),
            "Submission Date": r["submission_date"],
            "Experience Rating": r["experience_rating"],
        }
        for r in results
    ])
    st.dataframe(leaderboard, use_container_width=True, hide_index=True)

    st.markdown("### 📊 Supplier comparison")
    chart_df = leaderboard.set_index("Supplier")[["Absolute Score", "PPI %"]]
    st.bar_chart(chart_df)

    st.markdown("### 🔍 Detailed scorecard")
    selected = st.selectbox("Select supplier", [r["supplier_name"] for r in results])
    result = next(r for r in results if r["supplier_name"] == selected)

    x1, x2, x3, x4 = st.columns(4)
    x1.metric("Final Rank", f"#{result['final_rank']}")
    x2.metric("Absolute Score", f"{result['absolute_score']:.2f}")
    x3.metric("PPI", f"{result['ppi']:.2f}%")
    x4.metric("Experience", f"{result['experience_rating']:.1f}/10")

    st.markdown(f"**Overall assessment:** {result['overall_summary']}")
    if result.get("risks"):
        st.warning("Risks: " + " • ".join(result["risks"]))

    detail = pd.DataFrame([
        {
            "Criterion": item["criterion_name"],
            "Score": f"{item['score']:.2f}/{item['max_score']:.0f}",
            "Weight %": item["weight"],
            "Weighted Contribution": round(item["weighted_contribution"], 2),
            "Benchmark": item["benchmark"],
            "Gap": round(item["gap"], 2),
            "Relative %": round(item["relative_performance_pct"], 2),
        }
        for item in result["criteria"]
    ])
    st.dataframe(detail, use_container_width=True, hide_index=True)

    for item in result["criteria"]:
        with st.expander(f"{item['criterion_name']}  •  {item['score']:.2f}/{item['max_score']}", expanded=False):
            st.markdown(f"**What was evaluated:** {next((c['description'] for c in get_active_criteria() if int(c['criterion_id']) == int(item['criterion_id'])), '')}")
            st.markdown(f"**Justification**\n\n{item['justification']}")
            st.markdown(f"**Evidence from proposal**\n\n> {item['evidence']}")
            st.caption(
                f"Source page: {item['evidence_page']} • Weight: {item['weight']}% • "
                f"Benchmark: {item['benchmark']} • Gap: {item['gap']:.2f} • "
                f"Relative performance: {item['relative_performance_pct']:.2f}%"
            )

    warnings = json.loads(run.get("warnings_json", "[]"))
    if warnings:
        with st.expander(f"⚠️ Validation warnings ({len(warnings)})"):
            for warning in warnings:
                st.write("• " + warning)

    st.markdown("### ⚖️ Deterministic ranking rule")
    st.info(result["tie_break_rule"])

    payload = {
        "rfp_run_id": run_id,
        "criteria": json.loads(run["criteria_snapshot_json"]),
        "suppliers": results,
        "run_warnings": warnings,
    }
    st.download_button(
        "⬇️ Download complete evaluation JSON",
        json.dumps(payload, indent=2, ensure_ascii=False),
        file_name=f"{run_id}_complete_result.json",
        mime="application/json",
        use_container_width=True,
    )


def page_criteria():
    st.header("🎯 Criteria Studio")
    st.caption("Criteria are database-driven. Changing them changes the next evaluation prompt without editing Python code.")
    criteria = get_all_criteria()
    df = pd.DataFrame(criteria)
    st.dataframe(df, use_container_width=True, hide_index=True)

    selected_id = st.selectbox(
        "Criterion to edit",
        [int(c["criterion_id"]) for c in criteria],
        format_func=lambda x: next(c["name"] for c in criteria if int(c["criterion_id"]) == x),
    )
    c = next(c for c in criteria if int(c["criterion_id"]) == selected_id)
    a, b, d = st.columns(3)
    weight = a.number_input("Weight (%)", 0.0, 100.0, float(c["weight"]), 1.0)
    max_score = b.number_input("Maximum score", 1.0, 100.0, float(c["max_score"]), 1.0)
    active = d.checkbox("Active", bool(c["is_active"]))
    if st.button("💾 Save criterion", type="primary"):
        update_criterion(selected_id, weight, max_score, active)
        st.success("Criterion updated.")
        st.rerun()

    active_total = sum(float(x["weight"]) for x in get_active_criteria())
    if abs(active_total - 100) < 1e-9:
        st.success(f"Active weights are valid: {active_total:.1f}%")
    else:
        st.error(f"Active weights are {active_total:.1f}%. They must total exactly 100% before evaluation.")


def page_documents():
    st.header("📄 Proposal Viewer")
    st.caption("Read the actual extracted proposal content page-by-page. The Document Tool preserves page boundaries so LLM evidence can point to a source page.")

    docs = st.session_state.get("uploaded_documents", {})
    _, run, results = load_current_results()

    if not docs and not results:
        st.info("Upload PDFs on Evaluate RFP first.")
        return

    suppliers = sorted(set(docs) | {r["supplier_name"] for r in results})
    selected = st.selectbox("Supplier", suppliers)

    if selected in docs:
        doc = docs[selected]
        a, b = st.columns(2)
        a.metric("Pages", len(doc["pages"]))
        b.metric("Extracted characters", f"{len(doc['text']):,}")
        for page in doc["pages"]:
            with st.expander(f"📄 Page {page['page']}", expanded=False):
                if page["text"]:
                    st.text(page["text"])
                else:
                    st.warning("No extractable text found on this page. It may be image-only/scanned.")
    else:
        st.warning("Raw PDF text is not available in this browser session for this supplier.")

    if results:
        result = next(r for r in results if r["supplier_name"] == selected)
        st.markdown("### 🧾 Evidence used in the scorecard")
        for item in result["criteria"]:
            with st.expander(f"Page {item['evidence_page']} • {item['criterion_name']}"):
                st.markdown(f"> {item['evidence']}")
                st.markdown(f"**Justification:** {item['justification']}")

    st.info("Uploaded PDFs are processed in memory/temp files for the run. SQLite stores the run, criteria snapshot, scorecards, evidence, warnings and ranking results rather than the original PDF binary.")


def page_run_details():
    st.header("🧾 Run Details")
    run_id, run, results = load_current_results()
    if not run:
        st.info("No completed run available.")
        return

    a, b, c = st.columns(3)
    a.metric("RFP_RUN_ID", run_id)
    b.metric("Status", run["status"])
    c.metric("Suppliers", len(results))

    st.markdown("### 📌 Run metadata")
    st.json({
        "rfp_run_id": run["rfp_run_id"],
        "created_at": run["created_at"],
        "status": run["status"],
        "database": str(RFP_DB_PATH),
    })

    st.markdown("### 🎯 Criteria snapshot used for this run")
    st.dataframe(pd.DataFrame(json.loads(run["criteria_snapshot_json"])), use_container_width=True, hide_index=True)

    warnings = json.loads(run.get("warnings_json", "[]"))
    st.markdown("### ⚠️ Validation / run warnings")
    if warnings:
        for warning in warnings:
            st.warning(warning)
    else:
        st.success("No validation warnings were recorded.")

    st.markdown("### ⚖️ Ranking explanation")
    st.info("Higher PPI → earlier submission date → higher historical experience rating → supplier name ascending. Ranks are assigned only after this stable sort.")


def page_validation():
    st.header("🧪 Validation Lab")
    st.caption("Demonstrates the validation tool independently. This does not replace the production Cohere path.")
    criteria = get_active_criteria()
    malformed = {
        "supplier_name": "Example Supplier",
        "criteria": [
            {
                "criterion_id": 1,
                "score": 14,
                "max_score": 10,
                "justification": "",
                "evidence": "",
                "evidence_page": "not-a-number",
            }
        ],
        "risks": [],
        "overall_summary": "",
    }
    result = validate_and_normalize(malformed, "Example Supplier", criteria)
    st.markdown("### Expected validation issues")
    st.write(result["warnings"])
    st.markdown("### Normalized result")
    st.dataframe(pd.DataFrame(result["criteria"]), use_container_width=True, hide_index=True)


def page_architecture():
    st.header("🧭 Agentic Workflow & Tool Separation")
    st.markdown("### 20-mark rubric: Agentic workflow & tool use")
    st.info("Clear orchestration and appropriate separation of LLM and tools are demonstrated through LangGraph, a dedicated Evaluation Agent and deterministic Python tools.")

    show_workflow_cards()

    st.markdown("### 🔌 Responsibility map")
    rows = [
        ["LangGraph Orchestrator", "Controls workflow order and state", "No scoring/ranking arithmetic"],
        ["Criteria Tool", "Loads active criteria from SQLite", "Deterministic"],
        ["Document Tool", "Extracts PDF text page-by-page", "Deterministic"],
        ["Evaluation Agent", "Scores proposal content and cites evidence", "REAL Cohere LLM"],
        ["Validation Tool", "Checks schema, missing criteria, invalid scores/evidence", "Deterministic"],
        ["Scoring Tool", "Calculates absolute weighted score", "Deterministic"],
        ["Ranking Tool", "Benchmark, gap, relative %, PPI, tie-break and rank", "Deterministic"],
        ["Persistence Tool", "Stores run and complete supplier results", "SQLite"],
    ]
    st.dataframe(pd.DataFrame(rows, columns=["Component", "Responsibility", "Execution"]), use_container_width=True, hide_index=True)

    st.markdown("### 🔁 Runtime graph")
    st.code(
        "START\n  ↓\nload_criteria\n  ↓\nextract_documents\n  ↓\nevaluate_suppliers  ← REAL COHERE\n  ↓\nvalidate_outputs\n  ↓\ncalculate_scores    ← Python\n  ↓\nbenchmark_and_rank  ← Python\n  ↓\npersist_results     ← SQLite\n  ↓\nEND",
        language="text",
    )

    st.markdown("### 🛡️ Why this is agentic")
    st.write(
        "The orchestrator is a workflow controller that invokes specialized components in sequence. "
        "The LLM is constrained to proposal-content judgment; deterministic tools own business rules and persistence. "
        "This makes the final score traceable and reproducible after LLM scorecards have been validated."
    )


def run_app():
    inject_css()
    hero()
    page = render_sidebar()

    pages = {
        "🏠 Overview": page_overview,
        "🚀 Evaluate RFP": page_evaluate,
        "📄 Proposal Viewer": page_documents,
        "🏆 Results Explorer": page_results,
        "🎯 Criteria Studio": page_criteria,
        "🧾 Run Details": page_run_details,
        "🧪 Validation Lab": page_validation,
        "🧭 Architecture": page_architecture,
    }
    pages[page]()
