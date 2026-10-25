# Scientific Benchmark Audit & Baseline Evaluation Report

**Project:** The Annotation Contradiction Atlas: An Evidence-Aware Database for Detecting Potentially Misannotated Protein Kinase Functions  
**Audit Date:** 2026-10-25  
**Audit Purpose:** Comprehensive scientific and methodology audit of existing benchmark generation, evaluation metrics, anomaly detection logic, and task-specific evaluation design.

---

## 1. Executive Summary of Audit Findings

| Audit Dimension | Original Baseline Status | Scientific Issue / Finding | Required Correction |
|---|---|---|---|
| **Natural Pseudokinase Labels** | VRK3 (Q9Y616) and ILK (Q13418) labeled `is_inconsistent: True` ("Misannotated") | **Severe Scientific Flaw**: Pseudokinases have legitimate regulatory, non-catalytic scaffolding roles. Their UniProt annotations correctly identify them as inactive kinases/pseudokinases. They are NOT annotation errors. | Classify in **Category B (`NATURAL_EXCEPTION`)**. Label as biological exceptions, not confirmed annotation errors. Remove from binary misannotation ground-truth. |
| **Natural Subset Performance** | Reported **100% Precision, 100% Recall, F1=1.0** on Natural Subset | **Misleading Metric Artifact**: Combining 10 congruent references (`is_inconsistent=False`) and 2 pseudokinases (`is_inconsistent=True`) created a synthetic 2-positive class where the model flagged both pseudokinases, creating an artificial 1.0 F1 score. | Separate natural exploratory analysis from binary classification. Natural pseudokinases must be evaluated for biological feature detection and explanation, not binary error classification. |
| **ESM-2 Embedding Anomaly Detector** | **0.000 Precision, 0.000 Recall, 0 TP, 0 FP** (0 positive predictions) | **Methodological Limitation & Threshold Mismatch**: Global mean-pooled ESM-2 embeddings (8M model) are dominated by the stable catalytic core fold. A single-residue or 3-residue motif perturbation alters cosine distance by $<0.001$, while label swaps do not alter sequence at all. The threshold ($0.50$) only triggered on completely non-kinase random peptides. | Add functional class-conditioned manifold distance; calibrate threshold on independent calibration split; provide full score distributions and diagnostics; document inherent limitations of global embeddings for subtle point mutations. |
| **Task Conflation** | All 44 test cases (10 reference, 2 pseudokinase, 16 motif knockouts, 8 label swaps, 8 controls) combined into a single binary evaluation table. | **Conflated Tasks**: Detecting a deliberate label swap (Task 1) is a different computational problem from detecting an artificial motif disruption (Task 2) or investigating a natural pseudokinase (Task 3). | Create **4 explicit, documented benchmark categories** (A, B, C, D) and separate task-specific evaluation metrics tables. |
| **Data Leakage & Calibration** | Calibration cases were defined in code but predictions were computed on all cases without a frozen calibration split. | **Risk of Test Leakage**: Thresholds must be chosen strictly on calibration data and frozen before evaluating test sets. | Formally split synthetic and reference instances into **Calibration (train/dev)** and **Test (eval)** partitions by parent kinase family. Freeze thresholds prior to test execution. |

---

## 2. Baseline Evaluation Results (Preserved Historical Artifact)

The original evaluation artifact (`artifacts/evaluation_report.json`) recorded the following metrics across 44 combined cases:

### Overall Methods Comparison (Baseline)
| Method | Sample Size | TP | FP | TN | FN | Precision | Recall | Specificity | F1-Score | Accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Sequence Similarity Baseline** | 44 | 16 | 6 | 12 | 10 | **0.7273** | **0.6154** | 0.6667 | **0.6667** | 0.6364 |
| **ESM-2 Embedding Anomaly** | 44 | 0 | 0 | 18 | 26 | **0.0000** | **0.0000** | 1.0000 | **0.0000** | 0.4091 |
| **Kinase Biological Features** | 44 | 5 | 1 | 17 | 21 | **0.8333** | **0.1923** | 0.9444 | **0.3125** | 0.5000 |
| **Evidence-Aware Ensemble** | 44 | 2 | 0 | 18 | 24 | **1.0000** | **0.0769** | 1.0000 | **0.1429** | 0.4545 |

### Subset Breakdown (Baseline)
- **Synthetic Subset (32 cases, Ensemble):**
  - TP: 0, FP: 0, TN: 8, FN: 24
  - Precision: 0.000, Recall: 0.000, F1: 0.000, Accuracy: 0.250
- **Natural Subset (12 cases, Ensemble):**
  - TP: 2, FP: 0, TN: 10, FN: 0
  - Precision: 1.000, Recall: 1.000, F1: 1.000, Accuracy: 1.000

---

## 3. Detailed Investigation of Methods

### 3.1 Sequence Similarity Baseline
- **Mechanism:** Computes Biopython `PairwiseAligner` global/local identity against characterized reference panel. Compares assigned functional label with top reference label.
- **Why it performs best on label swaps:** If a tyrosine kinase is assigned the label "serine/threonine kinase", sequence alignment reveals 95%+ identity to EGFR (a tyrosine kinase), directly flagging functional discordance.
- **Limitation:** Cannot detect a clerical error if reference proteins in public databases also carry the same ambiguous label.

### 3.2 ESM-2 Embedding Anomaly Detection
- **Mechanism:** ESM-2 8M (`facebook/esm2_t6_8M_UR50D`) mean-pooled 320-D sequence representations compared via cosine distance to reference panel centroid and k-NN ($k=5$).
- **Score Distribution Diagnostic:**
  - Canonical kinases vs reference centroid: cosine dist $\approx 0.024 - 0.106$ (calibrated score $\approx 0.04 - 0.11$)
  - EGFR with catalytic motif knockout (`VAIK` $\rightarrow$ `VAIA`): cosine dist $= 0.0542$ (calibrated score $= 0.0812$, $\Delta < 0.001$)
  - Natural pseudokinase VRK3: cosine dist $= 0.1604$ (calibrated score $= 0.2033$)
  - Non-kinase random peptide: cosine dist $= 0.8384$ (calibrated score $= 1.000$)
- **Root Cause of Zero Positive Predictions:**
  1. The global embedding space treats the kinase fold as a coherent manifold; 1-4 mutated residues in a 500-residue sequence do not displace the mean vector beyond the generic kinase cluster boundary.
  2. For label swaps, the sequence itself is unaltered; an unsupervised sequence embedding alone has zero signal for label discordance unless conditioned on the assigned functional class.
  3. The fixed threshold of $0.50$ was positioned near the boundary of non-homologous peptides ($>0.80$), so no kinase-derived synthetic case could ever cross it.

### 3.3 Kinase Biological Features Detector
- **Mechanism:** Regular expression and spatial motif validation for VAIK (subdomain II), HRD (subdomain VIB), and DFG (subdomain VII).
- **Strengths:** Highly sensitive to catalytic knockouts (`VAIK` $\rightarrow$ `VAIA`, `HRD` $\rightarrow$ `HAA`, `DFG` $\rightarrow$ `AFG`).
- **Limitation:** Unaltered label swaps have 100% intact motifs, so motif checks alone cannot detect label swaps ($Recall = 0.192$).

### 3.4 Evidence-Aware Ensemble
- **Mechanism:** Weighted linear combination $S = 0.35 A_{\text{emb}} + 0.25 A_{\text{sim}} + 0.25 A_{\text{feat}} + 0.15 P_{\text{prov}}$.
- **Root Cause of Low Recall ($0.077$):**
  - High threshold for positive prediction (`HIGH` or `MODERATE` priority $\ge 0.40$).
  - When ESM-2 contributes $\approx 0.08 \times 0.35 \approx 0.028$, the score is suppressed, requiring both sequence dissimilarity and broken motifs to achieve $\ge 0.40$.

---

## 4. Benchmark Redesign Architecture (Version 2)

### Categorization Framework
1. **Category A (`CONGRUENT_REFERENCE`):**
   - 10 characterized human kinase controls with experimental supporting evidence (e.g., EGFR, SRC, AKT1, BRAF, CDK2, MAPK1, ABL1, MET, JAK2, PRKACA).
   - Ground truth: Negative control for inconsistency (`is_inconsistent: False`).
2. **Category B (`NATURAL_EXCEPTION`):**
   - Naturally occurring pseudokinases and biological exceptions (VRK3, ILK).
   - Ground truth: Exploratory biological exceptions (`is_exception: True`, `is_inconsistent: False`).
   - NOT counted as binary misannotation positives. Evaluated via descriptive feature and explanation tracking.
3. **Category C (`SYNTHETIC_LABEL_CONTRADICTION`):**
   - Controlled functional label swaps between tyrosine kinase and serine/threonine kinase annotations.
   - Ground truth: Positive label contradiction (`is_inconsistent: True`).
4. **Category D (`SYNTHETIC_SEQUENCE_PERTURBATION`):**
   - Controlled catalytic motif disruptions (`VAIK` $\rightarrow$ `VAIA`, `HRD` $\rightarrow$ `HAA`, `DFG` $\rightarrow$ `AFG`).
   - Ground truth: Positive sequence/motif perturbation (`is_inconsistent: True`).

### Evaluation Tasks
- **Task 1: Synthetic Label Contradiction Detection** (Category C vs Controls)
- **Task 2: Synthetic Sequence Perturbation Detection** (Category D vs Controls)
- **Task 3: Natural Biological Exception Characterization** (Category B qualitative/exploratory analysis)
- **Task 4: Confirmed Real-World Annotation Errors** (Explicitly reported as: *No validated real-world confirmed misannotation dataset available in public knowledgebases; exploratory review only.*)

---

## 5. Implementation Roadmap
- **Phase 2:** Update `database/models.py` and `services/benchmark.py` with explicit benchmark categories and task separation.
- **Phase 3:** Centralize metrics in `services/evaluation.py` using standard scikit-learn metrics, verified confusion matrix orientation, and explicit zero-division guards.
- **Phase 4:** Add class-conditioned nearest-neighbor distance to `services/anomaly_detection.py` and calibrate thresholds on frozen calibration splits.
- **Phase 5:** Execute benchmark v2 pipeline producing `artifacts/evaluation_report_v2.json`, `evaluation_summary_v2.csv`, and `benchmark_diagnostics_v2.json`.
- **Phase 6:** Update Streamlit UI (`ui/evaluation.py`) to render task-separated tabs, honest diagnostic charts, and confusion matrices.
- **Phase 7:** Expand automated test suite in `tests/test_evaluation_v2.py`.
- **Phase 8:** Update scientific documentation in `docs/` and `README.md`.
