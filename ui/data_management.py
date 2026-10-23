"""
Page 6: Data Management & Ingestion Pipeline Controls.
Enables UniProt data refreshes, embedding generation jobs, benchmark execution,
and schema inspection.
"""
from __future__ import annotations

import subprocess
import streamlit as st
import pandas as pd
from sqlalchemy import func

from config import DEFAULT_MAX_RECORDS, DEFAULT_ESM_MODEL, RANDOM_SEED
from database.connection import get_db_session, init_db
from database.models import Protein, FunctionAnnotation, ReviewFlag, EmbeddingRecord, BenchmarkCase, SequenceFeature
from database.schema import get_schema_summary
from services.data_import import DataImportService
from services.benchmark import BenchmarkService


def render_data_management():
    st.title("Data Management & Pipeline Execution")
    st.markdown(
        "Manage UniProtKB data ingestion, trigger language model embedding workflows, "
        "and control evaluation benchmarks."
    )

    # Database Summary Metrics
    with get_db_session() as session:
        prot_cnt = session.query(Protein).count()
        ann_cnt = session.query(FunctionAnnotation).count()
        flag_cnt = session.query(ReviewFlag).count()
        emb_cnt = session.query(EmbeddingRecord).count()
        feat_cnt = session.query(SequenceFeature).count()
        bench_cnt = session.query(BenchmarkCase).count()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Proteins in DB", f"{prot_cnt:,}")
    with c2:
        st.metric("Annotations Stored", f"{ann_cnt:,}")
    with c3:
        st.metric("Flagged / Analyzed", f"{flag_cnt:,}")
    with c4:
        st.metric("ESM-2 Embeddings", f"{emb_cnt:,}")

    st.markdown("---")

    # Ingestion Controls
    st.subheader("1. UniProtKB Data Ingestion")
    st.markdown(
        "Fetches human protein kinase records directly from the UniProtKB REST API with pagination, "
        "rate-limiting, response caching, and atomic database insertion."
    )

    col_ing1, col_ing2, col_ing3 = st.columns([1.5, 1, 1])
    with col_ing1:
        max_recs = st.slider("Target Record Count", min_value=50, max_value=600, value=500, step=50)
    with col_ing2:
        reviewed_only = st.checkbox("Reviewed Only (Swiss-Prot)", value=True)
    with col_ing3:
        force_refresh = st.checkbox("Force Live Refresh (Bypass Cache)", value=False)

    if st.button("Fetch / Refresh UniProt Kinome", type="primary"):
        with st.spinner("Connecting to UniProtKB API and importing validated kinase records..."):
            import_service = DataImportService()
            summary = import_service.import_kinases(
                max_records=max_recs,
                reviewed_only=reviewed_only,
                force_refresh=force_refresh,
            )
            st.success(f"Import complete: {summary['newly_inserted']} inserted, {summary['updated']} updated, {summary['annotations_saved']} annotations saved.")
            st.rerun()

    st.markdown("---")

    # Analytical Pipeline Controls
    st.subheader("2. Computational Analysis Pipeline")
    st.markdown(
        "Executes **Method A** (Sequence similarity baseline), **Method B** (ESM-2 language model representations), "
        "**Method D** (Kinase catalytic motifs), and **Method E** (Annotation provenance) to synthesize "
        "evidence-aware contradiction scores."
    )

    col_an1, col_an2 = st.columns([1.5, 1])
    with col_an1:
        analysis_limit = st.selectbox(
            "Record Limit for Run",
            [("Quick Run (50 proteins)", 50), ("Standard Run (150 proteins)", 150), ("Full Kinome (All proteins in DB)", None)],
            format_func=lambda x: x[0],
            index=1,
        )
    with col_an2:
        esm_model = st.text_input("ESM-2 Model Identifier", value=DEFAULT_ESM_MODEL)

    if st.button("Execute Computational Analysis Pipeline", type="primary"):
        with st.spinner("Running full analytical pipeline across protein kinase records..."):
            from scripts.run_analysis import run_full_pipeline
            summary = run_full_pipeline(limit=analysis_limit[1], model_name=esm_model, seed=RANDOM_SEED)
            st.success(f"Pipeline executed successfully! Analyzed {summary.get('total_analyzed', 0)} proteins. Priority Breakdown: {summary.get('priority_counts', {})}")
            st.rerun()

    st.markdown("---")

    # Benchmark & Evaluation Controls
    st.subheader("3. Evaluation Benchmark Suite")
    st.markdown(
        "Generates controlled synthetic test cases (catalytic lysine/aspartate knockouts, label swaps) "
        "and evaluates detection accuracy across all methods."
    )

    col_b1, col_b2 = st.columns([1.5, 1])
    with col_b1:
        num_synthetic = st.slider("Number of Synthetic Cases", min_value=12, max_value=60, value=32, step=4)
    with col_b2:
        eval_seed = st.number_input("Random Seed", value=RANDOM_SEED)

    col_btn_eval, col_btn_clear = st.columns([1, 1])
    with col_btn_eval:
        if st.button("Run Benchmark Evaluation", key="btn_eval_run"):
            with st.spinner("Generating controlled benchmark cases and executing evaluation..."):
                res = subprocess.run(["python", "scripts/run_evaluation.py", "--num-synthetic", str(num_synthetic), "--seed", str(eval_seed)], capture_output=True, text=True)
                st.success("Benchmark completed! Check results on the 'Analysis & Evaluation' page.")
                st.rerun()

    with col_btn_clear:
        if st.button("Clear Synthetic Cases from DB", key="btn_eval_clear"):
            bench_service = BenchmarkService()
            with get_db_session() as session:
                from database.repositories import BenchmarkRepository
                b_repo = BenchmarkRepository(session)
                deleted = b_repo.clear_synthetic_cases()
            st.success(f"Cleared {deleted} synthetic cases.")
            st.rerun()

    st.markdown("---")

    # Database Schema Inspection
    st.subheader("4. Database Schema & Integrity")
    with st.expander("Inspect SQLite Relational Schema Tables and Indexes", expanded=False):
        schema_info = get_schema_summary()
        for t_name, t_meta in schema_info.items():
            st.markdown(f"**Table: `{t_name}`**")
            cols_df = pd.DataFrame(t_meta["columns"])
            st.dataframe(cols_df, use_container_width=True, hide_index=True)
            if t_meta["indexes"]:
                st.caption(f"Indexes: {', '.join([i['name'] for i in t_meta['indexes']])}")
            st.markdown("<br/>", unsafe_allow_html=True)
