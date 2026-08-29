import json
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from db import get_active_criteria, get_run, init_db, seed_criteria
from orchestrator import evaluate_batch


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="RFP Intelligence Hub",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# APP SETUP
# ============================================================

init_db()
seed_criteria()

criteria = get_active_criteria()
weight_total = sum(float(c["weight"]) for c in criteria)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>
    /* ---------- Global ---------- */
    .stApp {
        background: #f7f9fc;
    }

    .block-container {
        max-width: 1400px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    /* ---------- Header ---------- */
    .hero {
        padding: 1.6rem 1.8rem;
        border-radius: 18px;
        background: linear-gradient(135deg, #102a43 0%, #1f4e79 55%, #2878b5 100%);
        color: white;
        margin-bottom: 1.3rem;
        box-shadow: 0 10px 30px rgba(16, 42, 67, 0.15);
    }

    .hero h1 {
        margin: 0;
        font-size: 2.1rem;
        font-weight: 750;
        letter-spacing: -0.5px;
    }

    .hero p {
        margin: 0.45rem 0 0 0;
        opacity: 0.88;
        font-size: 1rem;
    }

    /* ---------- Cards ---------- */
    .info-card {
        background: white;
        border: 1px solid #e6ebf2;
        border-radius: 14px;
        padding: 1rem 1.1rem;
        box-shadow: 0 3px 12px rgba(31, 78, 121, 0.06);
        height: 100%;
    }

    .card-label {
        color: #667085;
        font-size: 0.78rem;
        font-weight: 650;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .card-value {
        color: #102a43;
        font-size: 1.45rem;
        font-weight: 750;
        margin-top: 0.2rem;
    }

    .card-sub {
        color: #667085;
        font-size: 0.82rem;
        margin-top: 0.15rem;
    }

    /* ---------- Supplier cards ---------- */
    .supplier-card {
        background: white;
        border: 1px solid #e6ebf2;
        border-radius: 14px;
        padding: 0.9rem 1rem;
        margin-bottom: 0.6rem;
        box-shadow: 0 3px 10px rgba(31, 78, 121, 0.05);
    }

    .supplier-name {
        font-size: 1.05rem;
        font-weight: 720;
        color: #102a43;
    }

    .supplier-file {
        color: #667085;
        font-size: 0.78rem;
    }

    /* ---------- Ranking ---------- */
    .rank-badge {
        display: inline-block;
        min-width: 42px;
        padding: 0.25rem 0.55rem;
        border-radius: 20px;
        text-align: center;
        font-weight: 750;
        background: #eef4fb;
        color: #1f4e79;
    }

    .rank-1 {
        background: #fff4cc;
        color: #8a6500;
    }

    .rank-2 {
        background: #edf0f4;
        color: #59636e;
    }

    .rank-3 {
        background: #f8e8dc;
        color: #8a5638;
    }

    /* ---------- Section headings ---------- */
    .section-title {
        color: #102a43;
        font-size: 1.25rem;
        font-weight: 750;
        margin-top: 0.3rem;
        margin-bottom: 0.2rem;
    }

    .section-caption {
        color: #667085;
        font-size: 0.9rem;
        margin-bottom: 0.8rem;
    }

    /* ---------- Status ---------- */
    .status-pill {
        display: inline-block;
        padding: 0.3rem 0.7rem;
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 700;
        background: #e8f7ee;
        color: #177245;
    }

    /* ---------- Hide default decoration ---------- */
    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    /* ---------- Buttons ---------- */
    div.stButton > button[kind="primary"] {
        border-radius: 10px;
        min-height: 2.7rem;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="hero">
        <h1>📊 RFP Intelligence Hub</h1>
        <p>
            Evidence-grounded supplier evaluation with deterministic scoring,
            peer benchmarking and transparent ranking.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("## ⚙️ Evaluation Setup")

    st.markdown("### Active criteria")

    for criterion in criteria:
        st.markdown(
            f"""
            <div style="
                background:#ffffff;
                border:1px solid #e6ebf2;
                border-radius:10px;
                padding:0.65rem 0.75rem;
                margin-bottom:0.45rem;
            ">
                <div style="font-weight:700;color:#102a43;font-size:0.88rem;">
                    {criterion["name"]}
                </div>
                <div style="color:#667085;font-size:0.75rem;margin-top:0.2rem;">
                    Weight: {criterion["weight"]:.0f}% &nbsp;•&nbsp;
                    Max: {criterion["max_score"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    if abs(weight_total - 100.0) < 1e-9:
        st.success(f"✓ Criteria weights: {weight_total:.0f}%")
    else:
        st.error(f"Criteria weights: {weight_total:.2f}%")

    st.markdown("### 🤖 Decision model")

    st.markdown(
        """
        <div style="
            background:#eef6ff;
            border-left:4px solid #2878b5;
            padding:0.8rem;
            border-radius:7px;
            font-size:0.82rem;
            color:#344054;
        ">
        <b>LLM</b> → evaluates proposal evidence<br>
        <b>Python</b> → validates, scores and ranks<br>
        <b>SQLite</b> → persists every run
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.caption("Agentic RFP Evaluation • Streamlit")


# ============================================================
# TOP KPI STRIP
# ============================================================

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(
        f"""
        <div class="info-card">
            <div class="card-label">Evaluation criteria</div>
            <div class="card-value">{len(criteria)}</div>
            <div class="card-sub">Active criteria</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k2:
    st.markdown(
        f"""
        <div class="info-card">
            <div class="card-label">Weight allocation</div>
            <div class="card-value">{weight_total:.0f}%</div>
            <div class="card-sub">Must equal 100%</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k3:
    supplier_count = len(st.session_state.get("results", []))
    st.markdown(
        f"""
        <div class="info-card">
            <div class="card-label">Suppliers evaluated</div>
            <div class="card-value">{supplier_count}</div>
            <div class="card-sub">Current loaded run</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k4:
    current_run = st.session_state.get("run_id", "—")
    st.markdown(
        f"""
        <div class="info-card">
            <div class="card-label">Current run</div>
            <div class="card-value" style="font-size:1rem;">{current_run}</div>
            <div class="card-sub">RFP_RUN_ID</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")


# ============================================================
# MAIN TABS
# ============================================================

input_tab, results_tab, run_tab = st.tabs(
    [
        "📥 Supplier Input",
        "🏆 Leaderboard & Scorecards",
        "🗃️ Run Details",
    ]
)


# ============================================================
# SUPPLIER INPUT
# ============================================================

with input_tab:
    st.markdown(
        '<div class="section-title">📥 Build your supplier evaluation batch</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-caption">Upload proposals, provide the required supplier metadata, then run the evaluation.</div>',
        unsafe_allow_html=True,
    )

    uploads = st.file_uploader(
        "Drop supplier PDF proposals here",
        type=["pdf"],
        accept_multiple_files=True,
        help="Upload two or more supplier proposals to enable peer benchmarking.",
    )

    suppliers = []

    if uploads:
        st.markdown(f"**{len(uploads)} proposal(s) uploaded**")

        for i, upload in enumerate(uploads):
            default_name = Path(upload.name).stem.replace("_", " ").title()

            with st.container(border=True):
                st.markdown(
                    f"""
                    <div class="supplier-card">
                        <div class="supplier-name">📄 {default_name}</div>
                        <div class="supplier-file">{upload.name} • {upload.size / 1024:.1f} KB</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                c1, c2, c3 = st.columns([2.2, 1.2, 1.2])

                with c1:
                    name = st.text_input(
                        "Supplier name",
                        value=default_name,
                        key=f"name_{i}",
                    ).strip()

                with c2:
                    submission_date = st.date_input(
                        "Submission date",
                        value=date.today(),
                        key=f"date_{i}",
                    )

                with c3:
                    experience = st.number_input(
                        "Experience rating",
                        min_value=0.0,
                        max_value=10.0,
                        value=7.0,
                        step=0.5,
                        key=f"experience_{i}",
                        help="Historical supplier experience rating from 0 to 10.",
                    )

                suppliers.append(
                    {
                        "supplier_name": name,
                        "submission_date": submission_date.isoformat(),
                        "experience_rating": experience,
                        "pdf_bytes": upload.getvalue(),
                        "file_name": upload.name,
                    }
                )

        st.write("")

        if len(suppliers) >= 2:
            st.info(
                "🔎 Peer benchmarking is enabled. The highest valid score for each criterion "
                "will become the benchmark."
            )
        else:
            st.warning("Upload at least two proposals for peer benchmarking.")

        st.write("")

        evaluate_clicked = st.button(
            "🚀 Evaluate Supplier Batch",
            type="primary",
            use_container_width=True,
        )

        if evaluate_clicked:
            if len(suppliers) < 2:
                st.error("At least two suppliers are required for peer benchmarking.")

            elif any(not s["supplier_name"] for s in suppliers):
                st.error("Every supplier must have a name.")

            elif abs(weight_total - 100.0) > 1e-9:
                st.error(
                    f"Active criterion weights must total 100%. "
                    f"Current total: {weight_total:.2f}%."
                )

            else:
                progress = st.progress(0, text="Starting evaluation...")

                try:
                    progress.progress(
                        15,
                        text="Preparing supplier proposals..."
                    )

                    with st.spinner(
                        "Extracting PDFs → calling Cohere → validating → ranking..."
                    ):
                        run_id, used_criteria, results, warnings = evaluate_batch(
                            suppliers
                        )

                    progress.progress(100, text="Evaluation completed.")

                    st.session_state.update(
                        run_id=run_id,
                        criteria=used_criteria,
                        results=results,
                        warnings=warnings,
                    )

                    st.success(
                        f"✅ Evaluation completed successfully — {run_id}"
                    )

                    st.info(
                        "Go to **Leaderboard & Scorecards** to review the supplier ranking."
                    )

                except Exception as exc:
                    progress.empty()
                    st.error(f"❌ Evaluation failed: {exc}")


# ============================================================
# RESULTS
# ============================================================

with results_tab:
    if "results" not in st.session_state:
        st.info(
            "👋 No evaluation results yet. Upload supplier proposals in "
            "**Supplier Input** and run an evaluation."
        )

    else:
        results = st.session_state["results"]

        st.markdown(
            '<div class="section-title">🏆 Supplier leaderboard</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="section-caption">Suppliers are ranked deterministically using PPI and the required tie-break rules.</div>',
            unsafe_allow_html=True,
        )

        # ----------------------------
        # Winner / podium cards
        # ----------------------------

        top_results = results[:3]
        podium_cols = st.columns(len(top_results))

        for idx, result in enumerate(top_results):
            rank = result["final_rank"]

            if rank == 1:
                icon = "🥇"
                rank_class = "rank-1"
            elif rank == 2:
                icon = "🥈"
                rank_class = "rank-2"
            else:
                icon = "🥉"
                rank_class = "rank-3"

            with podium_cols[idx]:
                st.markdown(
                    f"""
                    <div class="info-card">
                        <div>
                            <span class="rank-badge {rank_class}">
                                {icon} #{rank}
                            </span>
                        </div>
                        <div style="
                            color:#102a43;
                            font-size:1.1rem;
                            font-weight:750;
                            margin-top:0.65rem;
                        ">
                            {result["supplier_name"]}
                        </div>
                        <div style="
                            display:flex;
                            gap:1.5rem;
                            margin-top:0.7rem;
                        ">
                            <div>
                                <div class="card-label">Score</div>
                                <div style="font-size:1.25rem;font-weight:750;">
                                    {result["absolute_score"]:.2f}
                                </div>
                            </div>
                            <div>
                                <div class="card-label">PPI</div>
                                <div style="font-size:1.25rem;font-weight:750;">
                                    {result["ppi"]:.2f}%
                                </div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.write("")

        # ----------------------------
        # Full leaderboard
        # ----------------------------

        board = pd.DataFrame(
            [
                {
                    "Rank": r["final_rank"],
                    "Supplier": r["supplier_name"],
                    "Absolute Score": r["absolute_score"],
                    "PPI": r["ppi"],
                    "Submission Date": r["submission_date"],
                    "Experience": r["experience_rating"],
                }
                for r in results
            ]
        )

        st.dataframe(
            board,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Rank": st.column_config.NumberColumn("Rank", width="small"),
                "Supplier": st.column_config.TextColumn("Supplier", width="medium"),
                "Absolute Score": st.column_config.NumberColumn(
                    "Absolute Score",
                    format="%.2f",
                ),
                "PPI": st.column_config.NumberColumn(
                    "PPI",
                    format="%.2f%%",
                ),
                "Submission Date": st.column_config.DateColumn(
                    "Submission Date",
                    format="YYYY-MM-DD",
                ),
                "Experience": st.column_config.NumberColumn(
                    "Experience",
                    format="%.1f",
                ),
            },
        )

        # ----------------------------
        # Visual score comparison
        # ----------------------------

        st.markdown(
            '<div class="section-title">📈 Score comparison</div>',
            unsafe_allow_html=True,
        )

        chart_df = board.set_index("Supplier")[["Absolute Score", "PPI"]].copy()
        chart_df["PPI"] = chart_df["PPI"] / 100.0
        chart_df = chart_df.rename(columns={"PPI": "PPI (0-1)"})

        st.bar_chart(chart_df)

        # ----------------------------
        # Detailed scorecards
        # ----------------------------

        st.markdown(
            '<div class="section-title">🔍 Detailed scorecards</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="section-caption">Trace every result from criterion score to benchmark, gap, relative performance and evidence.</div>',
            unsafe_allow_html=True,
        )

        for result in results:
            rank = result["final_rank"]

            with st.expander(
                f'#{rank}  {result["supplier_name"]}  •  '
                f'Score {result["absolute_score"]:.2f}  •  '
                f'PPI {result["ppi"]:.2f}%',
                expanded=(rank == 1),
            ):
                m1, m2, m3, m4 = st.columns(4)

                with m1:
                    st.metric(
                        "Absolute Score",
                        f'{result["absolute_score"]:.2f}/100',
                    )

                with m2:
                    st.metric(
                        "PPI",
                        f'{result["ppi"]:.2f}%',
                    )

                with m3:
                    st.metric(
                        "Experience",
                        f'{result["experience_rating"]:.1f}/10',
                    )

                with m4:
                    st.metric(
                        "Submission",
                        result["submission_date"],
                    )

                st.write("")

                detail_df = pd.DataFrame(result["criterion_details"])

                display_df = detail_df[
                    [
                        "criterion_name",
                        "score",
                        "max_score",
                        "weight",
                        "benchmark",
                        "gap",
                        "relative_performance_pct",
                    ]
                ].copy()

                st.dataframe(
                    display_df,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "criterion_name": st.column_config.TextColumn(
                            "Criterion"
                        ),
                        "score": st.column_config.NumberColumn(
                            "Score",
                            format="%.2f",
                        ),
                        "max_score": st.column_config.NumberColumn(
                            "Max",
                            format="%.2f",
                        ),
                        "weight": st.column_config.NumberColumn(
                            "Weight %",
                            format="%.0f",
                        ),
                        "benchmark": st.column_config.NumberColumn(
                            "Benchmark",
                            format="%.2f",
                        ),
                        "gap": st.column_config.NumberColumn(
                            "Gap",
                            format="%.2f",
                        ),
                        "relative_performance_pct": st.column_config.NumberColumn(
                            "Relative %",
                            format="%.2f%%",
                        ),
                    },
                )

                st.write("")

                for detail in result["criterion_details"]:
                    with st.container(border=True):
                        left, right = st.columns([1.15, 2.85])

                        with left:
                            st.markdown(
                                f"**{detail['criterion_name']}**"
                            )
                            st.metric(
                                "Score",
                                f'{detail["score"]:.1f}/{detail["max_score"]:.1f}',
                            )
                            st.progress(
                                min(
                                    max(
                                        detail["score"] /
                                        detail["max_score"],
                                        0.0,
                                    ),
                                    1.0,
                                )
                            )

                            st.caption(
                                f'Weight: {detail["weight"]:.0f}% • '
                                f'Benchmark: {detail["benchmark"]:.2f} • '
                                f'Gap: {detail["gap"]:.2f}'
                            )

                        with right:
                            st.markdown("**📌 Evidence**")
                            st.write(
                                detail["evidence"]
                                or "No evidence returned."
                            )

                            st.markdown("**💡 Justification**")
                            st.write(
                                detail["justification"]
                                or "No justification returned."
                            )

                if result.get("risks"):
                    st.warning(
                        "⚠️ **Risks / Dependencies:** "
                        + " • ".join(result["risks"])
                    )

                st.info(
                    f'**Overall assessment:** {result["overall_summary"]}'
                )

                st.caption(
                    f'Ranking rule: {result["tie_break_explanation"]}'
                )

        # ----------------------------
        # Downloads and warnings
        # ----------------------------

        st.markdown(
            '<div class="section-title">📦 Export</div>',
            unsafe_allow_html=True,
        )

        export = {
            "rfp_run_id": st.session_state["run_id"],
            "criteria": st.session_state["criteria"],
            "suppliers": results,
            "warnings": st.session_state.get("warnings", []),
        }

        e1, e2 = st.columns(2)

        with e1:
            st.download_button(
                "⬇️ Download Complete Result JSON",
                data=json.dumps(
                    export,
                    indent=2,
                    ensure_ascii=False,
                ),
                file_name=f'{st.session_state["run_id"]}.json',
                mime="application/json",
                use_container_width=True,
            )

        with e2:
            st.download_button(
                "⬇️ Download Leaderboard CSV",
                data=board.to_csv(index=False),
                file_name=f'{st.session_state["run_id"]}_leaderboard.csv',
                mime="text/csv",
                use_container_width=True,
            )

        warnings = st.session_state.get("warnings", [])

        if warnings:
            st.markdown(
                '<div class="section-title">⚠️ Validation warnings</div>',
                unsafe_allow_html=True,
            )

            for warning in warnings:
                st.warning(warning)


# ============================================================
# RUN DETAILS
# ============================================================

with run_tab:
    if "run_id" not in st.session_state:
        st.info(
            "No persisted run selected. Complete an evaluation first."
        )

    else:
        run_id = st.session_state["run_id"]
        run, rows = get_run(run_id)

        st.markdown(
            '<div class="section-title">🗃️ Evaluation run</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="section-caption">Audit-friendly details for the persisted evaluation run.</div>',
            unsafe_allow_html=True,
        )

        if run:
            r1, r2, r3 = st.columns(3)

            with r1:
                st.markdown(
                    f"""
                    <div class="info-card">
                        <div class="card-label">RFP Run ID</div>
                        <div class="card-value" style="font-size:1.05rem;">
                            {run["rfp_run_id"]}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with r2:
                st.markdown(
                    f"""
                    <div class="info-card">
                        <div class="card-label">Status</div>
                        <div class="card-value">
                            {run["status"]}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with r3:
                st.markdown(
                    f"""
                    <div class="info-card">
                        <div class="card-label">Created</div>
                        <div class="card-value" style="font-size:1rem;">
                            {run["created_at"]}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.write("")

        st.markdown("### 🔐 Deterministic ranking rule")

        st.code(
            """1. Higher PPI
2. Earlier submission date
3. Higher historical experience rating
4. Supplier name ascending""",
            language="text",
        )

        st.markdown("### 🧮 Calculation pipeline")

        st.code(
            """LLM evaluation
      ↓
JSON validation / normalization
      ↓
Weighted absolute score
      ↓
Criterion benchmark
      ↓
Criterion gap
      ↓
Relative performance %
      ↓
Weighted PPI
      ↓
Deterministic tie-break
      ↓
Final rank
      ↓
SQLite persistence""",
            language="text",
        )

        persisted = {
            "rfp_run": run,
            "supplier_results": [
                {
                    **row,
                    "result_json": json.loads(row["result_json"]),
                }
                for row in rows
            ],
        }

        st.download_button(
            "⬇️ Download Persisted Run JSON",
            data=json.dumps(
                persisted,
                indent=2,
                ensure_ascii=False,
            ),
            file_name=f"{run_id}_persisted.json",
            mime="application/json",
            use_container_width=True,
        )
