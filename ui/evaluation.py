"""
Page 5: Analysis and Evaluation.
Displays benchmark performance, confusion matrices, synthetic control results,
and comparative evaluations across detection methods.
"""
from __future__ import annotations

import json
from pathlib import Path
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from config import ARTIFACTS_DIR
from services.benchmark import BenchmarkService


def render_evaluation():
    st.title("Method Evaluation & Benchmark Performance")
    st.markdown(
        "Empirical assessment of detection methods against **controlled synthetic test cases** "
        "and **independently characterized biological references / pseudokinases**."
    )

    report_path = ARTIFACTS_DIR / "evaluation_report.json"
    report = None
    if report_path.exists():
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                report = json.load(f)
        except Exception as e:
            st.error(f"Error reading evaluation report: {e}")

    # Top Control Bar
    col_status, col_btn = st.columns([3, 1])
    with col_status:
        if report:
            st.success(f"Loaded benchmark report: **{report.get('total_benchmark_cases', 0)} total evaluation cases** ({report.get('synthetic_cases_count', 0)} synthetic, {report.get('natural_cases_count', 0)} natural references).")
        else:
            st.warning("Benchmark evaluation has not been executed yet. Click 'Run Benchmark Evaluation' below to run reproducible assessment.")

    with col_btn:
        st.markdown("<div style='padding-top: 4px;'></div>", unsafe_allow_html=True)
        if st.button("Run Benchmark Evaluation", type="primary"):
            with st.spinner("Generating controlled synthetic cases and evaluating detection methods..."):
                import subprocess
                res = subprocess.run(["python", "scripts/run_evaluation.py", "--num-synthetic", "32"], capture_output=True, text=True)
                st.success("Evaluation complete!")
                st.rerun()

    if not report:
        st.info(
            "The benchmark evaluation requires running controlled test cases through all 4 analytical pipelines. "
            "Please click the button above to execute the evaluation suite."
        )
        return

    st.markdown("---")

    # Methods Comparison Table
    st.subheader("Performance Comparison Across Analytical Methods")
    methods_comp = report.get("methods_comparison", {})
    if methods_comp:
        comp_rows = []
        for m_key, m_val in methods_comp.items():
            name_clean = m_key.replace("_", " ").title()
            comp_rows.append({
                "Method": name_clean,
                "Precision": f"{m_val['precision']:.3f}",
                "Recall": f"{m_val['recall']:.3f}",
                "F1-Score": f"{m_val['f1_score']:.3f}",
                "Specificity": f"{m_val['specificity']:.3f}",
                "Accuracy": f"{m_val['accuracy']:.3f}",
                "True Positives (TP)": m_val["true_positives"],
                "False Positives (FP)": m_val["false_positives"],
                "True Negatives (TN)": m_val["true_negatives"],
                "False Negatives (FN)": m_val["false_negatives"],
            })
        df_comp = pd.DataFrame(comp_rows)
        st.dataframe(df_comp, use_container_width=True, hide_index=True)

        # Plotly Bar Chart Comparison
        df_plot = []
        for m_key, m_val in methods_comp.items():
            name_clean = m_key.replace("_", " ").title()
            df_plot.append({"Method": name_clean, "Metric": "Precision", "Score": m_val["precision"]})
            df_plot.append({"Method": name_clean, "Metric": "Recall", "Score": m_val["recall"]})
            df_plot.append({"Method": name_clean, "Metric": "F1-Score", "Score": m_val["f1_score"]})

        fig_bar = px.bar(
            pd.DataFrame(df_plot),
            x="Method",
            y="Score",
            color="Metric",
            barmode="group",
            range_y=[0, 1.1],
            color_discrete_sequence=["#3B82F6", "#10B981", "#EF4444"],
        )
        fig_bar.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # Confusion Matrix & Subsets
    col_cm, col_subsets = st.columns([1, 1])

    with col_cm:
        st.subheader("Ensemble Confusion Matrix")
        ens = methods_comp.get("evidence_aware_ensemble", {})
        if ens:
            cm_z = [
                [ens["true_negatives"], ens["false_positives"]],
                [ens["false_negatives"], ens["true_positives"]],
            ]
            fig_cm = px.imshow(
                cm_z,
                labels=dict(x="Predicted Class", y="Actual Ground Truth", color="Cases"),
                x=["Congruent", "Inconsistent / Contradiction"],
                y=["Congruent", "Inconsistent / Contradiction"],
                text_auto=True,
                color_continuous_scale="Blues",
            )
            fig_cm.update_layout(height=320, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_cm, use_container_width=True)

    with col_subsets:
        st.subheader("Synthetic Controls vs. Natural Cases")
        st.markdown(
            "> [!NOTE]\n"
            "> In accordance with scientific safeguards, synthetic perturbation performance "
            "is tracked strictly separately from natural biological reference cases."
        )

        synth_perf = report.get("synthetic_subset_performance")
        nat_perf = report.get("natural_subset_performance")

        if synth_perf:
            st.markdown(f"""
            **Synthetic Controlled Perturbations ({report.get('synthetic_cases_count', 0)} cases):**
            - **Precision:** `{synth_perf['precision']:.3f}` &bull; **Recall:** `{synth_perf['recall']:.3f}`
            - **F1-Score:** `{synth_perf['f1_score']:.3f}` &bull; **Accuracy:** `{synth_perf['accuracy']:.3f}`
            """)

        if nat_perf:
            st.markdown(f"""
            **Natural Reference Kinases & Pseudokinases ({report.get('natural_cases_count', 0)} cases):**
            - **Precision:** `{nat_perf['precision']:.3f}` &bull; **Recall:** `{nat_perf['recall']:.3f}`
            - **F1-Score:** `{nat_perf['f1_score']:.3f}` &bull; **Accuracy:** `{nat_perf['accuracy']:.3f}`
            """)

    st.markdown("---")

    # Scientific Limitations
    st.subheader("Scientific Safeguards & Limitations")
    limits = report.get("scientific_limitations", [])
    for lim in limits:
        st.markdown(f"- {lim}")
