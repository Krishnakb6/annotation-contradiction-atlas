"""
Unit tests for Streamlit interface components and visual renderers.
"""
from __future__ import annotations

import pytest
from database.models import SequenceFeature
from ui.styles import render_priority_badge, CUSTOM_CSS
from ui.protein_detail import highlight_sequence


def test_priority_badge_rendering():
    """Verify HTML badges for review priority statuses."""
    badge_high = render_priority_badge("HIGH")
    assert "badge-priority-high" in badge_high
    assert "HIGH REVIEW PRIORITY" in badge_high

    badge_mod = render_priority_badge("MODERATE")
    assert "badge-priority-moderate" in badge_mod
    assert "MODERATE REVIEW PRIORITY" in badge_mod

    badge_low = render_priority_badge("LOW")
    assert "badge-priority-low" in badge_low
    assert "LOW REVIEW PRIORITY" in badge_low

    badge_ex = render_priority_badge("HIGH", is_exception=True)
    assert "HIGH (EXCEPTION)" in badge_ex


def test_exception_badge_rendering():
    """Verify HTML badge for biological exceptions."""
    from ui.styles import render_exception_badge
    badge = render_exception_badge("BIOLOGICAL EXCEPTION (Pseudokinase)")
    assert "BIOLOGICAL EXCEPTION" in badge
    assert "#EFF6FF" in badge
    assert "#1D4ED8" in badge



def test_custom_css_high_contrast_properties():
    """Verify that CSS defines high contrast and explicit text colors for sequence viewers."""
    assert ".sequence-box" in CUSTOM_CSS
    assert "background-color: #0F172A" in CUSTOM_CSS
    assert "color: #F8FAFC" in CUSTOM_CSS


def test_highlight_sequence_empty():
    """Empty or None sequences should return an empty string safely."""
    assert highlight_sequence("", []) == ""
    assert highlight_sequence(None, []) == ""


def test_highlight_sequence_motifs():
    """Verify that sequence motifs are wrapped in high-contrast styled spans."""
    seq = "VAIKLMNP"
    feat = SequenceFeature(
        feature_name="VAIK",
        detected_status="canonical",
        start_position=1,
        end_position=4,
    )
    highlighted = highlight_sequence(seq, [feat])
    assert "<span style=" in highlighted
    assert "#059669" in highlighted  # Canonical emerald green
    assert "#FFFFFF" in highlighted  # White bold text
    assert "title='VAIK (CANONICAL): pos 1-4'" in highlighted
    assert "LMNP" in highlighted


def test_highlight_sequence_variant_motif():
    """Verify variant/atypical motifs use the warm amber badge."""
    seq = "HGNKLMNP"
    feat = SequenceFeature(
        feature_name="HRD",
        detected_status="variant",
        start_position=1,
        end_position=3,
    )
    highlighted = highlight_sequence(seq, [feat])
    assert "#D97706" in highlighted  # Variant amber
    assert "#FFFFFF" in highlighted


def test_streamlit_ui_modules_importable():
    """Verify all Streamlit UI view modules can be imported without errors."""
    import ui.dashboard as d
    import ui.protein_explorer as pe
    import ui.protein_detail as pd
    import ui.contradiction_explorer as ce
    import ui.evaluation as ev
    import ui.data_management as dm
    import ui.methods as m

    assert hasattr(d, "render_dashboard")
    assert hasattr(pe, "render_protein_explorer")
    assert hasattr(pd, "render_protein_detail")
    assert hasattr(ce, "render_contradiction_explorer")
    assert hasattr(ev, "render_evaluation")
    assert hasattr(dm, "render_data_management")
    assert hasattr(m, "render_methods")
