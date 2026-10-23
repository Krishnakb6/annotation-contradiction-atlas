"""
Page 3: Protein Detail.
Provides deep-dive inspection of an individual kinase record, separating
directly retrieved biological facts from computed model predictions.
"""
from __future__ import annotations

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from sqlalchemy.orm import joinedload

from database.connection import get_db_session
from database.models import Protein, FunctionAnnotation, SequenceFeature, ReviewFlag, ModelResult, ProteinFamilyMembership
from ui.styles import render_priority_badge


def highlight_sequence(sequence: str, features: list) -> str:
    """Highlights motif positions within the sequence string with high-contrast scientific colors."""
    if not sequence:
        return ""
    # Sort motifs by start position descending to insert tags from back to front
    valid_motifs = [f for f in features if f.start_position and f.end_position and f.start_position <= len(sequence)]
    valid_motifs.sort(key=lambda x: x.start_position, reverse=True)

    seq_chars = list(sequence)
    for m in valid_motifs:
        start_idx = m.start_position - 1
        end_idx = min(m.end_position, len(sequence))
        is_canonical = m.detected_status == "canonical"
        bg_color = "#059669" if is_canonical else "#D97706"
        tag_title = f"{m.feature_name} ({m.detected_status.upper()}): pos {m.start_position}-{m.end_position}"
        style = (
            f"background-color: {bg_color} !important; "
            f"color: #FFFFFF !important; "
            f"font-weight: 800; "
            f"padding: 2px 6px; "
            f"border-radius: 4px; "
            f"display: inline-block; "
            f"margin: 0 1px; "
            f"box-shadow: 0 1px 2px rgba(0, 0, 0, 0.4);"
        )
        seq_chars[start_idx] = f"<span style='{style}' title='{tag_title}'>" + seq_chars[start_idx]
        seq_chars[end_idx - 1] = seq_chars[end_idx - 1] + "</span>"

    return "".join(seq_chars)


def render_protein_detail():
    accession = st.session_state.get("selected_protein_accession", "P00533")

    col_title, col_search = st.columns([3, 1])
    with col_title:
        st.title(f"Protein Record: {accession}")
    with col_search:
        new_acc = st.text_input("Look up another accession:", value=accession)
        if new_acc.strip().upper() != accession:
            st.session_state["selected_protein_accession"] = new_acc.strip().upper()
            st.rerun()

    with get_db_session() as session:
        protein = session.query(Protein).options(
            joinedload(Protein.annotations),
            joinedload(Protein.sequence_features),
            joinedload(Protein.review_flags),
            joinedload(Protein.model_results),
            joinedload(Protein.family_memberships).joinedload(ProteinFamilyMembership.family),
        ).filter(Protein.accession == accession).first()

    if not protein:
        st.error(f"Protein with accession '{accession}' was not found in the local database.")
        if st.button("Return to Protein Explorer"):
            st.session_state["current_page"] = "Protein Explorer"
            st.rerun()
        return

    # Header Card
    flag = protein.review_flags[0] if protein.review_flags else None
    priority = flag.review_priority if flag else "PENDING"
    score = flag.contradiction_score if flag else 0.0

    st.markdown(f"""
    <div style="background-color: #FFFFFF; color: #1E293B; border: 1px solid #E2E8F0; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h3 style="margin: 0; color: #1E293B;">{protein.protein_name}</h3>
                <p style="margin: 4px 0 0 0; color: #64748B; font-size: 15px;">
                    Gene: <b style="color: #0F172A;">{protein.gene_name or 'N/A'}</b> &bull; Organism: <i>{protein.organism}</i> &bull; Length: <b style="color: #0F172A;">{protein.sequence_length} aa</b>
                </p>
            </div>
            <div>
                {render_priority_badge(priority)}
            </div>
        </div>
        <div style="margin-top: 12px; font-size: 14px;">
            <a href="{protein.source_url}" target="_blank" style="color: #2563EB; text-decoration: none; font-weight: 500;">
                🔗 View official entry on UniProt ({protein.accession}) &rarr;
            </a>
            &nbsp;|&nbsp;
            <span style="color: #475569;">Status: <b style="color: #0F172A;">{'UniProtKB Reviewed (Swiss-Prot)' if protein.reviewed else 'Unreviewed (TrEMBL)'}</b></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Review Priority & Scientific Explanation Banner
    if flag:
        bg_col = "#FEF2F2" if priority == "HIGH" else "#FFFBEB" if priority == "MODERATE" else "#F0FDF4"
        border_col = "#FCA5A5" if priority == "HIGH" else "#FCD34D" if priority == "MODERATE" else "#86EFAC"

        st.markdown(f"""
        <div style="background-color: {bg_col}; color: #1E293B; border-left: 5px solid {border_col}; padding: 16px; border-radius: 4px; margin-bottom: 20px;">
            <h4 style="margin: 0 0 8px 0; color: #1E293B;">Evidence-Based Review Prioritization Summary</h4>
            <p style="margin: 0 0 8px 0; font-size: 15px; color: #334155; line-height: 1.5;">{flag.flag_reason}</p>
            <div style="font-size: 13px; color: #64748B;">
                <b>Contradictory Signals:</b> {flag.contradictory_signals}<br/>
                <b>Composite Contradiction Score:</b> {flag.contradiction_score:.4f} (Priority: {priority})
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("Scientific Caveats and Evidence Limitations", expanded=False):
            st.info(flag.limitations)

    # Radar Chart of Component Scores
    if flag:
        # Retrieve model results
        c_radar, c_summary = st.columns([1, 1.2])
        with c_radar:
            st.subheader("Component Anomaly Breakdown")
            # Extract scores from results or flag
            sim_score = 0.0
            emb_score = 0.0
            for r in protein.model_results:
                if r.method_name == "sequence_similarity":
                    sim_score = r.anomaly_score
                elif r.method_name == "esm2_anomaly":
                    emb_score = r.anomaly_score

            feat_score = 0.0
            if protein.sequence_features:
                canonical = sum(1 for f in protein.sequence_features if f.detected_status == "canonical")
                feat_score = (3 - canonical) / 3.0

            prov_score = 0.1 if protein.reviewed else 0.8

            df_radar = pd.DataFrame(dict(
                r=[emb_score, sim_score, feat_score, prov_score],
                theta=['ESM-2 Embedding Anomaly', 'Sequence Dissimilarity', 'Motif Disruption', 'Provenance Uncertainty']
            ))
            fig_radar = px.line_polar(df_radar, r='r', theta='theta', line_close=True, range_r=[0, 1])
            fig_radar.update_traces(fill='toself', fillcolor='rgba(239, 68, 68, 0.25)', line_color='#DC2626')
            fig_radar.update_layout(height=280, margin=dict(l=30, r=30, t=20, b=20))
            st.plotly_chart(fig_radar, use_container_width=True)

        with c_summary:
            st.subheader("Analytical Evidence Synthesis")
            st.markdown(f"""
            - **ESM-2 Language Model Manifold:** Anomaly score: `{emb_score:.3f}`.
            - **Sequence Similarity Baseline:** Anomaly score: `{sim_score:.3f}`.
            - **Catalytic Motif Integrity:** Anomaly score: `{feat_score:.3f}`.
            - **Provenance & Review Status:** Penalty score: `{prov_score:.3f}`.
            """)
            st.markdown(f"**Supporting Evidence:** {flag.supporting_evidence_summary}")

    st.markdown("---")

    # Detailed Tabs
    tab_seq, tab_ann, tab_ref, tab_fam = st.tabs([
        "🧬 Biological Sequence & Motifs",
        "📋 Functional Annotations & Evidence",
        "🔍 Reference Comparisons & Manifold Neighbors",
        "🏷️ Protein Families & Domains",
    ])

    with tab_seq:
        st.subheader("Conserved Kinase Catalytic Motifs")
        st.markdown(
            "Evaluation of essential catalytic triad elements: **VAIK** (subdomain II, ATP orientation), "
            "**HRD** (subdomain VIB, catalytic base), and **DFG** (subdomain VII, Mg2+ metal coordination)."
        )

        if protein.sequence_features:
            feat_rows = []
            for f in protein.sequence_features:
                feat_rows.append({
                    "Motif": f.feature_name,
                    "Detected Status": f.detected_status.upper(),
                    "Sequence": f.detected_sequence or "None",
                    "Positions": f"{f.start_position} - {f.end_position}" if f.start_position else "N/A",
                    "Biological Context": f.expected_context or "",
                    "Evidence Note": f.evidence_or_limitation or "",
                })
            st.dataframe(pd.DataFrame(feat_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No motif features computed yet.")

        st.subheader("Primary Amino Acid Sequence")
        st.markdown(
            """
            <div style="display: flex; gap: 16px; align-items: center; margin-bottom: 10px; font-size: 13px;">
                <span style="color: #64748B; font-weight: 500;">Detected Motifs:</span>
                <span style="background-color: #059669; color: #FFFFFF; font-weight: 700; padding: 2px 8px; border-radius: 4px;">Canonical Triad</span>
                <span style="background-color: #D97706; color: #FFFFFF; font-weight: 700; padding: 2px 8px; border-radius: 4px;">Atypical / Variant Motif</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        highlighted_html = highlight_sequence(protein.sequence, protein.sequence_features)
        st.markdown(f'<div class="sequence-box">{highlighted_html}</div>', unsafe_allow_html=True)

    with tab_ann:
        st.subheader("Assigned Functional Annotations & Provenance")
        st.markdown(
            "Traceable evidence codes (ECO), experimental assays, and external citations associated with this record."
        )

        if protein.annotations:
            ann_rows = []
            for a in protein.annotations:
                ann_rows.append({
                    "Functional Annotation": a.functional_label,
                    "Type": a.annotation_type.replace("_", " ").title(),
                    "Evidence Tier": a.evidence_category.replace("_", " ").title(),
                    "ECO Code": a.evidence_code or "Unspecified",
                    "Supporting Reference": a.supporting_reference or "None",
                })
            st.dataframe(pd.DataFrame(ann_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No functional annotations recorded for this protein.")

    with tab_ref:
        st.subheader("Nearest High-Confidence Kinase References")
        for res in protein.model_results:
            if res.method_name == "sequence_similarity":
                st.markdown(f"""
                **Sequence Similarity Baseline Match:**
                - Nearest Reference Accession: `{res.reference_protein_accession or 'N/A'}`
                - Sequence Identity: `{(res.similarity_score or 0)*100:.1f}%`
                - Functional Concordance: `{'Concordant' if not res.is_outlier else 'Discordant'}`
                - Detail: {res.result_explanation}
                """)
            elif res.method_name == "esm2_anomaly":
                st.markdown(f"""
                **ESM-2 Manifold Anomaly Metric:**
                - Manifold Outlier Status: `{'OUTLIER' if res.is_outlier else 'CONGRUENT'}`
                - Embedding Anomaly Score: `{res.anomaly_score:.4f}` (Threshold: `{res.threshold}`)
                - Detail: {res.result_explanation}
                """)

    with tab_fam:
        st.subheader("Family Classification & Cross-References")
        if protein.family_memberships:
            fam_rows = []
            for m in protein.family_memberships:
                fam = m.family
                fam_rows.append({
                    "Domain / Family Name": fam.family_name,
                    "Source Database": fam.classification_source,
                    "Identifier": fam.external_identifier or "N/A",
                    "Description": fam.description or "",
                })
            st.dataframe(pd.DataFrame(fam_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No cross-referenced protein families linked to this record.")
