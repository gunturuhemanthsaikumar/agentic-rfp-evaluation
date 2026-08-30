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


# -----------------------------------------------------------------------------
# DESIGN SYSTEM
# -----------------------------------------------------------------------------

def inject_css():
    st.markdown(
        """
        <style>
        :root {
            --navy:#070b2b;
            --indigo:#312e81;
            --purple:#6d28d9;
            --blue:#2563eb;
            --green:#16a34a;
            --orange:#f97316;
            --text:#17203a;
            --muted:#69738a;
            --line:#e6e9f2;
            --surface:#ffffff;
            --soft:#f6f7fc;
        }

        .stApp {
            background:
                radial-gradient(circle at 85% 4%, rgba(124,58,237,.08), transparent 24%),
                radial-gradient(circle at 15% 18%, rgba(37,99,235,.06), transparent 24%),
                #f7f8fc;
            color:var(--text);
        }

        [data-testid="stHeader"] { background:transparent; }

        /* Streamlit Cloud: use the full browser width instead of the
           narrower default content container. */
        [data-testid="stMainBlockContainer"] {
            max-width: none !important;
            width: 100% !important;
            padding-left: 2.4rem !important;
            padding-right: 2.4rem !important;
        }
        .block-container {
            max-width: none !important;
            width: 100% !important;
        }

        /* Keep the navigation compact so the application content has
           enough horizontal space on laptops and Streamlit Cloud. */
        [data-testid="stSidebar"] {
            background:linear-gradient(180deg,#080c30 0%,#0d123d 58%,#080b29 100%);
            border-right:1px solid rgba(255,255,255,.08);
            min-width: 280px !important;
            max-width: 280px !important;
        }
        [data-testid="stSidebar"] * { color:#eef1ff !important; }
        [data-testid="stSidebar"] [data-testid="stRadio"] label {
            border-radius:12px;
            padding:7px 10px;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
            background:rgba(255,255,255,.08);
        }
        [data-testid="stSidebar"] hr { border-color:rgba(255,255,255,.12); }

        .brand {
            padding:12px 8px 18px;
            text-align:center;
        }
        .brand-icon {
            width:58px;height:58px;margin:0 auto 9px;
            display:flex;align-items:center;justify-content:center;
            border-radius:18px;
            background:linear-gradient(135deg,#fbbf24,#f97316);
            box-shadow:0 12px 30px rgba(249,115,22,.28);
            font-size:29px;
        }
        .brand-title { font-size:1.15rem;font-weight:850;letter-spacing:-.02em; }
        .brand-sub { font-size:.70rem;color:#b9c0df !important;margin-top:4px; }

        .side-run {
            margin-top:18px;padding:13px;border:1px solid rgba(255,255,255,.14);
            border-radius:15px;background:rgba(255,255,255,.045);
        }
        .side-run .label {font-size:.68rem;color:#9da7cf !important;text-transform:uppercase;letter-spacing:.09em;}
        .side-run .value {font-weight:750;margin-top:5px;}

        .topbar {
            display:flex;align-items:center;justify-content:space-between;gap:22px;
            margin:0 0 18px;padding:5px 0;
        }
        .title {min-width:0;flex:1;}
        .title h1 {margin:0;font-size:clamp(1.7rem,2.4vw,2.35rem);font-weight:900;letter-spacing:-.045em;color:#101638;line-height:1.05;}
        .title p {margin:7px 0 0;color:var(--muted);font-size:.93rem;}
        .top-status {
            flex:0 0 auto;display:flex;align-items:stretch;background:#fff;border:1px solid var(--line);
            border-radius:15px;overflow:hidden;box-shadow:0 8px 24px rgba(24,34,73,.05);
        }
        .status-item {padding:10px 14px;min-width:118px;border-left:1px solid var(--line);}
        .status-item:first-child {border-left:0;}
        .status-k {font-size:.68rem;color:#8790a7;}
        .status-v {font-weight:800;font-size:.86rem;color:#202949;margin-top:2px;}
        .dot {display:inline-block;width:8px;height:8px;border-radius:50%;background:#22c55e;margin-right:6px;}

        .workflow-wrap {
            background:#fff;border:1px solid var(--line);border-radius:18px;padding:13px 13px 12px;
            box-shadow:0 8px 24px rgba(24,34,73,.045);margin-bottom:16px;
        }
        .workflow-title {font-size:.72rem;font-weight:800;color:#727c94;text-transform:uppercase;letter-spacing:.08em;margin:0 0 10px 4px;}
        .workflow-grid {display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:8px;}
        .wf-card {position:relative;min-height:105px;padding:12px 10px 11px;border:1px solid #e8eaf2;border-radius:14px;background:#fff;overflow:hidden;}
        .wf-card:after {content:"";position:absolute;left:0;right:0;bottom:0;height:3px;background:#e7e9f3;}
        .wf-card.active {background:linear-gradient(180deg,#faf9ff,#f6f3ff);border-color:#b8a8ff;box-shadow:0 7px 18px rgba(109,40,217,.09);}
        .wf-card.active:after {background:linear-gradient(90deg,#4f46e5,#8b5cf6);}
        .wf-num {display:inline-flex;width:25px;height:25px;border-radius:50%;align-items:center;justify-content:center;font-size:.72rem;font-weight:850;background:#eef0f6;color:#667085;margin-bottom:7px;}
        .wf-card.active .wf-num {background:#ede9fe;color:#6d28d9;}
        .wf-name {font-size:.82rem;font-weight:850;color:#1e2745;}
        .wf-desc {font-size:.68rem;line-height:1.35;color:#7a849a;margin-top:4px;}
        .wf-check {float:right;color:#22c55e;font-size:.9rem;}

        .kpi-grid {display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin-bottom:17px;}
        .kpi {background:#fff;border:1px solid var(--line);border-radius:16px;padding:13px 15px;box-shadow:0 8px 24px rgba(24,34,73,.045);min-height:93px;}
        .kpi-head {display:flex;align-items:center;gap:9px;color:#778199;font-size:.70rem;font-weight:750;}
        .kpi-icon {width:32px;height:32px;border-radius:11px;display:flex;align-items:center;justify-content:center;font-size:17px;}
        .kpi-value {font-size:1.38rem;font-weight:900;color:#17203a;margin-top:7px;letter-spacing:-.03em;}
        .kpi-note {font-size:.68rem;color:#7b8498;margin-top:1px;}
        .green {background:#eaf9ef;color:#16a34a}.blue {background:#edf4ff;color:#2563eb}.purple {background:#f1edff;color:#6d28d9}.orange {background:#fff3e8;color:#ea580c}.cyan {background:#e8f9fb;color:#0891b2}

        .panel {background:#fff;border:1px solid var(--line);border-radius:17px;padding:17px 18px;box-shadow:0 8px 24px rgba(24,34,73,.045);}
        .panel-title {font-size:1rem;font-weight:850;color:#1b2443;}
        .panel-sub {font-size:.70rem;color:#7c869b;margin-top:2px;margin-bottom:12px;}
        .winner {background:linear-gradient(135deg,#f8fff9,#effcf3);border:1px solid #c9eed4;border-radius:17px;padding:17px;}
        .winner-k {font-size:.68rem;color:#5e7c68;text-transform:uppercase;letter-spacing:.08em;font-weight:800;}
        .winner-name {font-size:1.45rem;font-weight:900;color:#166534;margin:3px 0;}
        .winner-copy {font-size:.78rem;color:#56705e;line-height:1.45;}
        .rank-pill {display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border-radius:50%;font-weight:900;background:#fff3c4;color:#a16207;}

        .metric-strip {display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;}
        .pill {background:#f5f6fb;border:1px solid #e7e9f1;border-radius:999px;padding:5px 9px;font-size:.69rem;color:#5d667c;}

        .section-gap {margin-top:17px;}
        .footer-note {text-align:center;color:#8a93a7;font-size:.67rem;padding:20px 0 5px;}

        .config-pills {display:flex;gap:6px;flex-wrap:wrap;margin-top:9px;}
        .config-pill {background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.10);border-radius:999px;padding:5px 8px;font-size:.64rem;color:#cbd2f1 !important;}
        .config-pill strong {color:#fff !important;}

        .score-card {border:1px solid var(--line);border-radius:14px;background:#fff;padding:13px;margin-bottom:9px;}
        .score-head {display:flex;align-items:center;justify-content:space-between;gap:10px;}
        .score-name {font-weight:850;color:#1f2949;font-size:.88rem;}
        .score-number {font-weight:900;color:#4338ca;}
        .score-bar {height:7px;background:#edf0f7;border-radius:99px;overflow:hidden;margin:8px 0;}
        .score-fill {height:100%;background:linear-gradient(90deg,#4f46e5,#8b5cf6);border-radius:99px;}
        .score-meta {font-size:.67rem;color:#7b8498;}

        @media (max-width:1350px) {
            [data-testid="stMainBlockContainer"] {
                padding-left: 1.4rem !important;
                padding-right: 1.4rem !important;
            }
            .workflow-grid {grid-template-columns:repeat(4,minmax(0,1fr));}
            .kpi-grid {grid-template-columns:repeat(3,minmax(0,1fr));}
        }
        @media (max-width:900px) {
            [data-testid="stSidebar"] {min-width:240px !important;max-width:240px !important;}
            .workflow-grid {grid-template-columns:repeat(2,minmax(0,1fr));}
            .kpi-grid {grid-template-columns:repeat(2,minmax(0,1fr));}
            .top-status {display:none;}
        }
        @media (max-width:640px) {
            [data-testid="stMainBlockContainer"] {padding-left:.8rem !important;padding-right:.8rem !important;}
            .workflow-grid,.kpi-grid {grid-template-columns:1fr;}
            .topbar {margin-bottom:12px;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def topbar():
    criteria = get_active_criteria()
    st.markdown(
        f"""
        <div class="topbar">
          <div class="title">
            <h1>Agentic RFP Evaluation &amp; Supplier Ranking</h1>
            <p>Evaluate &nbsp;•&nbsp; Compare &nbsp;•&nbsp; Rank &nbsp;•&nbsp; Decide with Confidence</p>
          </div>
          <div class="top-status">
            <div class="status-item"><div class="status-k">TODAY</div><div class="status-v">{time.strftime('%d %b %Y')}</div></div>
            <div class="status-item"><div class="status-k">ACTIVE CRITERIA</div><div class="status-v">{len(criteria)} Criteria</div></div>
            <div class="status-item"><div class="status-k">SYSTEM STATUS</div><div class="status-v"><span class="dot"></span>{'Ready' if COHERE_API_KEY else 'Configuration needed'}</div></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def workflow_steps():
    return [
        ("1", "Criteria", "Load active criteria", "⚙️"),
        ("2", "Documents", "Extract PDF pages", "📄"),
        ("3", "LLM Agent", "Real Cohere evaluation", "🧠"),
        ("4", "Validation", "Validate JSON output", "✓"),
        ("5", "Scoring", "Deterministic arithmetic", "▣"),
        ("6", "Ranking", "PPI + tie-breaks", "🏆"),
        ("7", "Persistence", "Store complete run", "▤"),
    ]


def show_workflow_cards(active_stage=None):
    cards = []
    for num, name, desc, icon in workflow_steps():
        active = active_stage == int(num) if active_stage is not None else False
        check = "✓" if active_stage is not None and int(num) < active_stage else ""
        cards.append(
            f"""<div class='wf-card {'active' if active else ''}'>
                <span class='wf-num'>{num}</span><span class='wf-check'>{check}</span>
                <div class='wf-name'>{icon} {name}</div>
                <div class='wf-desc'>{desc}</div>
            </div>"""
        )
    st.markdown(
        "<div class='workflow-wrap'><div class='workflow-title'>Agentic evaluation pipeline</div><div class='workflow-grid'>" +
        "".join(cards) + "</div></div>",
        unsafe_allow_html=True,
    )


def kpi(icon, label, value, note="", color="blue"):
    return f"""<div class='kpi'><div class='kpi-head'><span class='kpi-icon {color}'>{icon}</span>{label}</div><div class='kpi-value'>{value}</div><div class='kpi-note'>{note}</div></div>"""


def config_status():
    return bool(COHERE_API_KEY)


def run_agentic_evaluation(pdf_files, metadata, api_key, model):
    events = queue.Queue()

    def progress(event):
        events.put(event)

    def worker():
        orchestrator = RFPOrchestrator(api_key, model, progress_callback=progress)
        return orchestrator.run(pdf_files, metadata)

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(worker)

    status = st.status("🧠 Agentic workflow is running…", expanded=True)
    progress_bar = st.progress(0, text="Preparing evaluation…")
    event_placeholder = st.empty()
    detail_placeholder = st.empty()

    while not future.done():
        try:
            event = events.get(timeout=0.25)
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
                f"<div class='panel'><div class='panel-title'>Current stage: {phase.upper()}</div><div class='panel-sub'>{message}</div></div>",
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
        event_placeholder.markdown(
            f"<div class='winner'><div class='winner-k'>Workflow update</div><div class='winner-name' style='font-size:1rem'>✓ {event.get('message','Completed')}</div></div>",
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
        st.markdown(
            """
            <div class='brand'>
              <div class='brand-icon'>🏆</div>
              <div class='brand-title'>RFP Command Center</div>
              <div class='brand-sub'>AI-POWERED • EVIDENCE-DRIVEN • FAIR • TRANSPARENT</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        page = st.radio(
            "Navigation",
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
            label_visibility="collapsed",
        )

        st.markdown("<div class='side-run'><div class='label'>Active Run</div><div class='value'>" +
                    (st.session_state.get("last_run_id", "No active run")) +
                    "</div><div class='brand-sub'>" +
                    ("Latest evaluation available" if st.session_state.get("last_run_id") else "Start a new evaluation") +
                    "</div></div>", unsafe_allow_html=True)

        st.markdown("### 🔐 LLM Runtime")
        if config_status():
            st.success("Cohere connected")
        else:
            st.error("Cohere key missing")
            st.caption("Local: .env • Cloud: Streamlit Secrets")
        st.markdown(
            f"""<div class='config-pills'>
            <span class='config-pill'><strong>Model</strong> {COHERE_MODEL}</span>
            <span class='config-pill'><strong>T</strong> {LLM_TEMPERATURE}</span>
            <span class='config-pill'><strong>Seed</strong> {LLM_SEED}</span>
            <span class='config-pill'><strong>Timeout</strong> {LLM_TIMEOUT_SECONDS}s</span>
            </div>""",
            unsafe_allow_html=True,
        )
        st.markdown("<div class='brand-sub' style='margin-top:8px'>SQLite: " + str(RFP_DB_PATH) + "</div>", unsafe_allow_html=True)
        return page


def page_overview():
    criteria = get_active_criteria()
    runs = get_run_results()
    total_weight = sum(float(x["weight"]) for x in criteria)

    topbar()
    show_workflow_cards()

    # Latest run summary
    latest_results = []
    latest_run_id = st.session_state.get("last_run_id")
    if latest_run_id:
        rows = get_run_results(latest_run_id)
        latest_results = [json.loads(r["result_json"]) for r in rows]
    elif runs:
        latest_run_id = runs[0]["rfp_run_id"]
        rows = get_run_results(latest_run_id)
        latest_results = [json.loads(r["result_json"]) for r in rows]

    winner = latest_results[0] if latest_results else None
    max_score = max([float(r["absolute_score"]) for r in latest_results], default=0)
    max_ppi = max([float(r["ppi"]) for r in latest_results], default=0)

    cards = [
        kpi("👥", "Suppliers Evaluated", len(latest_results) if latest_results else 0, "Latest run", "blue"),
        kpi("🏆", "Highest Score", f"{max_score:.2f}", winner["supplier_name"] if winner else "No completed run", "green"),
        kpi("🎯", "Highest PPI", f"{max_ppi:.2f}%", winner["supplier_name"] if winner else "Peer benchmark", "purple"),
        kpi("⚖️", "Active Criteria", len(criteria), f"Total weight {total_weight:.0f}%", "orange"),
        kpi("◷", "Evaluation Engine", "READY" if config_status() else "SETUP", COHERE_MODEL, "cyan"),
    ]
    st.markdown("<div class='kpi-grid'>" + "".join(cards) + "</div>", unsafe_allow_html=True)

    if winner:
        left, right = st.columns([1.1, 1.9], gap="medium")
        with left:
            st.markdown(
                f"""<div class='winner'>
                <div class='winner-k'>🥇 Current leader</div>
                <div class='winner-name'>{winner['supplier_name']}</div>
                <div class='winner-copy'>{winner.get('overall_summary','Strongest validated peer result in the latest run.')}</div>
                <div class='metric-strip'>
                  <span class='pill'>Absolute {winner['absolute_score']:.2f}/100</span>
                  <span class='pill'>PPI {winner['ppi']:.2f}%</span>
                  <span class='pill'>Experience {winner['experience_rating']:.1f}/10</span>
                </div></div>""",
                unsafe_allow_html=True,
            )
        with right:
            st.markdown("<div class='panel'><div class='panel-title'>🏅 Leaderboard</div><div class='panel-sub'>Ranked by PPI with the mandatory deterministic tie-break rules</div>", unsafe_allow_html=True)
            leaderboard = pd.DataFrame([
                {"Rank": r["final_rank"], "Supplier": r["supplier_name"], "Absolute Score": round(r["absolute_score"],2), "PPI": round(r["ppi"],2), "Submitted": r["submission_date"], "Experience": r["experience_rating"]}
                for r in latest_results
            ])
            st.dataframe(leaderboard, use_container_width=True, hide_index=True, height=245)
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            "<div class='panel'><div class='panel-title'>🚀 Ready for your first evaluation</div><div class='panel-sub'>Upload multiple supplier proposals to activate the full agentic workflow.</div></div>",
            unsafe_allow_html=True,
        )

    col1, col2 = st.columns([1.4, 1], gap="medium")
    with col1:
        st.markdown("<div class='panel'><div class='panel-title'>📊 Score comparison</div><div class='panel-sub'>Absolute weighted score out of 100</div>", unsafe_allow_html=True)
        if latest_results:
            chart = pd.DataFrame({r["supplier_name"]: [r["absolute_score"]] for r in latest_results}).T
            chart.columns = ["Absolute Score"]
            st.bar_chart(chart, height=280)
        else:
            st.info("Complete an evaluation to see supplier comparisons.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='panel'><div class='panel-title'>🎯 Active evaluation criteria</div><div class='panel-sub'>Database-driven criteria and business weights</div>", unsafe_allow_html=True)
        for c in criteria:
            st.markdown(
                f"""<div class='score-card'>
                <div class='score-head'><span class='score-name'>{c['name']}</span><span class='score-number'>{float(c['weight']):.0f}%</span></div>
                <div class='score-bar'><div class='score-fill' style='width:{min(float(c['weight'])/30*100,100):.0f}%'></div></div>
                <div class='score-meta'>{c['description']}</div></div>""",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)
    st.markdown(
        """<div class='panel'><div class='panel-title'>🧠 AI vs Business Rules</div><div class='panel-sub'>A key design principle of the solution</div>
        <div class='metric-strip'>
          <span class='pill'>🤖 LLM: proposal judgment + evidence</span>
          <span class='pill'>🛡️ Validation: schema + normalization</span>
          <span class='pill'>🧮 Python: weighted score + PPI</span>
          <span class='pill'>🏆 Python: benchmark + tie-break + rank</span>
          <span class='pill'>💾 SQLite: complete run persistence</span>
        </div></div>""",
        unsafe_allow_html=True,
    )


def page_evaluate():
    topbar()
    st.markdown("## 🚀 Evaluate RFP Batch")
    st.caption("Upload supplier proposals, provide metadata, then let the agentic pipeline evaluate, validate, score, benchmark, rank and persist the run.")

    criteria = get_active_criteria()
    total_weight = sum(float(c["weight"]) for c in criteria)
    if abs(total_weight - 100) > 1e-9:
        st.error(f"Evaluation blocked. Active criteria weights total {total_weight:.2f}%, but must total 100%.")
        return
    if not config_status():
        st.error("Cohere API key is not configured.")
        st.info("Create .env beside app.py locally, or add COHERE_API_KEY to Streamlit Cloud Secrets.")
        return

    st.markdown(
        "<div class='metric-strip'><span class='pill'>Criteria  " + str(len(criteria)) + "</span><span class='pill'>Weight  100%</span><span class='pill'>LLM  " + COHERE_MODEL + "</span><span class='pill'>Temperature  " + str(LLM_TEMPERATURE) + "</span></div>",
        unsafe_allow_html=True,
    )

    with st.expander("🎯 Criteria used by the Evaluation Agent", expanded=True):
        df = pd.DataFrame(criteria)[["criterion_id", "name", "description", "weight", "max_score"]]
        df.columns = ["ID", "Criterion", "LLM inspects", "Weight %", "Max Score"]
        st.dataframe(df, use_container_width=True, hide_index=True)

    uploads = st.file_uploader("Supplier proposal PDFs", type=["pdf"], accept_multiple_files=True, help="Upload one PDF per supplier.")
    if not uploads:
        st.info("Upload two or more supplier PDFs to compare peers. Four synthetic proposals are available in sample_data/.")
        return

    metadata = {}
    pdf_files = {}
    valid = True
    st.markdown("### 👤 Supplier metadata")

    for upload in uploads:
        name_default = Path(upload.name).stem.replace("_", " ").replace("-", " ").title()
        with st.container(border=True):
            a, b, c = st.columns([1.5, 1, 1])
            name = a.text_input("Supplier name", value=name_default, key=f"name_{upload.name}")
            submission_date = b.date_input("Submission date", key=f"date_{upload.name}")
            experience = c.number_input("Historical experience /10", 0.0, 10.0, 7.0, 0.5, key=f"exp_{upload.name}")
            if not name.strip():
                valid = False
                st.error(f"Supplier name is required for {upload.name}.")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
                f.write(upload.getbuffer())
                temp_path = Path(f.name)
            pdf_files[upload.name] = temp_path
            metadata[upload.name] = {"supplier_name": name.strip(), "submission_date": submission_date.isoformat(), "experience_rating": float(experience)}

    st.markdown("### 🔎 Pre-flight validation")
    summary = []
    for upload in uploads:
        doc = extract_pdf_document(pdf_files[upload.name])
        summary.append({"Supplier": metadata[upload.name]["supplier_name"], "PDF": upload.name, "Pages": len(doc["pages"]), "Characters": len(doc["text"]), "Submission": metadata[upload.name]["submission_date"], "Experience": metadata[upload.name]["experience_rating"]})
    st.dataframe(pd.DataFrame(summary), use_container_width=True, hide_index=True)

    st.session_state["uploaded_documents"] = {metadata[u.name]["supplier_name"]: extract_pdf_document(pdf_files[u.name]) for u in uploads}

    if st.button("🚀 Start Agentic Evaluation", type="primary", use_container_width=True, disabled=not valid):
        try:
            state = run_agentic_evaluation(pdf_files, metadata, COHERE_API_KEY, COHERE_MODEL)
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
    topbar()
    st.markdown("## 🏆 Results Explorer")
    run_id, run, results = load_current_results()
    if not run_id:
        st.info("Run an evaluation first.")
        return
    if not results:
        st.warning("No supplier results found for this run.")
        return

    winner = results[0]
    st.markdown(
        f"<div class='winner'><div class='winner-k'>RFP RUN • {run_id}</div><div class='winner-name'>🥇 {winner['supplier_name']}</div><div class='winner-copy'>Top supplier after validated scoring, peer benchmarking, PPI and deterministic tie-break rules.</div><div class='metric-strip'><span class='pill'>Score {winner['absolute_score']:.2f}/100</span><span class='pill'>PPI {winner['ppi']:.2f}%</span><span class='pill'>Experience {winner['experience_rating']:.1f}/10</span><span class='pill'>Submitted {winner['submission_date']}</span></div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("### 🏅 Leaderboard")
    leaderboard = pd.DataFrame([
        {"Rank": r["final_rank"], "Supplier": r["supplier_name"], "Absolute Score": round(r["absolute_score"], 2), "PPI %": round(r["ppi"], 2), "Submission Date": r["submission_date"], "Experience Rating": r["experience_rating"]}
        for r in results
    ])
    st.dataframe(leaderboard, use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='panel'><div class='panel-title'>📊 Score comparison</div><div class='panel-sub'>Absolute weighted score out of 100</div>", unsafe_allow_html=True)
        chart_df = leaderboard.set_index("Supplier")[["Absolute Score"]]
        st.bar_chart(chart_df, height=300)
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='panel'><div class='panel-title'>🎯 PPI comparison</div><div class='panel-sub'>Peer Performance Index relative to the best observed criterion performance</div>", unsafe_allow_html=True)
        ppi_df = leaderboard.set_index("Supplier")[["PPI %"]]
        st.bar_chart(ppi_df, height=300)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### 🔍 Detailed supplier scorecard")
    selected = st.selectbox("Supplier", [r["supplier_name"] for r in results])
    result = next(r for r in results if r["supplier_name"] == selected)

    a, b, c, d = st.columns(4)
    a.metric("Final Rank", f"#{result['final_rank']}")
    b.metric("Absolute Score", f"{result['absolute_score']:.2f}")
    c.metric("PPI", f"{result['ppi']:.2f}%")
    d.metric("Experience", f"{result['experience_rating']:.1f}/10")

    st.markdown(f"**Overall assessment:** {result['overall_summary']}")
    if result.get("risks"):
        st.warning("Risks: " + " • ".join(result["risks"]))

    detail = pd.DataFrame([
        {"Criterion": item["criterion_name"], "Score": f"{item['score']:.2f}/{item['max_score']:.0f}", "Weight %": item["weight"], "Weighted Contribution": round(item["weighted_contribution"], 2), "Benchmark": item["benchmark"], "Gap": round(item["gap"], 2), "Relative %": round(item["relative_performance_pct"], 2)}
        for item in result["criteria"]
    ])
    st.dataframe(detail, use_container_width=True, hide_index=True)

    for item in result["criteria"]:
        with st.expander(f"{item['criterion_name']}  •  {item['score']:.2f}/{item['max_score']}", expanded=False):
            description = next((c["description"] for c in get_active_criteria() if int(c["criterion_id"]) == int(item["criterion_id"])), "")
            st.markdown(f"**Benchmark:** {item['benchmark']} &nbsp; **Gap:** {item['gap']:.2f} &nbsp; **Relative:** {item['relative_performance_pct']:.2f}% &nbsp; **Weight:** {item['weight']}%")
            st.markdown(f"**What was evaluated:** {description}")
            st.markdown(f"**Justification**\n\n{item['justification']}")
            st.markdown(f"**Evidence from proposal — page {item['evidence_page']}**\n\n> {item['evidence']}")

    warnings = json.loads(run.get("warnings_json", "[]"))
    if warnings:
        with st.expander(f"⚠️ Validation warnings ({len(warnings)})"):
            for warning in warnings:
                st.write("• " + warning)

    st.markdown("### ⚖️ Deterministic ranking rule")
    st.info(result["tie_break_rule"])

    payload = {"rfp_run_id": run_id, "criteria": json.loads(run["criteria_snapshot_json"]), "suppliers": results, "run_warnings": warnings}
    st.download_button("⬇️ Download complete evaluation JSON", json.dumps(payload, indent=2, ensure_ascii=False), file_name=f"{run_id}_complete_result.json", mime="application/json", use_container_width=True)


def page_criteria():
    topbar()
    st.markdown("## 🎯 Criteria Studio")
    st.caption("Criteria are database-driven. Activate/deactivate criteria or change weights without changing the evaluation prompt code.")
    criteria = get_all_criteria()
    st.dataframe(pd.DataFrame(criteria), use_container_width=True, hide_index=True)

    selected_id = st.selectbox("Criterion to edit", [int(c["criterion_id"]) for c in criteria], format_func=lambda x: next(c["name"] for c in criteria if int(c["criterion_id"]) == x))
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
    topbar()
    st.markdown("## 📄 Proposal Viewer")
    st.caption("Read the extracted supplier proposal page-by-page and compare the source text with the evidence used by the LLM scorecard.")
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


def page_run_details():
    topbar()
    st.markdown("## 🧾 Run Details")
    run_id, run, results = load_current_results()
    if not run:
        st.info("No completed run available.")
        return
    a, b, c = st.columns(3)
    a.metric("RFP_RUN_ID", run_id)
    b.metric("Status", run["status"])
    c.metric("Suppliers", len(results))
    st.markdown("### 📌 Run metadata")
    st.json({"rfp_run_id": run["rfp_run_id"], "created_at": run["created_at"], "status": run["status"], "database": str(RFP_DB_PATH)})
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
    topbar()
    st.markdown("## 🧪 Validation Lab")
    st.caption("Demonstrates the validation tool independently. This does not replace the production Cohere path.")
    criteria = get_active_criteria()
    malformed = {"supplier_name": "Example Supplier", "criteria": [{"criterion_id": 1, "score": 14, "max_score": 10, "justification": "", "evidence": "", "evidence_page": "not-a-number"}], "risks": [], "overall_summary": ""}
    result = validate_and_normalize(malformed, "Example Supplier", criteria)
    st.markdown("### Expected validation issues")
    for warning in result["warnings"]:
        st.warning(warning)
    st.markdown("### Normalized result")
    st.dataframe(pd.DataFrame(result["criteria"]), use_container_width=True, hide_index=True)


def page_architecture():
    topbar()
    st.markdown("## 🧭 Agentic Workflow & Tool Separation")
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
    st.code("START\n  ↓\nload_criteria\n  ↓\nextract_documents\n  ↓\nevaluate_suppliers  ← REAL COHERE\n  ↓\nvalidate_outputs\n  ↓\ncalculate_scores    ← Python\n  ↓\nbenchmark_and_rank  ← Python\n  ↓\npersist_results     ← SQLite\n  ↓\nEND", language="text")
    st.markdown("### 🛡️ Why this is agentic")
    st.write("The orchestrator invokes specialized components in sequence. The LLM is constrained to proposal-content judgment; deterministic tools own business rules and persistence. This makes the final score traceable and reproducible after LLM scorecards have been validated.")


def run_app():
    inject_css()
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
    st.markdown("<div class='footer-note'>Agentic RFP Evaluation • Evidence-grounded AI • Deterministic business rules • SQLite persistence</div>", unsafe_allow_html=True)
