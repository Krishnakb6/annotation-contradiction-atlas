# The Annotation Contradiction Atlas

### An Evidence-Aware Database & Interactive Application for Detecting Potentially Misannotated Protein Kinase Functions

---

## 1. Project Overview & Scientific Problem

Functional annotations in biological databases such as UniProtKB range from direct physical in vitro assays to computational predictions transferred across phylogenetic homologs. When inaccurate or ambiguous functional labels enter reference knowledgebases, automated rule engines risk systematically propagating them.

However, an atypical sequence or missing catalytic motif is **not necessarily an annotation error**. It may represent a legitimate divergent biological variant, an atypical kinase, or a **pseudokinase** (a protein that has lost phosphotransfer activity but fulfills essential non-catalytic scaffolding or regulatory functions).

### Primary Research Question
> **Can the integration of protein language model embeddings, sequence similarity baselines, kinase-related biological features, and annotation provenance identify potentially inconsistent protein function annotations more effectively and explainably than individual computational methods?**

The **Annotation Contradiction Atlas** provides a functional, scientifically defensible platform that distinguishes between:
1. **Potential functional annotation inconsistencies** (e.g. absent catalytic triads combined with unreviewed automated activity labels).
2. **Unusual but legitimate biological variants** (e.g. divergent folds or atypical kinases).
3. **Biological exceptions / Pseudokinases** (e.g. VRK3 or ILK with recognized motif deviations).
4. **Annotations with limited supporting evidence** (purely computational or unreviewed provenance).

---

## 2. Technology Stack & Architecture

The application is built entirely in Python using scientific libraries and Streamlit:

- **Interactive Interface:** Streamlit multi-page scientific dashboard with Plotly charts, high-contrast monospace biological sequence viewer, and side-by-side reference comparison engine.
- **Bioinformatics & Alignment:** Biopython (`Bio.Align.PairwiseAligner`), sequence motif pattern matching for conserved kinase subdomains (VAIK, HRD, DFG), and ECO code evidence tiering.
- **Protein Language Modeling & ML:** Pretrained ESM-2 model (`facebook/esm2_t6_8M_UR50D`) via Hugging Face Transformers & PyTorch, sliding-window pooling for long sequences, scikit-learn anomaly detection, and SciPy numerical analysis.
- **Database Layer:** SQLite relational database with SQLAlchemy 2.0 ORM, strict foreign keys, indexing, and disk-persisted binary `.npy` artifacts for 320-D embedding vectors.
- **Data Ingestion:** UniProtKB REST API client with query builder, pagination, retry/timeout handling, deterministic caching, and validation.

```
+---------------------------------------------------------------------------------+
|                       STREAMLIT SCIENTIFIC APPLICATION (app.py)                 |
|   Dashboard  |  Kinome Explorer  |  Detail & Motifs  |  Evaluation  |  Methods  |
+---------------------------------------------------------------------------------+
                                      |
                                      v
          +---------------------------+---------------------------+
          |                           |                           |
          v                           v                           v
+------------------+   +----------------------+   +-----------------------+
|  Bioinformatics  |   |    Machine Learning  |   |    Relational DB      |
|  - Pairwise Bio  |   |  - ESM-2 Embeddings  |   |  - SQLite + SQLAlchemy|
|  - VAIK/HRD/DFG  |   |  - Manifold Anomaly  |   |  - 500 Kinases        |
|  - ECO Hierarchy |   |  - Disk Cache (.npy) |   |  - 5,464 Annotations  |
+------------------+   +----------------------+   +-----------------------+
```

---

## 3. Quick Start & Launch Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch the Streamlit Application
```bash
streamlit run app.py
```

---

## 4. Key Application Views & Features

1. **Kinome Evidence Overview (Dashboard):**
   - KPI metrics: 500 imported human protein kinases, 5,464 functional annotations, reviewed status, and priority breakdown.
   - Interactive Plotly Donut chart for Review Priorities (High, Moderate, Low).
   - Annotation Provenance distribution across Experimental (`ECO:0000269`), Homology (`ECO:0000250`), Computational (`ECO:0000256`), and Author Statements.
   - Breakdown of contradictory signals and run telemetry.

2. **Kinome Explorer:**
   - Real-time search across UniProt accession, gene name, and protein title.
   - Multi-parameter filtering by Review Priority and Swiss-Prot review status.
   - Full dataset pagination and instant CSV export.

3. **Protein Record & Motif Inspector:**
   - **High-contrast Primary Amino Acid Sequence viewer** with dark slate background (`#0F172A`) and vivid highlighting:
     - **Green (`#059669`):** Canonical Triad (VAIK, HRD, DFG).
     - **Amber (`#D97706`):** Atypical / Variant Motifs (e.g. `HGN` in VRK3).
   - Radar chart decomposing multi-component anomaly signals: ESM-2 manifold distance, sequence dissimilarity, motif disruption, and provenance uncertainty.
   - Tabular breakdown of functional annotations with direct ECO code evidence levels and links to UniProt entries.

4. **Contradiction Explorer & Side-by-Side Comparison:**
   - Filter review candidates by specific contradiction triggers (e.g., *Broken catalytic motifs*, *ESM-2 embedding outlier*, *Purely computational provenance*).
   - **Comparative Inspection:** Select any candidate kinase to compare directly against its closest characterized reference kinase, displaying pairwise sequence identity, alignment metrics, motif status, and functional concordance side-by-side.

5. **Empirical Benchmark & Evaluation:**
   - Empirical evaluation across all 4 computational methods (Precision, Recall, F1, Specificity, Accuracy).
   - Ensemble Confusion Matrix and performance breakdown comparing Natural Reference Kinases (100% Precision) vs Controlled Synthetic Perturbations.

6. **Scientific Methodology & Documentation:**
   - Detailed scientific documentation of catalytic triad biochemistry (VAIK, HRD, DFG), scoring formulas, pseudokinase differentiation, and evidence tiering.

---

## 5. CLI Data Pipeline & Evaluation Scripts

### Ingest Human Kinase Records from UniProt
```bash
python scripts/fetch_data.py --max-records 500 --init-db
```
*(If offline, the pipeline seamlessly employs the cached reference kinome fallback dataset).*

### Run the Computational Analysis Pipeline
```bash
python scripts/run_analysis.py --limit 150
```

### Run the Benchmark Evaluation
```bash
python scripts/run_evaluation.py --num-synthetic 32
```
*Outputs evaluation metrics and saves `artifacts/evaluation_report.json`.*

### Run System Health Diagnostic
```bash
python scripts/test_system.py
```

---

## 6. Automated Testing

Run the automated test suite covering database models, UniProt ingestion, motif detection, embeddings, scoring, evaluation, and Streamlit visual components:
```bash
python -m pytest tests/ -v
```
All unit and integration tests pass with 100% success rate.
