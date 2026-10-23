# Project Demonstration & Presentation Guide

**Project Title:** The Annotation Contradiction Atlas: An Evidence-Aware Database for Detecting Potentially Misannotated Protein Kinase Functions  
**Audience:** Evaluators, Bioinformatics Researchers, Database Architects  

---

## 1. 2-Minute Elevator Pitch

Public biological knowledgebases like UniProtKB are indispensable to modern biomedical discovery. However, millions of computational annotations are propagated automatically across homologs, creating systemic risks of unverified error transfer.

A protein with an atypical motif is **not necessarily misannotated**—it may be a genuine biological exception or a **pseudokinase** regulating vital scaffolding pathways. 

Our application, **The Annotation Contradiction Atlas**, provides an evidence-aware relational database and interactive exploration platform. By synthesizing **ESM-2 protein language model embeddings**, **sequence similarity baselines**, **catalytic motif integrity (VAIK, HRD, DFG)**, and **annotation provenance (ECO codes)**, the Atlas prioritizes review candidates with explainable justifications without declaring unverified errors.

---

## 2. Key Scientific Innovations

1. **Evidence-Aware Prioritization vs Black-Box AI:** We do not claim proteins are "definitely misannotated". We formulate explicit **review priorities (High, Moderate, Low)** accompanied by complete signal breakdowns.
2. **Pseudokinase Discrimination:** Distinguishes known non-catalytic pseudokinase signatures (e.g., VRK3 with `HGN`) from arbitrary sequence errors or clerical mistakes.
3. **Multi-Method Orthogonality:**
   - Sequence similarity catches functional class mismatches.
   - Motif checks catch catalytic triad knockouts.
   - ESM-2 embeddings catch manifold-level domain anomalies.
   - Provenance analysis distinguishes experimental assays from automated rules.
4. **Leak-Free Benchmark:** Evaluates controlled synthetic perturbations (quarantined from the real biological dataset) alongside natural reference kinases.

---

## 3. Demonstration Workflow & Script

### Step 1: Launch Application
```bash
streamlit run app.py
```
- Showcase the clean scientific layout, navigation sidebar, and team attribution.

### Step 2: Overview Dashboard (Page 1)
- Point to real metrics: **500 imported human kinases**, **5,464 functional annotations**, and live review priority distribution.
- Highlight the **Annotation Evidence Tiers** chart: shows the ratio of direct experimental assay records (`ECO:0000269`) vs computational unreviewed rules (`ECO:0000256`).

### Step 3: Protein Explorer (Page 2)
- Demonstrate live search: Type `EGFR` or `AKT1` or `VRK3`.
- Filter by **Review Priority** (HIGH, MODERATE, LOW).
- Click **"Export CSV"** to demonstrate downloadable results for researchers.
- Select `VRK3` and click **"Open Protein Detail"**.

### Step 4: Protein Detail Inspection (Page 3)
- Highlight the **Scientific Explanation Banner**: Explains why VRK3 is flagged as a *"Biological Exception / Pseudokinase Candidate"*.
- Examine the **Radar Chart**: Visualizes the 4 component anomaly scores.
- Tab 1 (**Biological Sequence & Motifs**): Show the interactive sequence box with highlighted motifs. Note the variant `HGN` motif at position 74!
- Tab 2 (**Functional Annotations**): Show the explicit evidence codes and PubMed citations.
- Tab 3 (**Nearest References**): Point out the nearest reference kinase and alignment metrics.

### Step 5: Contradiction Explorer (Page 4)
- Filter by specific contradiction triggers: e.g., *"Variant motif sequence"* or *"ESM-2 embedding outlier"*.
- Demonstrate the **Side-by-Side Comparison Tool**: Compare a flagged candidate kinase directly against its closest reference kinase (sequence identity, motif comparisons, functional label concordance).

### Step 6: Analysis & Evaluation (Page 5)
- Review empirical benchmark metrics across all 4 methods.
- Point to the **Confusion Matrix** and note the **100% precision on natural reference kinases**.
- Emphasize the separation of synthetic subset performance vs natural reference performance.

### Step 7: Data Management (Page 6)
- Showcase the UniProt live API ingestion controls and background pipeline executor.
- Show the **Schema Inspection** expander displaying the SQLite tables and indexes.

---

## 4. Frequently Asked Questions (Defense Preparation)

**Q1: Why use ESM-2 instead of BLAST alone?**  
*A:* BLAST relies entirely on pairwise sequence alignment. ESM-2 captures high-order evolutionary constraints, physicochemical patterns, and structural viability directly from raw sequences without requiring multiple sequence alignments.

**Q2: Does your system prove that a UniProt annotation is false?**  
*A:* No. In accordance with biological integrity guidelines, we explicitly state that computational flags highlight *review candidates* and *evidence conflicts*. Conclusive proof of inactivity requires in vitro enzymatic assays.

**Q3: How do you prevent data leakage during evaluation?**  
*A:* All synthetic perturbation cases are isolated from real database records, tagged with random seeds, and partitioned into independent splits before threshold evaluation.
