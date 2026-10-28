"""
Scientific design system, CSS styles, and visual components for Streamlit.
Focuses on readability, restrained scientific palette, and clear evidence status indicators.
"""
from __future__ import annotations

CUSTOM_CSS = """
<style>
/* Main layout and typography */
.main {
    background-color: #F8FAFC;
    color: #0F172A;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

/* Metric card styling */
.metric-card {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 16px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    margin-bottom: 12px;
}
.metric-value {
    font-size: 26px;
    font-weight: 700;
    color: #1E293B;
    line-height: 1.2;
}
.metric-label {
    font-size: 13px;
    font-weight: 500;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 4px;
}

/* Priority status pills */
.badge-priority-high {
    background-color: #FEE2E2;
    color: #991B1B;
    border: 1px solid #FCA5A5;
    padding: 4px 10px;
    border-radius: 9999px;
    font-weight: 600;
    font-size: 12px;
    display: inline-block;
}
.badge-priority-moderate {
    background-color: #FEF3C7;
    color: #92400E;
    border: 1px solid #FCD34D;
    padding: 4px 10px;
    border-radius: 9999px;
    font-weight: 600;
    font-size: 12px;
    display: inline-block;
}
.badge-priority-low {
    background-color: #DCFCE7;
    color: #166534;
    border: 1px solid #86EFAC;
    padding: 4px 10px;
    border-radius: 9999px;
    font-weight: 600;
    font-size: 12px;
    display: inline-block;
}

/* Section info banners */
.scientific-callout {
    background-color: #F1F5F9;
    border-left: 4px solid #3B82F6;
    padding: 12px 16px;
    border-radius: 0 6px 6px 0;
    font-size: 14px;
    color: #334155;
    margin-bottom: 16px;
}

/* Sequence highlight block - High-contrast scientific monospace */
.sequence-box {
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, "Courier New", monospace !important;
    background-color: #0F172A !important;
    color: #F8FAFC !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    padding: 16px !important;
    font-size: 13px !important;
    line-height: 1.7 !important;
    letter-spacing: 0.06em !important;
    word-break: break-all !important;
    max-height: 280px !important;
    overflow-y: auto !important;
    box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.4) !important;
}
</style>
"""


def render_priority_badge(priority: str, is_exception: bool = False) -> str:
    """Returns HTML badge for review priority or exception characterization."""
    p_upper = (priority or "LOW").upper()
    if is_exception:
        return f'<span class="badge-priority-moderate" style="background-color: #EFF6FF; color: #1D4ED8; border: 1px solid #93C5FD; font-weight: 600;">{p_upper} (EXCEPTION)</span>'
    if p_upper == "HIGH":
        return '<span class="badge-priority-high">HIGH REVIEW PRIORITY</span>'
    elif p_upper == "MODERATE":
        return '<span class="badge-priority-moderate">MODERATE REVIEW PRIORITY</span>'
    else:
        return '<span class="badge-priority-low">LOW REVIEW PRIORITY</span>'


def render_exception_badge(classification: str = "BIOLOGICAL EXCEPTION") -> str:
    """Returns HTML badge for biological exceptions / pseudokinases."""
    return f'<span class="badge-priority-moderate" style="background-color: #EFF6FF; color: #1D4ED8; border: 1px solid #93C5FD; font-weight: 600;">🧬 {classification}</span>'

