"""
Page 2: Protein Explorer.
Provides searchable, filterable, and paginated exploration of the human kinome database.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, desc, asc

from database.connection import get_db_session
from database.models import Protein, ReviewFlag
from services.reporting import ReportingService
from ui.styles import render_priority_badge


def render_protein_explorer():
    st.title("Human Kinome Protein Explorer")
    st.markdown(
        "Search and filter human protein kinase records by accession, gene symbol, review status, "
        "and evidence-based review priority."
    )

    # Search and Filter Controls in Expandable or Columns layout
    col_search, col_prio, col_rev = st.columns([2, 1, 1])

    with col_search:
        search_query = st.text_input("Search (Accession, Gene, or Name)", placeholder="e.g. EGFR, P00533, BRAF, AKT1")

    with col_prio:
        priority_options = ["All Priorities", "HIGH", "MODERATE", "LOW", "Not Analyzed"]
        selected_priority = st.selectbox("Review Priority", priority_options)

    with col_rev:
        reviewed_options = ["All Statuses", "Reviewed (Swiss-Prot)", "Unreviewed (TrEMBL)"]
        selected_reviewed = st.selectbox("Review Status", reviewed_options)

    col_sort, col_page_size, col_export = st.columns([1.5, 1, 1])
    with col_sort:
        sort_by = st.selectbox("Sort By", ["Contradiction Score (Highest)", "Accession (A-Z)", "Gene Name (A-Z)", "Sequence Length (Longest)"])
    with col_page_size:
        page_size = st.selectbox("Rows per page", [25, 50, 100], index=0)

    # Database query
    with get_db_session() as session:
        query = session.query(Protein).outerjoin(ReviewFlag)

        if search_query:
            term = f"%{search_query.strip()}%"
            query = query.filter(
                or_(
                    Protein.accession.ilike(term),
                    Protein.gene_name.ilike(term),
                    Protein.protein_name.ilike(term),
                )
            )

        if selected_priority != "All Priorities":
            if selected_priority == "Not Analyzed":
                query = query.filter(ReviewFlag.id == None)
            else:
                query = query.filter(ReviewFlag.review_priority == selected_priority)

        if selected_reviewed == "Reviewed (Swiss-Prot)":
            query = query.filter(Protein.reviewed == True)
        elif selected_reviewed == "Unreviewed (TrEMBL)":
            query = query.filter(Protein.reviewed == False)

        # Sorting
        if sort_by == "Contradiction Score (Highest)":
            query = query.order_by(desc(ReviewFlag.contradiction_score).nullslast())
        elif sort_by == "Gene Name (A-Z)":
            query = query.order_by(asc(Protein.gene_name).nullslast())
        elif sort_by == "Sequence Length (Longest)":
            query = query.order_by(desc(Protein.sequence_length))
        else:
            query = query.order_by(asc(Protein.accession))

        total_matching = query.count()

        # Pagination
        total_pages = max(1, (total_matching + page_size - 1) // page_size)
        col_p1, col_p2 = st.columns([1, 3])
        with col_p1:
            page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)
        with col_p2:
            st.markdown(f"<div style='padding-top: 28px; color: #64748B;'>Showing page <b>{page}</b> of <b>{total_pages}</b> ({total_matching:,} matching proteins)</div>", unsafe_allow_html=True)

        offset = (page - 1) * page_size
        results = query.options(joinedload(Protein.review_flags)).slice(offset, offset + page_size).all()

        # CSV Export button
        with col_export:
            st.markdown("<div style='padding-top: 24px;'></div>", unsafe_allow_html=True)
            if total_matching > 0:
                all_matching = query.options(joinedload(Protein.review_flags)).limit(500).all()
                csv_data = ReportingService.export_proteins_to_csv(all_matching)
                st.download_button(
                    label="Export CSV",
                    data=csv_data,
                    file_name="kinome_proteins_atlas.csv",
                    mime="text/csv",
                )

        if not results:
            st.info("No matching proteins found for the specified search criteria.")
            return

        # Prepare Table Data
        table_rows = []
        for p in results:
            flag = p.review_flags[0] if p.review_flags else None
            prio = flag.review_priority if flag else "PENDING"
            score = f"{flag.contradiction_score:.2f}" if flag else "N/A"
            table_rows.append({
                "Accession": p.accession,
                "Gene": p.gene_name or "—",
                "Protein Name": p.protein_name,
                "Length (aa)": p.sequence_length,
                "Status": "Reviewed" if p.reviewed else "Unreviewed",
                "Priority": prio,
                "Score": score,
            })

        df_display = pd.DataFrame(table_rows)

        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("### Inspect a Protein")
        accession_options = [r["Accession"] for r in table_rows]
        c_sel, c_btn = st.columns([3, 1])
        with c_sel:
            selected_acc = st.selectbox("Select accession to view full analysis details", accession_options)
        with c_btn:
            st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
            if st.button("Open Protein Detail", type="primary"):
                st.session_state["selected_protein_accession"] = selected_acc
                st.session_state["current_page"] = "Protein Detail"
                st.rerun()
