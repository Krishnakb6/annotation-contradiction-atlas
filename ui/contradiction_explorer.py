"""
Page 4: Contradiction Explorer.
Investigates flagged kinase review candidates, signal breakdowns,
and provides side-by-side comparative inspection against closest reference kinases.
"""
from __future__ import annotations

import streamlit as st
import plotly.express as px
import pandas as pd
from sqlalchemy.orm import joinedload
from sqlalchemy import desc

from database.connection import get_db_session
from database.models import Protein, ReviewFlag, SequenceFeature, ModelResult, FunctionAnnotation
from ui.styles import render_priority_badge


def render_contradiction_explorer():
    st.title("Annotation Contradiction Explorer")
    st.markdown(
        "Interactive investigation environment for potential annotation conflicts, atypical variants, "
        "and pseudokinases detected across multi-evidence analysis methods."
    )

    with get_db_session() as session:
        # Load all flagged proteins with review priority HIGH or MODERATE
        flags = session.query(ReviewFlag).options(
            joinedload(ReviewFlag.protein).joinedload(Protein.sequence_features),
            joinedload(ReviewFlag.protein).joinedload(Protein.annotations),
            joinedload(ReviewFlag.protein).joinedload(Protein.model_results),
        ).filter(ReviewFlag.review_priority.in_(["HIGH", "MODERATE"])).order_by(desc(ReviewFlag.contradiction_score)).all()

    if not flags:
        st.info("No proteins currently flagged with HIGH or MODERATE review priority. Run computational analysis to generate flags.")
        return

    # Filter controls
    col_prio, col_signal = st.columns([1, 2])
    with col_prio:
        filter_priority = st.selectbox("Filter by Priority", ["All Flagged (High + Moderate)", "HIGH only", "MODERATE only"])
    with col_signal:
        signal_filter = st.selectbox("Filter by Contradictory Signal", [
            "All Signals",
            "Missing catalytic motif(s)",
            "Variant motif sequence",
            "ESM-2 embedding outlier",
            "Purely computational / unreviewed provenance",
        ])

    filtered_flags = []
    for f in flags:
        if filter_priority == "HIGH only" and f.review_priority != "HIGH":
            continue
        if filter_priority == "MODERATE only" and f.review_priority != "MODERATE":
            continue
        if signal_filter != "All Signals":
            if signal_filter.lower() not in f.contradictory_signals.lower():
                continue
        filtered_flags.append(f)

    st.markdown(f"**Found {len(filtered_flags)} priority candidates matching criteria.**")

    # Table of candidates
    table_data = []
    for f in filtered_flags:
        p = f.protein
        table_data.append({
            "Accession": p.accession,
            "Gene": p.gene_name or "—",
            "Protein Name": p.protein_name,
            "Priority": f.review_priority,
            "Contradiction Score": f"{f.contradiction_score:.3f}",
            "Primary Signal": f.contradictory_signals.split(";")[0],
            "Flag Reason": f.flag_reason[:120] + "..." if len(f.flag_reason) > 120 else f.flag_reason,
        })

    st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

    st.markdown("---")

    # Side-by-Side Reference Comparison Tool
    st.subheader("Side-by-Side Reference Comparison")
    st.markdown("Select a candidate kinase to inspect side-by-side with its closest characterized reference kinase.")

    candidate_accessions = [f.protein.accession for f in filtered_flags]
    if candidate_accessions:
        selected_cand_acc = st.selectbox("Choose Candidate Kinase", candidate_accessions)
        chosen_flag = next((f for f in filtered_flags if f.protein.accession == selected_cand_acc), None)

        if chosen_flag:
            cand_prot = chosen_flag.protein

            # Find matching reference from model results
            ref_acc = None
            sim_score = 0.0
            for r in cand_prot.model_results:
                if r.method_name == "sequence_similarity" and r.reference_protein_accession:
                    ref_acc = r.reference_protein_accession
                    sim_score = r.similarity_score or 0.0
                    break

            with get_db_session() as session:
                ref_prot = session.query(Protein).options(
                    joinedload(Protein.sequence_features),
                    joinedload(Protein.annotations),
                ).filter(Protein.accession == ref_acc).first() if ref_acc else None

            col_query, col_ref = st.columns([1, 1])

            with col_query:
                st.markdown(f"""
                <div style="background-color: #FEF2F2; color: #1E293B; border: 1px solid #FCA5A5; border-radius: 6px; padding: 14px;">
                    <h4 style="margin: 0; color: #991B1B;">Candidate: {cand_prot.accession} ({cand_prot.gene_name or '—'})</h4>
                    <p style="margin: 4px 0; font-size: 13px; color: #64748B;">{cand_prot.protein_name}</p>
                    <p style="margin: 4px 0 0 0; color: #1E293B;"><b>Review Priority:</b> {chosen_flag.review_priority} (Score: {chosen_flag.contradiction_score:.3f})</p>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("**Motif Status:**")
                for m in cand_prot.sequence_features:
                    st.write(f"- `{m.feature_name}`: **{m.detected_status.upper()}** ({m.detected_sequence or 'Absent'}) at {m.start_position or 'N/A'}")

                st.markdown("**Functional Annotation:**")
                cand_ann = cand_prot.annotations[0].functional_label if cand_prot.annotations else "None"
                st.write(f"_{cand_ann}_")

            with col_ref:
                if ref_prot:
                    st.markdown(f"""
                    <div style="background-color: #F0FDF4; color: #1E293B; border: 1px solid #86EFAC; border-radius: 6px; padding: 14px;">
                        <h4 style="margin: 0; color: #166534;">Reference: {ref_prot.accession} ({ref_prot.gene_name or '—'})</h4>
                        <p style="margin: 4px 0; font-size: 13px; color: #64748B;">{ref_prot.protein_name}</p>
                        <p style="margin: 4px 0 0 0; color: #1E293B;"><b>Sequence Identity:</b> {sim_score*100:.1f}%</p>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown("**Motif Status:**")
                    for m in ref_prot.sequence_features:
                        st.write(f"- `{m.feature_name}`: **{m.detected_status.upper()}** ({m.detected_sequence or 'Absent'}) at {m.start_position or 'N/A'}")

                    st.markdown("**Functional Annotation:**")
                    ref_ann = ref_prot.annotations[0].functional_label if ref_prot.annotations else "None"
                    st.write(f"_{ref_ann}_")
                else:
                    st.info("No direct reference record loaded for comparison.")

            st.markdown("<br/>", unsafe_allow_html=True)
            if st.button("Open Full Protein Detail"):
                st.session_state["selected_protein_accession"] = cand_prot.accession
                st.session_state["current_page"] = "Protein Detail"
                st.rerun()
