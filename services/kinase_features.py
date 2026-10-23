"""
Method D: Kinase Biological Feature Analysis.
Inspects conserved kinase catalytic motifs (VAIK, HRD, DFG), checks spatial ordering,
distinguishes pseudokinase signatures from sequence anomalies, and assigns feature integrity scores.
"""
from __future__ import annotations

import re
import logging
from typing import Dict, Any, List, Optional, Tuple

from config import KINASE_MOTIFS

logger = logging.getLogger("contradiction_atlas.features")

# Canonical & variant regex patterns
PATTERNS = {
    "VAIK_CANONICAL": re.compile(r"[LIVMAFY][AVILMF][IVATC][K]"),
    "VAIK_VARIANT": re.compile(r"[LIVMAFY][AVILMF][IVATC][RQNAGS]"),
    "HRD_CANONICAL": re.compile(r"[HYF][RKN][D]"),
    "HRD_VARIANT": re.compile(r"[HYF][A-Z][SANG]|(?:[HYF][RKN][A-CE-Z])"),
    "DFG_CANONICAL": re.compile(r"[D][FYSW][GSA]"),
    "DFG_VARIANT": re.compile(r"[NEQS][FYSW][GSA]|(?:[D][FYSW][A-FH-RT-Z])"),
}


class KinaseFeatureAnalyzer:
    """
    Evaluates presence, order, and integrity of core catalytic kinase motifs.
    """

    def analyze_sequence(self, sequence: str) -> Dict[str, Any]:
        """
        Scans sequence for VAIK, HRD, and DFG motifs with spatial order validation.
        """
        if not sequence:
            return {
                "motifs": [],
                "canonical_count": 0,
                "variant_count": 0,
                "absent_count": 3,
                "order_valid": False,
                "integrity_score": 0.0,
                "anomaly_score": 1.0,
                "summary": "Empty sequence; features cannot be evaluated.",
            }

        seq_upper = sequence.upper()
        detected_motifs: List[Dict[str, Any]] = []

        # 1. Search VAIK
        vaik_match = PATTERNS["VAIK_CANONICAL"].search(seq_upper)
        vaik_status = "absent"
        vaik_pos = None
        vaik_seq = None

        if vaik_match:
            vaik_status = "canonical"
            vaik_pos = (vaik_match.start() + 1, vaik_match.end())
            vaik_seq = vaik_match.group(0)
        else:
            vaik_var = PATTERNS["VAIK_VARIANT"].search(seq_upper)
            if vaik_var:
                vaik_status = "variant"
                vaik_pos = (vaik_var.start() + 1, vaik_var.end())
                vaik_seq = vaik_var.group(0)

        detected_motifs.append({
            "feature_name": "VAIK",
            "start_position": vaik_pos[0] if vaik_pos else None,
            "end_position": vaik_pos[1] if vaik_pos else None,
            "detected_sequence": vaik_seq,
            "detected_status": vaik_status,
            "detection_method": "regex_heuristic",
            "expected_context": "Subdomain II: β3-strand ATP-phosphate orienting motif",
            "evidence_or_limitation": (
                "Canonical VAIK present." if vaik_status == "canonical"
                else "Variant K->R detected." if vaik_status == "variant"
                else "VAIK absent; may indicate divergent ATP-binding or pseudokinase status."
            ),
        })

        # 2. Search HRD
        # Look preferentially after VAIK if VAIK was found
        search_start_hrd = (vaik_pos[1] if vaik_pos else 0)
        hrd_match = PATTERNS["HRD_CANONICAL"].search(seq_upper, pos=search_start_hrd)
        if not hrd_match and search_start_hrd > 0:
            # Fallback search entire sequence
            hrd_match = PATTERNS["HRD_CANONICAL"].search(seq_upper)

        hrd_status = "absent"
        hrd_pos = None
        hrd_seq = None

        if hrd_match:
            hrd_status = "canonical"
            hrd_pos = (hrd_match.start() + 1, hrd_match.end())
            hrd_seq = hrd_match.group(0)
        else:
            hrd_var = PATTERNS["HRD_VARIANT"].search(seq_upper, pos=search_start_hrd) or PATTERNS["HRD_VARIANT"].search(seq_upper)
            if hrd_var:
                hrd_status = "variant"
                hrd_pos = (hrd_var.start() + 1, hrd_var.end())
                hrd_seq = hrd_var.group(0)

        detected_motifs.append({
            "feature_name": "HRD",
            "start_position": hrd_pos[0] if hrd_pos else None,
            "end_position": hrd_pos[1] if hrd_pos else None,
            "detected_sequence": hrd_seq,
            "detected_status": hrd_status,
            "detection_method": "regex_heuristic",
            "expected_context": "Subdomain VIB: Catalytic loop base (Asp accepts proton from substrate -OH)",
            "evidence_or_limitation": (
                "Canonical catalytic HRD motif present." if hrd_status == "canonical"
                else f"Variant HRD '{hrd_seq}' detected (typical of pseudokinases like VRK3 or atypical kinases)." if hrd_status == "variant"
                else "HRD motif absent; indicates severe catalytic disruption or non-canonical transfer."
            ),
        })

        # 3. Search DFG
        # Look preferentially after HRD
        search_start_dfg = (hrd_pos[1] if hrd_pos else search_start_hrd)
        dfg_match = PATTERNS["DFG_CANONICAL"].search(seq_upper, pos=search_start_dfg)
        if not dfg_match and search_start_dfg > 0:
            dfg_match = PATTERNS["DFG_CANONICAL"].search(seq_upper)

        dfg_status = "absent"
        dfg_pos = None
        dfg_seq = None

        if dfg_match:
            dfg_status = "canonical"
            dfg_pos = (dfg_match.start() + 1, dfg_match.end())
            dfg_seq = dfg_match.group(0)
        else:
            dfg_var = PATTERNS["DFG_VARIANT"].search(seq_upper, pos=search_start_dfg) or PATTERNS["DFG_VARIANT"].search(seq_upper)
            if dfg_var:
                dfg_status = "variant"
                dfg_pos = (dfg_var.start() + 1, dfg_var.end())
                dfg_seq = dfg_var.group(0)

        detected_motifs.append({
            "feature_name": "DFG",
            "start_position": dfg_pos[0] if dfg_pos else None,
            "end_position": dfg_pos[1] if dfg_pos else None,
            "detected_sequence": dfg_seq,
            "detected_status": dfg_status,
            "detection_method": "regex_heuristic",
            "expected_context": "Subdomain VII: Activation segment start (Asp coordinates Mg2+ ion)",
            "evidence_or_limitation": (
                "Canonical DFG motif present." if dfg_status == "canonical"
                else f"Variant DFG '{dfg_seq}' detected (observed in non-canonical kinases like ILK)." if dfg_status == "variant"
                else "DFG motif absent; metal-binding coordination likely lost."
            ),
        })

        # Spatial order validation (VAIK < HRD < DFG)
        order_valid = False
        if vaik_pos and hrd_pos and dfg_pos:
            order_valid = vaik_pos[0] < hrd_pos[0] < dfg_pos[0]
            # Spatial distance check: HRD is typically 50-250 residues after VAIK; DFG is 10-60 after HRD
            hrd_dist = hrd_pos[0] - vaik_pos[0]
            dfg_dist = dfg_pos[0] - hrd_pos[0]
            if not (40 <= hrd_dist <= 300 and 10 <= dfg_dist <= 80):
                order_valid = False  # Out of reasonable kinase domain bounds

        canonical_count = sum(1 for m in detected_motifs if m["detected_status"] == "canonical")
        variant_count = sum(1 for m in detected_motifs if m["detected_status"] == "variant")
        absent_count = sum(1 for m in detected_motifs if m["detected_status"] == "absent")

        # Compute integrity score (0.0 to 1.0)
        # Canonical = 1.0, Variant = 0.5, Absent = 0.0
        score = (canonical_count * 1.0 + variant_count * 0.45) / 3.0
        if not order_valid and canonical_count == 3:
            score *= 0.85  # Slight penalty if spatial domain order is abnormal

        integrity_score = round(float(score), 4)
        anomaly_score = round(float(1.0 - integrity_score), 4)

        summary_parts = []
        if canonical_count == 3 and order_valid:
            summary_parts.append("All canonical catalytic motifs (VAIK, HRD, DFG) verified in standard domain order.")
        else:
            if absent_count > 0:
                missing = [m["feature_name"] for m in detected_motifs if m["detected_status"] == "absent"]
                summary_parts.append(f"Missing core motif(s): {', '.join(missing)}.")
            if variant_count > 0:
                variants = [f"{m['feature_name']} ({m['detected_sequence']})" for m in detected_motifs if m["detected_status"] == "variant"]
                summary_parts.append(f"Atypical motif variant(s): {', '.join(variants)}.")
            if not order_valid and (canonical_count + variant_count) == 3:
                summary_parts.append("Motif spacing or relative order deviates from canonical kinase domain organization.")

        return {
            "motifs": detected_motifs,
            "canonical_count": canonical_count,
            "variant_count": variant_count,
            "absent_count": absent_count,
            "order_valid": order_valid,
            "integrity_score": integrity_score,
            "anomaly_score": anomaly_score,
            "summary": " ".join(summary_parts),
        }
