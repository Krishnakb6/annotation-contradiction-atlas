"""
Page 4: Contradiction Explorer.
Investigates flagged kinase review candidates, signal breakdowns,
and provides side-by-side comparative inspection against closest reference kinases.
Clearly distinguishes suspected annotation conflicts from natural biological exceptions.
"""
from __future__ import annotations

import streamlit as st
import plotly.express as px
import pandas as pd
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import joinedload
from sqlalchemy import desc

from database.connection import get_db_session
from database.models import Protein, ReviewFlag, SequenceFeature, ModelResult, FunctionAnnotation
from services.contradiction_scoring import (
    is_biological_exception,
    filter_suspected_conflicts,
    get_biological_exceptions,
    load_benchmark_exceptions,
)
from ui.styles import render_priority_badge, render_exception_badge


def get_explorer_candidates() -> Tuple[List[Any], List[Dict[str, Any]]]:
    """
    Retrieves and separates flagged candidates into:
    1. Suspected annotation conflicts (DB review flags with HIGH/MODERATE priority, excluding biological exceptions).
    2. Natural biological exceptions (e.g. VRK3, ILK, and DB-flagged pseudokinases).
    """
    with get_db_session() as session:
        db_flags = session.query(ReviewFlag).options(
            joinedload(ReviewFlag.protein).joinedload(Protein.sequence_features),
            joinedload(ReviewFlag.protein).joinedload(Protein.annotations),
            joinedload(ReviewFlag.protein).joinedload(Protein.model_results),
        ).filter(ReviewFlag.review_priority.in_(["HIGH", "MODERATE"])).order_by(desc(ReviewFlag.contradiction_score)).all()

    # 1. Suspected annotation conflicts (biological exceptions excluded by default)
    suspected_conflicts = [f for f in db_flags if not is_biological_exception(f)]

    # 2. Biological exceptions from DB flags
    db_exceptions = [f for f in db_flags if is_biological_exception(f)]
    bio_exceptions: List[Dict[str, Any]] = []
    seen_accessions = set()

    for f in db_exceptions:
        p = f.protein
        seen_accessions.add(p.accession)
        bio_exceptions.append({
            "accession": p.accession,
            "gene_name": p.gene_name or "—",
            "protein_name": p.protein_name,
            "priority": f.review_priority,
            "contradiction_score": f.contradiction_score,
            "classification": "BIOLOGICAL_EXCEPTION (Pseudokinase)",
            "primary_signal": f.contradictory_signals.split(";")[0] if f.contradictory_signals else "Atypical kinase motif",
            "flag_reason": f.flag_reason,
            "motif_summary": f.contradictory_signals,
            "canonical_count": sum(1 for feat in p.sequence_features if feat.detected_status == "canonical"),
            "variant_count": sum(1 for feat in p.sequence_features if feat.detected_status == "variant"),
            "absent_count": sum(1 for feat in p.sequence_features if feat.detected_status == "absent"),
            "biological_caveat": f.limitations,
            "flag_obj": f,
            "protein_obj": p,
        })

    # 3. Benchmark biological exceptions (guarantees VRK3 and ILK are always accessible)
    benchmark_cases = load_benchmark_exceptions()
    for case in benchmark_cases:
        acc = case.get("accession")
        if acc not in seen_accessions:
            seen_accessions.add(acc)
            motifs = case.get("detected_motifs", {})
            bio_exceptions.append({
                "accession": acc,
                "gene_name": case.get("gene_name") or "—",
                "protein_name": case.get("assigned_annotation"),
                "priority": case.get("review_priority", "MODERATE"),
                "contradiction_score": case.get("contradiction_score", 0.0),
                "classification": case.get("classification", "BIOLOGICAL_EXCEPTION (Pseudokinase)"),
                "primary_signal": "Atypical pseudokinase motif(s)",
                "flag_reason": case.get("biological_caveat", ""),
                "motif_summary": motifs.get("summary", ""),
                "canonical_count": motifs.get("canonical", 0),
                "variant_count": motifs.get("variant", 0),
                "absent_count": motifs.get("absent", 0),
                "biological_caveat": case.get("biological_caveat", ""),
                "flag_obj": None,
                "protein_obj": None,
            })

    return suspected_conflicts, bio_exceptions


def render_contradiction_explorer():
    st.title("Annotation Contradiction Explorer")
    st.markdown(
        "Interactive investigation environment for potential annotation conflicts and atypical kinase variants. "
        "Natural biological exceptions (pseudokinases) are rigorously separated from suspected clerical/functional misannotations."
    )

    suspected_conflicts, bio_exceptions = get_explorer_candidates()

    if not suspected_conflicts and not bio_exceptions:
        st.info("No proteins currently flagged with HIGH or MODERATE review priority. Run computational analysis to generate flags.")
        return

    # Dedicated Tabs separating Suspected Conflicts and Biological Exceptions
    tab_conflicts, tab_exceptions = st.tabs([
        "⚠️ Suspected Annotation Conflicts",
        "🧬 Natural Biological Exceptions (Pseudokinases)",
    ])

    # =========================================================================
    # TAB 1: Ordinary Suspected Annotation Conflicts Queue
    # =========================================================================
    with tab_conflicts:
        st.markdown(
            "Ordinary review queue for proteins exhibiting computational discordance across catalytic motifs, "
            "language model embeddings, or sequence homology baselines. "
            "**Natural biological exceptions are excluded by default.**"
        )

        col_prio, col_signal, col_opt = st.columns([1, 1.5, 1.5])
        with col_prio:
            filter_priority = st.selectbox(
                "Filter by Priority",
                ["All Flagged (High + Moderate)", "HIGH only", "MODERATE only"],
                key="conflict_prio",
            )
        with col_signal:
            signal_filter = st.selectbox(
                "Filter by Contradictory Signal",
                [
                    "All Signals",
                    "Missing catalytic motif(s)",
                    "Variant motif sequence",
                    "ESM-2 embedding outlier",
                    "Purely computational / unreviewed provenance",
                ],
                key="conflict_sig",
            )
        with col_opt:
            st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
            include_exceptions_toggle = st.checkbox(
                "Include biological exceptions in this queue",
                value=False,
                help="When unchecked (default), biological exceptions like pseudokinases are separated into their own dedicated section.",
            )

        # Base candidate pool
        if include_exceptions_toggle:
            conflict_pool = suspected_conflicts + [e["flag_obj"] for e in bio_exceptions if e.get("flag_obj")]
        else:
            conflict_pool = filter_suspected_conflicts(suspected_conflicts)

        filtered_conflicts = []
        for f in conflict_pool:
            if filter_priority == "HIGH only" and f.review_priority != "HIGH":
                continue
            if filter_priority == "MODERATE only" and f.review_priority != "MODERATE":
                continue
            if signal_filter != "All Signals":
                if signal_filter.lower() not in (f.contradictory_signals or "").lower():
                    continue
            filtered_conflicts.append(f)

        st.markdown(f"**Found {len(filtered_conflicts)} suspected annotation conflict candidates matching criteria.**")

        if filtered_conflicts:
            table_data = []
            for f in filtered_conflicts:
                p = f.protein
                table_data.append({
                    "Accession": p.accession,
                    "Gene": p.gene_name or "—",
                    "Protein Name": p.protein_name,
                    "Priority": f.review_priority,
                    "Contradiction Score": f"{f.contradiction_score:.3f}",
                    "Primary Signal": f.contradictory_signals.split(";")[0] if f.contradictory_signals else "Unspecified",
                    "Flag Reason": f.flag_reason[:120] + "..." if len(f.flag_reason) > 120 else f.flag_reason,
                })
            st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("Side-by-Side Reference Comparison (Suspected Conflicts)")
            st.markdown("Select a candidate kinase to inspect side-by-side with its closest characterized reference kinase.")

            candidate_accessions = [f.protein.accession for f in filtered_conflicts]
            selected_cand_acc = st.selectbox("Choose Candidate Kinase", candidate_accessions, key="conflict_compare_sel")
            chosen_flag = next((f for f in filtered_conflicts if f.protein.accession == selected_cand_acc), None)

            if chosen_flag:
                cand_prot = chosen_flag.protein
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
                if st.button("Open Full Protein Detail", key="btn_open_conflict"):
                    st.session_state["selected_protein_accession"] = cand_prot.accession
                    st.session_state["current_page"] = "Protein Detail"
                    st.rerun()
        else:
            st.info("No suspected annotation conflicts match the selected filter criteria.")

    # =========================================================================
    # TAB 2: Separate Natural Biological Exceptions Section
    # =========================================================================
    with tab_exceptions:
        st.info(
            "🧬 **Natural Biological Exceptions (Pseudokinases):**  \n"
            "These proteins (such as VRK3 and ILK) possess non-canonical or variant catalytic motifs (such as altered catalytic loop "
            "or metal-binding motifs) but function legitimately in non-catalytic scaffolding, allosteric regulation, or pseudo-enzymatic roles.  \n\n"
            "**Key Scientific Principle:** Contradiction scores shown below are **diagnostic scores** measuring structural divergence "
            "from canonical active kinases. They **do NOT establish that an annotation is wrong**."
        )

        col_eprio, col_esearch = st.columns([1, 2])
        with col_eprio:
            filter_ex_priority = st.selectbox(
                "Filter Exceptions by Priority",
                ["All Priorities", "HIGH only", "MODERATE only"],
                key="ex_prio_filter",
            )
        with col_esearch:
            ex_search = st.text_input("Filter Exceptions by Gene/Accession", placeholder="e.g. VRK3, ILK, ALPK2", key="ex_search")

        filtered_exceptions = []
        for e in bio_exceptions:
            if filter_ex_priority == "HIGH only" and e["priority"] != "HIGH":
                continue
            if filter_ex_priority == "MODERATE only" and e["priority"] != "MODERATE":
                continue
            if ex_search:
                term = ex_search.strip().lower()
                if term not in e["accession"].lower() and term not in e["gene_name"].lower() and term not in e["protein_name"].lower():
                    continue
            filtered_exceptions.append(e)

        st.markdown(f"**Found {len(filtered_exceptions)} natural biological exceptions.**")

        if filtered_exceptions:
            ex_table_data = []
            for e in filtered_exceptions:
                ex_table_data.append({
                    "Accession": e["accession"],
                    "Gene": e["gene_name"],
                    "Protein Name / Annotation": e["protein_name"],
                    "Characterization Priority": f"{e['priority']} (Diagnostic)",
                    "Diagnostic Score": f"{e['contradiction_score']:.4f}",
                    "Primary Signal": e["primary_signal"],
                    "Motif Summary": e["motif_summary"][:100] + "..." if len(e["motif_summary"]) > 100 else e["motif_summary"],
                    "Biological Caveat": e["biological_caveat"][:120] + "..." if len(e["biological_caveat"]) > 120 else e["biological_caveat"],
                })
            st.dataframe(pd.DataFrame(ex_table_data), use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("Motif Explanations & Structural Characterization")
            st.markdown("Inspect specific motif deviations and scientific explanations for natural biological exceptions:")

            for e in filtered_exceptions:
                with st.expander(f"🧬 {e['gene_name']} ({e['accession']}) — Characterization Priority: {e['priority']} [Biological Exception]", expanded=(e['accession'] in ('Q9Y616', 'Q13418'))):
                    c1, c2 = st.columns([1, 1])
                    with c1:
                        st.markdown(f"**Assigned Annotation:** {e['protein_name']}")
                        st.markdown(f"**Classification:** `{e['classification']}`")
                        st.markdown(f"**Diagnostic Contradiction Score:** `{e['contradiction_score']:.4f}` *(Diagnostic score; does NOT establish an annotation error)*")
                        st.caption("ℹ️ *Note: Priority reflects degree of structural divergence requiring characterization, not the probability that this biological exception is misannotated.*")
                    with c2:
                        st.markdown(f"**Motif Summary:** {e['motif_summary']}")
                        st.markdown(f"- Canonical Motifs: `{e['canonical_count']}` &bull; Variant Motifs: `{e['variant_count']}` &bull; Absent Motifs: `{e['absent_count']}`")
                    st.warning(f"**Scientific Caveat:** {e['biological_caveat']}")

            st.markdown("---")
            st.subheader("Side-by-Side Reference Comparison (Biological Exceptions)")
            st.markdown("Compare a biological exception with its nearest canonical reference kinase to examine motif divergence:")

            ex_accessions = [e["accession"] for e in filtered_exceptions]
            selected_ex_acc = st.selectbox("Choose Biological Exception", ex_accessions, key="ex_compare_sel")
            chosen_ex = next((e for e in filtered_exceptions if e["accession"] == selected_ex_acc), None)

            if chosen_ex:
                # Resolve DB protein if possible
                with get_db_session() as session:
                    db_prot = session.query(Protein).options(
                        joinedload(Protein.sequence_features),
                        joinedload(Protein.annotations),
                        joinedload(Protein.model_results),
                    ).filter(Protein.accession == chosen_ex["accession"]).first()

                    # Fallback by gene name if accession differed between UniProt versions
                    if not db_prot and chosen_ex["gene_name"] != "—":
                        db_prot = session.query(Protein).options(
                            joinedload(Protein.sequence_features),
                            joinedload(Protein.annotations),
                            joinedload(Protein.model_results),
                        ).filter(Protein.gene_name == chosen_ex["gene_name"]).first()

                    ref_acc = None
                    sim_score = 0.0
                    if db_prot and db_prot.model_results:
                        for r in db_prot.model_results:
                            if r.method_name == "sequence_similarity" and r.reference_protein_accession:
                                ref_acc = r.reference_protein_accession
                                sim_score = r.similarity_score or 0.0
                                break

                    ref_prot = session.query(Protein).options(
                        joinedload(Protein.sequence_features),
                        joinedload(Protein.annotations),
                    ).filter(Protein.accession == ref_acc).first() if ref_acc else None

                col_query, col_ref = st.columns([1, 1])
                with col_query:
                    st.markdown(f"""
                    <div style="background-color: #EFF6FF; color: #1E293B; border: 1px solid #93C5FD; border-radius: 6px; padding: 14px;">
                        <h4 style="margin: 0; color: #1E40AF;">Biological Exception: {chosen_ex['accession']} ({chosen_ex['gene_name']})</h4>
                        <p style="margin: 4px 0; font-size: 13px; color: #64748B;">{chosen_ex['protein_name']}</p>
                        <p style="margin: 4px 0 0 0; color: #1E293B;"><b>Characterization Priority:</b> {chosen_ex['priority']} (Diagnostic Score: {chosen_ex['contradiction_score']:.4f})</p>
                        <p style="margin: 2px 0 0 0; font-size: 12px; color: #2563EB;">Diagnostic divergence metric — does NOT establish an annotation error.</p>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown("**Motif Status:**")
                    if db_prot and db_prot.sequence_features:
                        for m in db_prot.sequence_features:
                            st.write(f"- `{m.feature_name}`: **{m.detected_status.upper()}** ({m.detected_sequence or 'Absent'}) at {m.start_position or 'N/A'}")
                    else:
                        st.write(f"- {chosen_ex['motif_summary']}")

                    st.markdown("**Assigned Biological Role:**")
                    st.write(f"_{chosen_ex['protein_name']}_")

                with col_ref:
                    if ref_prot:
                        st.markdown(f"""
                        <div style="background-color: #F0FDF4; color: #1E293B; border: 1px solid #86EFAC; border-radius: 6px; padding: 14px;">
                            <h4 style="margin: 0; color: #166534;">Reference Kinase: {ref_prot.accession} ({ref_prot.gene_name or '—'})</h4>
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
                        st.info("Direct canonical reference comparison panel: Canonical active kinases maintain intact VAIK, HRD, and DFG triads.")

                st.markdown("<br/>", unsafe_allow_html=True)
                if db_prot:
                    if st.button("Open Full Protein Detail", key="btn_open_ex"):
                        st.session_state["selected_protein_accession"] = db_prot.accession
                        st.session_state["current_page"] = "Protein Detail"
                        st.rerun()
        else:
            st.info("No natural biological exceptions match the selected filter criteria.")
