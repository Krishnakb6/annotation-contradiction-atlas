"""
Page 7: Scientific Methodology & System Documentation.
Details research background, biological motivation, computational algorithms,
evidence tiers, benchmark design, and team attribution.
"""
from __future__ import annotations

import streamlit as st
from config import PROJECT_TITLE, PROJECT_SUBTITLE, WEIGHTS, PRIORITY_THRESHOLDS


def render_methods():
    st.title("Scientific Methodology & Documentation")
    st.markdown(f"**{PROJECT_TITLE}** — *{PROJECT_SUBTITLE}*")

    st.markdown("---")

    st.subheader("1. Scientific Motivation & Research Question")
    st.markdown("""
    Protein knowledgebases such as UniProtKB contain functional annotations supported by disparate tiers of evidence.
    While some entries reflect rigorous direct biochemical characterization (e.g., in vitro phosphotransfer assays),
    millions of entries derive from automated homology-based inheritance or computational rule engines.
    
    A central hazard in modern bioinformatics is **error propagation**: an erroneous or ambiguous functional assignment,
    once entered into a reference database, is systematically copied to newly sequenced homologs.
    
    However, detecting annotation inconsistencies is scientifically subtle:
    - An unusual sequence or missing catalytic motif is **not necessarily an error**.
    - It may represent a divergent biological variant, an atypical kinase, an allosteric regulator, or a **pseudokinase**
      (proteins that have lost catalytic phosphotransfer but retain crucial non-catalytic scaffolding roles).
    
    > **Primary Research Question:**
    > *Can the integration of protein language model embeddings (ESM-2), sequence similarity baselines,
    > kinase-related biological features, and annotation provenance identify potentially inconsistent protein
    > function annotations more effectively and explainably than individual computational methods?*
    """)

    st.markdown("---")

    st.subheader("2. Conserved Protein Kinase Architecture")
    st.markdown("""
    Human protein kinases share a conserved catalytic domain fold consisting of an N-terminal lobe (primarily β-sheets)
    and a C-terminal lobe (predominantly α-helices). We focus on three universally recognized catalytic landmarks:
    
    1. **VAIK Motif (Subdomain II):**
       - Canonical sequence: `[LIVMAFY][AVILMF][IVATC][K]`
       - The invariant **Lysine (K)** forms salt bridges with the α- and β-phosphates of ATP, correctly orienting the triphosphate chain for catalysis.
    2. **HRD Motif (Subdomain VIB - Catalytic Loop):**
       - Canonical sequence: `[HYF][RKN][D]`
       - The **Aspartate (D)** acts as the catalytic base that accepts a proton from the incoming substrate hydroxyl group (serine, threonine, or tyrosine).
    3. **DFG Motif (Subdomain VII - Activation Segment Start):**
       - Canonical sequence: `[D][FYSW][GSA]`
       - The **Aspartate (D)** coordinates a divalent metal cation ($Mg^{2+}$), which stabilizes the nucleotide complex during phosphoryl transfer.
    
    *Safeguard:* A missing motif is a **review signal**, not proof of an error. Known human pseudokinases (e.g., VRK3 with `HGN`, ILK with altered DFG) are explicitly flagged as biological exceptions rather than clerical errors.
    """)

    st.markdown("---")

    st.subheader("3. Analytical Methods Overview")

    col_m1, col_m2 = st.columns([1, 1])

    with col_m1:
        st.markdown("""
        #### Method A: Sequence Similarity Baseline
        - Pairwise alignment of query proteins against high-confidence reference kinases using affine gap penalties.
        - Quantifies:
          - Best matching reference accession
          - Sequence identity percentage
          - Query alignment coverage
          - Functional class concordance (e.g. Tyrosine kinase vs Serine/Threonine kinase).
        
        #### Method B & C: ESM-2 Language Model & Anomaly Detection
        - Pretrained Evolutionary Scale Modeling transformer (**ESM-2** `esm2_t6_8M_UR50D` / `esm2_t12_35M_UR50D`).
        - Tokenizes amino acid sequences and generates per-residue representations.
        - Calculates mean-pooled 320-dimensional representations, with sliding window pooling for long proteins.
        - Evaluates distance in the ESM-2 manifold against reference clusters using **centroid cosine distance** and **$k$-Nearest Neighbors ($k$-NN)** neighborhood density.
        """)

    with col_m2:
        st.markdown("""
        #### Method D: Kinase Biological Feature Checks
        - Scans query sequences for canonical and variant patterns of the VAIK, HRD, and DFG motifs.
        - Enforces spatial ordering constraints ($VAIK < HRD < DFG$).
        - Produces an interpretable catalytic integrity score ($0.0$ to $1.0$).
        
        #### Method E: Annotation Provenance Analysis
        - Evaluates Evidence and Conclusion Ontology (**ECO**) codes and Swiss-Prot review status:
          - **Tier 1 (Experimental):** Direct enzyme assays, PubMed citations (e.g., `ECO:0000269`).
          - **Tier 2 (Phylogenetic / Homology):** Manually curated sequence similarity (e.g., `ECO:0000250`).
          - **Tier 3 (Computational Unreviewed):** UniRule, HAMAP, InterPro automated predictions (e.g., `ECO:0000256`).
          - **Tier 4 (Author Statement):** Unspecified curator inferences.
        """)

    st.markdown("---")

    st.subheader("4. Evidence-Aware Contradiction Scoring Formula")
    st.markdown(r"""
    Rather than relying on an opaque machine learning score, the Atlas calculates an interpretable composite contradiction score $S \in [0.0, 1.0]$:
    
    $$S = 0.35 \cdot A_{\text{emb}} + 0.25 \cdot A_{\text{sim}} + 0.25 \cdot A_{\text{feat}} + 0.15 \cdot P_{\text{prov}}$$
    
    Where:
    - $A_{\text{emb}}$: ESM-2 embedding manifold anomaly score.
    - $A_{\text{sim}}$: Sequence dissimilarity and label discordance penalty.
    - $A_{\text{feat}}$: Catalytic motif disruption score ($1.0 - \text{integrity}$).
    - $P_{\text{prov}}$: Annotation provenance uncertainty penalty.
    
    **Review Priority Tiers:**
    - **HIGH Priority** ($S \ge 0.65$): Multiple orthogonal signals indicate substantial divergence or missing catalytic features.
    - **MODERATE Priority** ($S \ge 0.40$): Single-signal divergence or atypical pseudokinase variants requiring inspection.
    - **LOW Priority** ($S < 0.40$): Mutually congruent evidence across sequence, features, and annotations.
    
    > **Scientific Safeguards:**
    > 1. *Low annotation confidence alone cannot trigger a HIGH priority flag if sequence features and embeddings are canonical.*
    > 2. *An unusual embedding alone cannot prove that a functional label is wrong; it is labeled as a divergent variant candidate.*
    > 3. *Natural biological exceptions (pseudokinases) are separated from ordinary suspected annotation conflicts. Contradiction scores serve as diagnostic divergence metrics and do not establish that an annotation is incorrect.*
    """)

    st.markdown("---")

    st.subheader("5. Controlled Benchmark Construction")
    st.markdown("""
    To avoid circular evaluation and ensure rigorous validation:
    - **Category A (Reference Kinases):** Fully characterized human kinases with direct experimental assay evidence.
    - **Category B (Natural Exceptions):** Documented pseudokinases (e.g., VRK3, ILK) and non-canonical kinases.
    - **Category C (Controlled Synthetic Perturbations):**
      - Knockouts of catalytic Lysine (K $\\rightarrow$ A in VAIK) or catalytic Aspartate (D $\\rightarrow$ A in HRD/DFG).
      - Label swaps (exchanging Tyrosine kinase labels with Serine/Threonine kinase labels).
      - Unaltered controls.
    
    All synthetic test cases are tagged with random seeds and **strictly quarantined** from the real database records.
    """)
