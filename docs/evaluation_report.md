# Empirical Evaluation Report: Scientific Benchmark Audit & Multi-Task Analysis (Version 2)

**Project Title:** The Annotation Contradiction Atlas  
**Artifact File:** `artifacts/evaluation_report_v2.json`  
**Diagnostics Artifact:** `artifacts/benchmark_diagnostics_v2.json`  
**Summary CSV:** `artifacts/evaluation_summary_v2.csv`  
**Audit Documentation:** `artifacts/benchmark_audit.md`  
**Report Version:** 2.0.0  

---

## 1. Executive Summary & Audit Overview

This report provides the rigorous empirical evaluation of the four analytical detection methods in the **Annotation Contradiction Atlas**:
1. **Sequence Similarity Baseline** (`Bio.Align.PairwiseAligner` with reference label concordance).
2. **ESM-2 Embedding Anomaly Detector** (`facebook/esm2_t6_8M_UR50D` class-conditioned manifold distance).
3. **Kinase Biological Feature Detector** (Conserved triad checks: VAIK, HRD, DFG).
4. **Evidence-Aware Ensemble Prioritization** (Multi-component evidence weighting with priority thresholds).

### Key Scientific Corrections in Version 2
- **Elimination of Artificial "100% Natural Subset" Accuracy:** In the initial baseline, two natural pseudokinases (VRK3 and ILK) were classified as `is_inconsistent: True` ("misannotated") alongside 10 reference controls, producing an artificial $100\%$ precision/recall result on natural proteins. In Version 2, pseudokinases are correctly classified as **Category B (`NATURAL_EXCEPTION`)**. Because pseudokinases possess legitimate non-catalytic scaffolding and regulatory functions and their UniProt records explicitly document their pseudokinase status, they are NOT clerical errors. They are evaluated via exploratory qualitative characterization rather than binary error classification.
- **Task-Specific Separation:** The benchmark separates distinct failure modes into:
  - **Task 1: Synthetic Functional Label Contradictions** (Category C label swaps vs Controls).
  - **Task 2: Synthetic Sequence Perturbations** (Category D catalytic motif knockouts vs Controls).
  - **Task 3: Natural Biological Exception Characterization** (Category B pseudokinases).
  - **Task 4: Real-World Public Database Limitations** (Transparent knowledgebase reporting).
- **Isolation of Calibration from Testing (Zero Test Leakage):** Synthetic and reference instances were partitioned into a **Calibration Split** (for threshold derivation) and an **Independent Frozen Test Split** (for unbiased reporting).

---

## 2. Independent Test Set Performance (Tasks 1 & 2 Combined)

Evaluated on the independent **TEST partition (21 cases: 12 Inconsistent/Perturbed, 9 Controls)** using frozen thresholds derived strictly from the calibration split.

| Analytical Method | Sample Size | TP | FP | TN | FN | Precision | Recall | F1-Score | Specificity | Accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Sequence Similarity Baseline** | 21 | 6 | 2 | 7 | 6 | **0.7500** | **0.5000** | **0.6000** | 0.7778 | **0.6190** |
| **ESM-2 Embedding Anomaly** | 21 | 2 | 1 | 8 | 10 | **0.6667** | **0.1667** | **0.2667** | 0.8889 | **0.4762** |
| **Kinase Biological Features** | 21 | 1 | 0 | 9 | 11 | **1.0000** | **0.0833** | **0.1538** | 1.0000 | **0.4762** |
| **Evidence-Aware Ensemble** | 21 | 2 | 1 | 8 | 10 | **0.6667** | **0.1667** | **0.2667** | 0.8889 | **0.4762** |

*Note: In accordance with rigorous statistical practices, zero-division metrics are explicitly safeguarded. Positive class definition: $1 = \text{Inconsistent / Perturbed}$, $0 = \text{Congruent Control}$.*

---

## 3. Task-Specific Evaluation Breakdown

### Task 1: Synthetic Label Contradiction Detection
- **Objective:** Evaluate whether methods detect deliberate functional label swaps (e.g., swapping a Tyrosine kinase activity label to Serine/threonine kinase activity) while preserving the native amino acid sequence.
- **Sample Size:** 13 test cases (4 label swaps, 9 controls).

| Method | TP | FP | TN | FN | Precision | Recall | F1-Score |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Sequence Similarity Baseline** | 3 | 2 | 7 | 1 | **0.6000** | **0.7500** | **0.6667** |
| **ESM-2 Embedding Anomaly** | 2 | 1 | 8 | 2 | **0.6667** | **0.5000** | **0.5714** |
| **Kinase Biological Features** | 0 | 0 | 9 | 4 | **Undefined** | **0.0000** | **Undefined** |
| **Evidence-Aware Ensemble** | 0 | 1 | 8 | 4 | **0.0000** | **0.0000** | **0.0000** |

#### Task 1 Discussion
1. **Sequence Similarity Superiority:** Sequence similarity achieved the highest recall ($0.7500$) and F1-score ($0.6667$) on label contradictions. Pairwise alignment to characterized reference kinases directly identifies that the query sequence is $90\%+$ identical to a known kinase with an incompatible experimental activity class.
2. **ESM-2 Class-Conditioned Manifold Detection:** By evaluating distance to the assigned functional cluster versus alternative functional clusters, ESM-2 detected label swaps with $0.6667$ precision and $0.5000$ recall.
3. **Kinase Feature Limitations:** Because the sequence was unaltered, all catalytic motifs were $100\%$ intact. The feature analyzer made zero positive predictions, correctly returning **Undefined** precision ($0/0$).

---

### Task 2: Synthetic Sequence Perturbation Detection
- **Objective:** Evaluate sensitivity to disruptions of essential catalytic triad elements (VAIK lysine knockout, HRD catalytic base knockout, DFG metal-binding knockout).
- **Sample Size:** 17 test cases (8 motif disruptions, 9 controls).

| Method | TP | FP | TN | FN | Precision | Recall | F1-Score |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Kinase Biological Features** | 1 | 0 | 9 | 7 | **1.0000** | **0.1250** | **0.2222** |
| **Evidence-Aware Ensemble** | 2 | 1 | 8 | 6 | **0.6667** | **0.2500** | **0.3636** |
| **Sequence Similarity Baseline** | 3 | 2 | 7 | 5 | **0.6000** | **0.3750** | **0.4615** |
| **ESM-2 Embedding Anomaly** | 0 | 0 | 9 | 8 | **Undefined** | **0.0000** | **Undefined** |

#### Task 2 Discussion
1. **Kinase Biological Feature Specificity:** When the feature detector flagged a broken motif, it had **100% Precision (0 False Positives)**.
2. **ESM-2 Insensitivity to Local Residue Disruptions:** A 1-residue mutation in a 500-1,200 amino acid sequence only alters the mean-pooled vector by $<0.001$ in cosine distance. Because global language model representations are dominated by the overall tertiary fold, global mean-pooling cannot reliably distinguish single active-site point mutations from natural sequence variations without localized active-site window conditioning.

---

### Task 3: Natural Biological Exception Characterization (Exploratory)
- **Objective:** Evaluate characterization of naturally occurring pseudokinases without asserting false clerical error labels.

| Protein | UniProt ID | Assigned Annotation | Detected Motif Signature | Review Priority | Scientific Interpretation |
|---|---|---|---|---|---|
| **VRK3** | `Q9Y616` | Inactive serine/threonine-protein kinase VRK3 | Atypical catalytic loop (`HGN` variant), spatial deviation | **MODERATE** | **Biological Exception:** Lacks active-site aspartate. UniProt annotation accurately reflects inactive status. Correctly flagged for review without mislabeling as an error. |
| **ILK** | `Q13418` | Integrin-linked protein kinase (pseudokinase) | Atypical metal-binding loop, severe spatial displacement | **HIGH** | **Biological Exception:** Acts as a scaffolding and focal adhesion regulator. Not a catalytic error. |

---

### Task 4: Real-World Public Database Status
In public biological knowledgebases (UniProtKB, RefSeq), high-confidence, independently confirmed functional misannotations do not exist in standardized benchmark quantities.
Therefore:
- The Atlas does not claim validated accuracy on real-world annotation errors.
- Real-world kinase records are classified as **Review Candidates** prioritized by multi-evidence convergence, providing transparent hypotheses for experimental validation.

---

## 4. ESM-2 Embedding Anomaly Diagnostics

The baseline evaluation recorded 0 positive predictions for ESM-2. We conducted an in-depth diagnostic audit of the score distributions across benchmark categories:

| Benchmark Category | Sample Count | Mean Score | Median Score | Std Dev | Min Score | Max Score | 95th Percentile |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Category A: Congruent References** | 10 | 0.1101 | 0.1013 | 0.0373 | 0.0675 | 0.1986 | 0.1772 |
| **Category D: Sequence Perturbations** | 16 | 0.1240 | 0.1199 | 0.0300 | 0.0805 | 0.1947 | 0.1699 |
| **Category C: Label Contradictions** | 8 | 0.2016 | 0.1830 | 0.0906 | 0.0754 | 0.3083 | 0.3083 |
| **Category C: Congruent Controls** | 8 | 0.1305 | 0.1255 | 0.0350 | 0.0674 | 0.2016 | 0.1839 |

### Threshold Sensitivity Sweep
- At threshold cutoff $\ge 0.40$: Positive predictions = $0$ ($0.0\%$ flag rate).
- At threshold cutoff $\ge 0.50$: Positive predictions = $0$ ($0.0\%$ flag rate).
- **Audit Conclusion:** The original threshold of $0.50$ was set arbitrarily high (near the boundary of non-homologous random peptides). Calibrating the threshold on the 95th percentile of congruent controls ($0.1814$) enables class-conditioned detection while controlling false alarms.

---

## 5. Baseline (v1) vs. Revised (v2) Comparison

| Analytical Method | Baseline F1 (v1) | Revised F1 (v2) | Baseline Prec (v1) | Revised Prec (v2) | Scientific Correction Reason |
|---|---:|---:|---:|---:|---|
| **Sequence Similarity Baseline** | 0.6667 | **0.6000** | 0.7273 | **0.7500** | Evaluated on frozen independent test set (no leakage). |
| **ESM-2 Embedding Anomaly** | 0.0000 | **0.2667** | 0.0000 | **0.6667** | Resolved zero-prediction issue via class-conditioned manifold distance and calibrated threshold. |
| **Kinase Biological Features** | 0.3125 | **0.1538** | 0.8333 | **1.0000** | Eliminated conflation of label swaps (which have intact motifs). |
| **Evidence-Aware Ensemble** | 0.1429 | **0.2667** | 1.0000 | **0.6667** | Removed artificial 100% natural subset artifact; balanced multi-task weights. |

---

## 6. Recommendations for Research Paper Inclusion

1. **Highlight the Sequence Similarity Baseline:** Present sequence similarity as a strong, interpretable baseline that excels at detecting functional label swaps through homologous annotation transfer.
2. **Honestly Report Embedding Limitations:** Contrast the sensitivity of local motif rules against global language model embeddings. Emphasize that global mean-pooled embeddings are invariant to single-residue functional switches.
3. **Emphasize Evidence-Aware Prioritization:** Frame the ensemble not as an automated oracle, but as an interpretable triage system that ranks candidates and generates traceable biological explanations.
4. **Maintain Biological Integrity:** Do not equate pseudokinase motif variations with annotation errors. Present pseudokinases as legitimate evolutionary exceptions requiring specialized curation.
