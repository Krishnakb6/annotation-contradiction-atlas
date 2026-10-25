# Scientific Methodology Report: The Annotation Contradiction Atlas (Version 2)

**Project:** The Annotation Contradiction Atlas  
**Discipline:** Bioinformatics & Computational Structural Biology  
**Methodology Version:** 2.0.0  

---

## 1. Abstract and Research Question

Automated computational pipelines populate public biological databases with millions of functional annotations inferred through sequence homology or transfer rules. When historical misannotations or borderline pseudokinases are imported, automated transfer mechanisms propagate these inconsistencies throughout phylogenetic clades.

This investigation explores:
> **Research Question:** Can the integration of protein language model embeddings, sequence similarity, kinase-related biological features, and annotation provenance identify potentially inconsistent protein function annotations more effectively and explainably than individual computational methods?

We demonstrate an evidence-aware system combining deep language model representations (**ESM-2**), pairwise sequence alignment baselines, catalytic triad motif validation (**VAIK, HRD, DFG**), and structured evidence tiers (**ECO codes**). We emphasize that our system does not declare definitive errors, but rather produces interpretable, calibrated **review priorities**.

---

## 2. Biological Background & Conserved Architecture of Protein Kinases

Human protein kinases (the "kinome") regulate virtually all cellular signal transduction cascades via transfer of the $\gamma$-phosphate of ATP to hydroxyl groups of target serine, threonine, or tyrosine residues. Conventional protein kinases share a conserved catalytic core of 12 subdomains folded into an N-terminal lobe and a C-terminal lobe.

Within this conserved core, three catalytic motifs are critical:
1. **VAIK Motif (Subdomain II):** Situated on the $\beta3$-strand. The core Lysine ($K$) forms ionic bonds with the $\alpha$- and $\beta$-phosphates of ATP, orienting the nucleotide for transfer.
2. **HRD Motif (Subdomain VIB):** Situated within the catalytic loop. The invariant Aspartate ($D$) functions as a catalytic base that accepts a proton from the substrate hydroxyl group.
3. **DFG Motif (Subdomain VII):** Situated at the beginning of the activation loop. The Aspartate ($D$) coordinates a divalent magnesium ion ($Mg^{2+}$), which complexes and stabilizes the ATP phosphates.

### Pseudokinases: The Biological Exception Hazard
Approximately 10% of the human kinome (~50 proteins) consists of **pseudokinases**—proteins that have accumulated substitutions in one or more catalytic motifs (e.g., VRK3 with `HGN` instead of `HRD`, or ILK with atypical activation segments). Crucially, pseudokinases are **not misannotated records**; they perform vital non-catalytic biological functions, such as allosteric activation of other enzymes, scaffolding, and subcellular localization. A naive computational check that marks any kinase lacking a canonical motif as "wrong" is biologically defective. Our system explicitly recognizes pseudokinase signatures as **biological exceptions** rather than database errors.

---

## 3. Data Acquisition & Validation Pipeline

We query the UniProtKB REST API (`https://rest.uniprot.org/uniprotkb/search`) with the query:
```
taxonomy_id:9606 AND reviewed:true AND (family:"protein kinase" OR keyword:"Kinase [KW-0418]" OR ec:2.7.10.* OR ec:2.7.11.*)
```
- **Validation:** Every sequence is validated against standard single-letter IUPAC amino acid codes (`ACDEFGHIKLMNPQRSTVWY`). Truncated or malformed sequences are rejected.
- **Traceability:** Accessions, source URLs, retrieval timestamps, and UniProtKB reviewed/unreviewed statuses are permanently recorded.
- **Evidence Extraction:** We parse catalytic comments, EC numbers, and reaction evidence codes down to PubMed IDs and Evidence and Conclusion Ontology (**ECO**) terms.

---

## 4. Multi-Method Computational Analysis

### Method A: Sequence Similarity Baseline
We align query sequences against an independently characterized panel of reference kinases using local/global alignment with affine gap penalties. We track:
- Best matching reference accession
- Sequence identity percentage
- Query coverage
- Functional class agreement (e.g. Tyrosine kinase vs Serine/Threonine kinase).

### Method B: Compact Protein Language Model Embeddings (ESM-2)
We employ pretrained **ESM-2** (`esm2_t6_8M_UR50D`), which captures deep contextual, structural, and evolutionary constraints without requiring homologous family multiple sequence alignments (MSAs).
- **Pooling:** Mean-pooling across the sequence tokens, excluding special `<cls>`, `<eos>`, and padding tokens.
- **Windowing:** Sequences exceeding the model context length (1,024 residues) undergo sliding-window pooling with 512-residue strides. For very large proteins (> 2,500 residues), representative domain windows are pooled to maintain computational efficiency.
- **Artifact Caching:** 320-dimensional embedding vectors are stored in disk `.npy` binary artifacts linked to relational records.

### Method C: Manifold Anomaly Detection & Class Conditioning
To assess whether a protein occupies an unusual region in the kinase manifold, we calculate:
1. **Centroid Cosine Distance:** Distance to the geometric center of high-confidence reference kinases:
   $$d_{\text{centroid}} = 1.0 - \frac{\mathbf{u} \cdot \mathbf{c}}{\|\mathbf{u}\| \|\mathbf{c}\|}$$
2. **$k$-Nearest Neighbors ($k$-NN) Distance:** Mean distance to the closest $k=5$ reference kinases in embedding space:
   $$d_{k\text{NN}} = \frac{1}{k} \sum_{i=1}^k d(\mathbf{u}, \mathbf{r}_i)$$
3. **Class-Conditioned Manifold Discordance:** When an assigned functional label is available (e.g. Tyrosine kinase), we compute distance to the assigned functional cluster versus alternative functional clusters. If a query sequence is markedly closer to an alternative functional manifold than to its assigned class, a functional discordance penalty is applied.
4. **Empirically Calibrated Anomaly Score:**
   $$A_{\text{emb}} = \min\left(1.0, \frac{0.4 \cdot d_{\text{centroid}} + 0.6 \cdot d_{k\text{NN}}}{\text{scale}} + P_{\text{discordance}}\right)$$
   The threshold is calibrated on the 95th percentile of independent calibration controls (default $\approx 0.18$).

### Method D: Catalytic Feature Integrity
We scan the sequence using regular expressions designed to capture canonical motifs and known variant signatures:
- VAIK: `[LIVMAFY][AVILMF][IVATC][K]` (canonical) or `...[RQNAGS]` (variant)
- HRD: `[HYF][RKN][D]` (canonical) or `[HYF][A-Z][SANG]` (variant)
- DFG: `[D][FYSW][GSA]` (canonical) or `[NEQS][FYSW][GSA]` (variant)

We enforce spatial domain ordering ($VAIK < HRD < DFG$). The catalytic integrity score is formulated as:
$$\text{Integrity} = \frac{1.0 \cdot N_{\text{canonical}} + 0.45 \cdot N_{\text{variant}}}{3.0}$$
$$A_{\text{feat}} = 1.0 - \text{Integrity}$$

### Method E: Annotation Provenance Assessment
We map evidence codes to four reliability tiers:
- **Experimental (ECO:0000269, ECO:0000314):** Direct in vitro assay ($P_{\text{prov}} \approx 0.05$).
- **Phylogenetic / Homology Curated (ECO:0000250):** Similarity to characterized homolog ($P_{\text{prov}} \approx 0.30$).
- **Computational Unreviewed (ECO:0000256, IEA):** Automated rule transfer ($P_{\text{prov}} \approx 0.70$).
- **Unannotated / Unspecified:** Missing evidence ($P_{\text{prov}} \approx 0.85$).

---

## 5. Evidence-Aware Contradiction Scoring & Safeguards

Rather than outputting an uncalibrated probability of error, we synthesize component scores into an explainable **Review Priority** index:

$$S = 0.35 \cdot A_{\text{emb}} + 0.25 \cdot A_{\text{sim}} + 0.25 \cdot A_{\text{feat}} + 0.15 \cdot P_{\text{prov}}$$

### Essential Scientific Safeguards
1. **Low Annotation Confidence Alone Cannot Trigger High Priority:** If a protein possesses intact canonical motifs ($A_{\text{feat}} \le 0.15$) and a standard embedding ($A_{\text{emb}} \le 0.40$), the score is strictly capped at $\le 0.55$ (Moderate Priority). Absence of evidence is not negative evidence.
2. **Isolated Embedding Anomaly Cannot Claim Misannotation:** If only the embedding is atypical while sequence motifs and homology are normal, the protein is categorized as a *"Divergent biological variant candidate"* rather than an annotation error.
3. **Pseudokinase Differentiation:** Records exhibiting known variant motifs are explicitly classified as *"Biological Exception / Pseudokinase Candidate"*.

---

## 6. Scientific Benchmark Construction (Version 2)

To guarantee scientific validity and eliminate the artificial metric inflation identified during audit:

### Explicit Benchmark Categories
- **Category A: High-Confidence Reference Controls (`CONGRUENT_REFERENCE`):**
  10 characterized human kinases with experimentally verified phosphotransfer activity (EGFR, SRC, AKT1, BRAF, CDK2, MAPK1, ABL1, MET, JAK2, PRKACA). Ground truth: `is_inconsistent: False`.
- **Category B: Natural Biological Exceptions (`NATURAL_EXCEPTION`):**
  Documented human pseudokinases (VRK3, ILK). Ground truth: `is_inconsistent: False` (legitimate pseudokinases fulfilling regulatory/scaffolding roles; NOT clerical misannotations). Evaluated qualitatively/exploratorily.
- **Category C: Controlled Synthetic Label Contradictions (`SYNTHETIC_LABEL_CONTRADICTION`):**
  Controlled functional label swaps between Tyrosine kinase and Serine/threonine kinase annotations, holding sequences unaltered. Ground truth: `is_inconsistent: True`.
- **Category D: Controlled Synthetic Sequence Perturbations (`SYNTHETIC_SEQUENCE_PERTURBATION`):**
  Controlled catalytic motif alterations (catalytic lysine knockout $VAIK \rightarrow VAIA$, catalytic base knockout $HRD \rightarrow HAA$, metal binding knockout $DFG \rightarrow AFG$). Ground truth: `is_inconsistent: True`.
- **Unaltered Synthetic Controls (`CONGRUENT_CONTROL`):**
  Unaltered sequences paired with native verified annotations as negative controls. Ground truth: `is_inconsistent: False`.

---

## 7. Calibration vs. Testing Partitioning (Zero Test Leakage)

To prevent data snooping and circular validation:
1. **Calibration Partition (50%):** 5 Reference controls, 8 motif knockouts, 4 label swaps, 4 unaltered controls. Used exclusively to calibrate empirical anomaly thresholds (e.g. 95th percentile of controls for ESM-2).
2. **Independent Test Partition (50%):** 5 Reference controls, 8 motif knockouts, 4 label swaps, 4 unaltered controls (21 cases total). Evaluated using frozen thresholds derived during calibration.
3. **Exploratory Partition:** Category B pseudokinases evaluated separately without conflation into binary classification accuracy.

---

## 8. Multi-Task Evaluation Design

The benchmark evaluates four distinct scientific tasks:
- **Task 1: Synthetic Label Contradiction Detection:** Evaluates Category C vs Controls.
- **Task 2: Synthetic Sequence Perturbation Detection:** Evaluates Category D vs Controls.
- **Task 3: Natural Biological Exception Characterization:** Evaluates Category B (VRK3, ILK) for correct atypical motif detection and biological exception explanations.
- **Task 4: Confirmed Annotation Error Status:** Reports public database limitations transparently.

---

## 9. Reproducibility Procedures

All benchmark runs can be reproduced deterministically:
```bash
python scripts/run_evaluation.py --seed 42 --num-synthetic 32
```
Output artifacts:
- `artifacts/evaluation_report_v2.json`: Master evaluation JSON with all task metrics and detailed cases.
- `artifacts/evaluation_summary_v2.csv`: Summary metrics table across methods.
- `artifacts/benchmark_diagnostics_v2.json`: Score distributions and sensitivity sweep diagnostics.
- `artifacts/benchmark_audit.md`: Scientific audit trail and methodology rationale.
