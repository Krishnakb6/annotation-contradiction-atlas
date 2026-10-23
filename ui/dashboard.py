"""
Page 1: Overview Dashboard.
Displays live database metrics, evidence distributions, review priority breakdown,
and analytical run telemetry.
"""
from __future__ import annotations

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from sqlalchemy import func, desc

from database.connection import get_db_session
from database.models import Protein, FunctionAnnotation, ReviewFlag, SequenceFeature, AnalysisRun
from ui.styles import render_priority_badge


def render_dashboard():
    st.title("Atlas Overview Dashboard")
    st.markdown(
        "A scientific monitoring interface for human protein kinase records, evaluating annotation "
        "congruence across **ESM-2 protein language model embeddings**, **sequence similarity baselines**, "
        "**catalytic motif integrity**, and **annotation provenance**."
    )

    with get_db_session() as session:
        total_proteins = session.query(Protein).count()

        if total_proteins == 0:
            st.warning("No protein records found in the database. Please visit **Data Management** to import the human kinome.")
            if st.button("Go to Data Management", type="primary"):
                st.session_state["current_page"] = "Data Management"
                st.rerun()
            return

        reviewed_count = session.query(Protein).filter(Protein.reviewed == True).count()
        unreviewed_count = session.query(Protein).filter(Protein.reviewed == False).count()
        annotations_count = session.query(FunctionAnnotation).count()
        analyzed_count = session.query(ReviewFlag).count()

        # Priority breakdown
        high_flags = session.query(ReviewFlag).filter(ReviewFlag.review_priority == "HIGH").count()
        mod_flags = session.query(ReviewFlag).filter(ReviewFlag.review_priority == "MODERATE").count()
        low_flags = session.query(ReviewFlag).filter(ReviewFlag.review_priority == "LOW").count()

        # Latest run
        latest_run_obj = session.query(AnalysisRun).filter(AnalysisRun.run_status == "COMPLETED").order_by(desc(AnalysisRun.completion_time)).first()
        latest_run_meta = None
        if latest_run_obj:
            latest_run_meta = {
                "run_identifier": latest_run_obj.run_identifier,
                "dataset_version": latest_run_obj.dataset_version,
                "run_status": latest_run_obj.run_status,
                "random_seed": latest_run_obj.random_seed,
                "completion_str": latest_run_obj.completion_time.strftime('%Y-%m-%d %H:%M UTC') if latest_run_obj.completion_time else 'N/A',
            }

    # Metric KPI cards
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{total_proteins:,}</div><div class="metric-label">Imported Kinases</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{annotations_count:,}</div><div class="metric-label">Functional Annotations</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{analyzed_count:,}</div><div class="metric-label">Analyzed Entries</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-card"><div class="metric-value" style="color: #991B1B;">{high_flags:,}</div><div class="metric-label">High Review Priority</div></div>', unsafe_allow_html=True)
    with c5:
        st.markdown(f'<div class="metric-card"><div class="metric-value" style="color: #D97706;">{mod_flags:,}</div><div class="metric-label">Moderate Priority</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("Review Priority Distribution")
        if analyzed_count > 0:
            df_prio = pd.DataFrame([
                {"Priority": "High Review Priority", "Count": high_flags, "Color": "#EF4444"},
                {"Priority": "Moderate Review Priority", "Count": mod_flags, "Color": "#F59E0B"},
                {"Priority": "Low / Congruent", "Count": low_flags, "Color": "#10B981"},
            ])
            fig_prio = px.pie(
                df_prio,
                names="Priority",
                values="Count",
                color="Priority",
                color_discrete_map={
                    "High Review Priority": "#EF4444",
                    "Moderate Review Priority": "#F59E0B",
                    "Low / Congruent": "#10B981",
                },
                hole=0.45,
            )
            fig_prio.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=320)
            st.plotly_chart(fig_prio, use_container_width=True)
        else:
            st.info("No records analyzed yet. Run analysis pipeline in Data Management.")

    with col_right:
        st.subheader("Annotation Evidence Tiers (Provenance)")
        with get_db_session() as session:
            ev_counts = session.query(
                FunctionAnnotation.evidence_category, func.count(FunctionAnnotation.id)
            ).group_by(FunctionAnnotation.evidence_category).all()
        if ev_counts:
            df_ev = pd.DataFrame(ev_counts, columns=["Evidence Tier", "Count"])
            df_ev["Evidence Tier"] = df_ev["Evidence Tier"].str.replace("_", " ").str.title()
            fig_ev = px.bar(
                df_ev,
                x="Evidence Tier",
                y="Count",
                text="Count",
                color="Evidence Tier",
                color_discrete_sequence=px.colors.qualitative.Prism,
            )
            fig_ev.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=320, showlegend=False)
            fig_ev.update_traces(textposition="outside")
            st.plotly_chart(fig_ev, use_container_width=True)
        else:
            st.info("No functional annotations available.")

    st.markdown("---")

    # Analytical run details & common contradiction reasons
    col_reasons, col_run = st.columns([1.3, 0.7])

    with col_reasons:
        st.subheader("Common Signals Triggering Review Flags")
        signals = []
        with get_db_session() as session:
            flags = session.query(ReviewFlag).filter(ReviewFlag.review_priority.in_(["HIGH", "MODERATE"])).limit(200).all()
            for f in flags:
                sig_str = f.contradictory_signals or ""
                for sig in sig_str.split(";"):
                    s_clean = sig.strip()
                    if s_clean and "no active" not in s_clean.lower():
                        signals.append(s_clean.split("[")[0].strip())

        if signals:
            df_sig = pd.Series(signals).value_counts().reset_index()
            df_sig.columns = ["Contradictory Signal", "Occurrences"]
            fig_sig = px.bar(
                df_sig.head(6),
                y="Contradictory Signal",
                x="Occurrences",
                orientation="h",
                color="Occurrences",
                color_continuous_scale="Reds",
            )
            fig_sig.update_layout(yaxis=dict(autorange="reversed"), height=280, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_sig, use_container_width=True)
        else:
            st.write("All analyzed records appear congruent with reference profiles.")

    with col_run:
        st.subheader("Latest Computational Run")
        if latest_run_meta:
            st.markdown(f"""
            - **Run ID:** `{latest_run_meta['run_identifier']}`
            - **Dataset Version:** `{latest_run_meta['dataset_version']}`
            - **Status:** `{latest_run_meta['run_status']}`
            - **Random Seed:** `{latest_run_meta['random_seed']}`
            - **Completed:** `{latest_run_meta['completion_str']}`
            """)
            st.success("Run completed with reproducible checkpoints.")
        else:
            st.info("No completed analysis runs recorded yet.")
