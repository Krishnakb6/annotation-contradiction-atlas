# Scientific Methodology Report: The Annotation Contradiction Atlas

**Project:** The Annotation Contradiction Atlas  
**Discipline:** Bioinformatics & Computational Structural Biology  

---

## 1. Abstract and Research Question

Automated computational pipelines populate public biological databases with millions of functional annotations inferred through sequence homology or transfer rules. When historical misannotations or borderline pseudokinases are imported, automated transfer mechanisms propagate these inconsistencies throughout phylogenetic clades.

This investigation explores:
> **Research Question:** Can the integration of protein language model embeddings, sequence similarity, kinase-related biological features, and annotation provenance identify potentially inconsistent protein function annotations more effectively and explainably than individual computational methods?

We demonstrate an evidence-aware system combining deep language model representations (**ESM-2**), pairwise sequence alignment baselines, catalytic triad motif validation (**VAIK, HRD, DFG**), and structured evidence tiers (**ECO codes**). We emphasize that our system does not declare definitive errors, but rather produces interpretable, calibrated **review priorities**.

---

## 2. Biological Background & Landmarked Architecture of Protein Kinases

Human protein kinases (the "kinome") regulate virtually all cellular signal transduction cascades via transfer of the $\gamma$-phosphate of ATP to hydroxyl groups of target serine, threonine, or tyrosine residues. Structurally, conventional protein kinases share a conserved catalytic core of 12 subdomains folded into an N-terminal lobe and a C-terminal lobe.

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
We employ pretrained **ESM-2** (`esm2_t6_8M_UR50D` / `esm2_t12_35M_UR50D`), which captures deep contextual, structural, and evolutionary constraints without requiring homologous family multiple sequence alignments (MSAs).
- **Pooling:** Mean-pooling across the sequence tokens, excluding special `<cls>`, `<eos>`, and padding tokens.
- **Windowing:** Sequences exceeding the model context length (1,024 residues) undergo sliding-window pooling with 512-residue strides. For very large proteins (> 2,500 residues), up to 4 representative domain windows are pooled to maintain computational efficiency.
- **Artifact Caching:** 320-dimensional embedding vectors are stored in disk `.npy` binary artifacts linked to relational records.

### Method C: Manifold Anomaly Detection
To assess whether a protein occupies an unusual region in the kinase manifold, we calculate:
1. **Centroid Cosine Distance:** Distance to the geometric center of high-confidence reference kinases:
   $$d_{\text{centroid}} = 1.0 - \frac{\mathbf{u} \cdot \mathbf{c}}{\|\mathbf{u}\| \|\mathbf{c}\|}$$
2. **$k$-Nearest Neighbors ($k$-NN) Distance:** Mean distance to the closest $k=5$ reference kinases in embedding space:
   $$d_{k\text{NN}} = \frac{1}{k} \sum_{i=1}^k d(\mathbf{u}, \mathbf{r}_i)$$
3. **Calibrated Anomaly Score:**
   $$A_{\text{emb}} = \min\left(1.0, \frac{0.4 \cdot d_{\text{centroid}} + 0.6 \cdot d_{k\text{NN}}}{0.80}\right)$$

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

## 6. Controlled Benchmark Design

To avoid data leakage:
- **Category A (Reference):** Experimentally characterized kinases (EGFR, SRC, AKT1, BRAF, CDK2, MAPK1).
- **Category B (Natural Exceptions):** Documented human pseudokinases (VRK3, ILK).
- **Category C (Controlled Synthetic Perturbations):**
  - Catalytic lysine knockout ($VAIK \rightarrow VAIA$).
  - Catalytic base knockout ($HRD \rightarrow HAA$).
  - Metal binding knockout ($DFG \rightarrow AFG$).
  - Functional label swaps (Tyrosine kinase $\leftrightarrow$ Serine/Threonine kinase).
  - Unaltered positive controls.

Synthetic examples are evaluated on independent splits and **never injected into the real biological database**. Performance on synthetic and natural subsets is reported separately.
