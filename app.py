"""
The Annotation Contradiction Atlas: An Evidence-Aware Database for
Detecting Potentially Misannotated Protein Kinase Functions.

Main Streamlit Application Entrypoint.
"""
from __future__ import annotations

import streamlit as st

# Configure wide page layout
st.set_page_config(
    page_title="Annotation Contradiction Atlas",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

from config import PROJECT_TITLE, PROJECT_SUBTITLE, DEFAULT_ESM_MODEL
from ui.styles import CUSTOM_CSS
from ui.dashboard import render_dashboard
from ui.protein_explorer import render_protein_explorer
from ui.protein_detail import render_protein_detail
from ui.contradiction_explorer import render_contradiction_explorer
from ui.evaluation import render_evaluation
from ui.data_management import render_data_management
from ui.methods import render_methods

# Inject custom CSS styles
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Initialize Session State
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Overview Dashboard"
if "selected_protein_accession" not in st.session_state:
    st.session_state["selected_protein_accession"] = "P00533"

# Sidebar Navigation
with st.sidebar:
    st.markdown(f"## 🧬 Contradiction Atlas")
    st.caption("Human Kinome Evidence-Aware Database")
    st.markdown("---")

    PAGES = [
        "Overview Dashboard",
        "Protein Explorer",
        "Protein Detail",
        "Contradiction Explorer",
        "Analysis & Evaluation",
        "Data Management",
        "Methods & Documentation",
    ]

    selected_page = st.radio(
        "Navigation",
        PAGES,
        index=PAGES.index(st.session_state["current_page"]) if st.session_state["current_page"] in PAGES else 0,
    )
    st.session_state["current_page"] = selected_page

    st.markdown("---")
    st.markdown("### Model & System Status")
    st.markdown(f"""
    - **Language Model:** `ESM-2 (8M)`
    - **Taxonomy:** *Homo sapiens* (9606)
    - **Database:** Local SQLite ORM
    - **Status:** Operational
    """)

    st.markdown("---")
    st.caption("The Annotation Contradiction Atlas")

# Page Routing
page = st.session_state["current_page"]
if page == "Overview Dashboard":
    render_dashboard()
elif page == "Protein Explorer":
    render_protein_explorer()
elif page == "Protein Detail":
    render_protein_detail()
elif page == "Contradiction Explorer":
    render_contradiction_explorer()
elif page == "Analysis & Evaluation":
    render_evaluation()
elif page == "Data Management":
    render_data_management()
elif page == "Methods & Documentation":
    render_methods()
