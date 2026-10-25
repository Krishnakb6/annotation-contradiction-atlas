"""
Configuration management for The Annotation Contradiction Atlas.
Centralizes paths, model hyperparameters, UniProt endpoints, and scoring thresholds.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Any

# Root directory
PROJECT_ROOT = Path(__file__).resolve().parent

# Directory locations
DATA_DIR = PROJECT_ROOT / os.getenv("ATLAS_DATA_DIR", "data")
CACHE_DIR = DATA_DIR / "cache"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
BENCHMARK_DIR = DATA_DIR / "benchmark"
ARTIFACTS_DIR = PROJECT_ROOT / os.getenv("ATLAS_ARTIFACTS_DIR", "artifacts")

# Ensure required local directories exist
for path in [DATA_DIR, CACHE_DIR, EMBEDDINGS_DIR, BENCHMARK_DIR, ARTIFACTS_DIR]:
    path.mkdir(parents=True, exist_ok=True)

# Database
DB_FILE = DATA_DIR / "contradiction_atlas.db"
DEFAULT_DB_URL = f"sqlite:///{DB_FILE.as_posix()}"
DATABASE_URL = os.getenv("ATLAS_DB_URL", DEFAULT_DB_URL)

# Metadata
PROJECT_TITLE = "The Annotation Contradiction Atlas"
PROJECT_SUBTITLE = "An Evidence-Aware Database for Detecting Potentially Misannotated Protein Kinase Functions"
TEAM_MEMBERS: List[str] = []

# UniProt REST API
UNIPROT_BASE_URL = os.getenv("ATLAS_UNIPROT_API_URL", "https://rest.uniprot.org")
UNIPROT_SEARCH_ENDPOINT = f"{UNIPROT_BASE_URL}/uniprotkb/search"
UNIPROT_STREAM_ENDPOINT = f"{UNIPROT_BASE_URL}/uniprotkb/stream"
DEFAULT_TAXONOMY_ID = 9606  # Homo sapiens
DEFAULT_TARGET_FAMILY = "protein kinase"
DEFAULT_QUERY_REVIEWED = (
    '(taxonomy_id:9606) AND (reviewed:true) AND ('
    'family:"protein kinase" OR keyword:"Kinase [KW-0418]" OR ec:2.7.10.* OR ec:2.7.11.*)'
)
DEFAULT_MAX_RECORDS = 600

# Protein Language Model
# Default to 8M or 35M compact model for reliable local CPU/GPU execution
DEFAULT_ESM_MODEL = os.getenv("ATLAS_ESM_MODEL_NAME", "facebook/esm2_t6_8M_UR50D")
FALLBACK_ESM_MODEL = "facebook/esm2_t12_35M_UR50D"
MAX_SEQUENCE_LENGTH = int(os.getenv("ATLAS_MAX_SEQUENCE_LENGTH", "1024"))
BATCH_SIZE = int(os.getenv("ATLAS_BATCH_SIZE", "8"))
RANDOM_SEED = int(os.getenv("ATLAS_RANDOM_SEED", "42"))

# Conserved Kinase Motifs
# Standard catalytic features:
# 1. VAIK motif (subdomain II): Lysine binds alpha and beta phosphates of ATP
# 2. HRD motif (subdomain VIB): Catalytic aspartate accepts proton during phosphotransfer
# 3. DFG motif (subdomain VII): Aspartate coordinates Mg2+ ion for ATP binding
KINASE_MOTIFS: Dict[str, Dict[str, Any]] = {
    "VAIK": {
        "name": "VAIK / β3-Lysine",
        "subdomain": "II",
        "regex": r"[LIVMAFY][AVILMF][IVATC][KR]",
        "core_residue": "K",
        "description": "ATP-phosphate orienting lysine (usually VAIK or closely related hydrophobic-aliphatic-K)",
        "essential": True,
    },
    "HRD": {
        "name": "HRD / Catalytic Loop",
        "subdomain": "VI B",
        "regex": r"[HYF][RKN][DSANG]",
        "core_residue": "D",
        "description": "Catalytic base aspartate assisting phosphotransfer (HRD or variants in atypicals/pseudokinases)",
        "essential": True,
    },
    "DFG": {
        "name": "DFG / Activation Loop Start",
        "subdomain": "VII",
        "regex": r"[DNE][FYSW][GSA]",
        "core_residue": "D",
        "description": "Metal-binding (Mg2+) motif (DFG motif; coordinates ATP-phosphate chelation)",
        "essential": True,
    },
}

# Evidence Codes mapping (Evidence & Conclusion Ontology - ECO & UniProt)
# Differentiates experimental support, high-throughput, phylogenetic/computational inference, and uncurated
EVIDENCE_CATEGORIES = {
    "EXPERIMENTAL": [
        "ECO:0000269",  # PubMed direct experimental evidence
        "ECO:0000314",  # Direct assay
        "ECO:0000353",  # Physical interaction
        "ECO:0000268",  # Expression pattern
        "EXP", "IDA", "IPI", "IMP", "IGI", "IEP"
    ],
    "PHYLOGENETIC_CURATED": [
        "ECO:0000250",  # Sequence similarity to experimentally characterized
        "ECO:0000315",  # Mutant phenotype
        "ECO:0000316",  # Genetic interaction
        "IBA", "IBD", "IKR", "IRD", "ISS", "ISO", "ISA", "ISM", "IGC"
    ],
    "COMPUTATIONAL_UNREVIEWED": [
        "ECO:0000256",  # Rule-based automatic annotation (HAMAP/UniRule)
        "ECO:0000259",  # InterPro automatic
        "ECO:0000213",  # Combinatorial feature inference
        "IEA", "RCA"
    ],
    "AUTHOR_STATEMENT": [
        "ECO:0000303",  # Non-traceable author statement
        "ECO:0000305",  # Curator inference
        "ECO:0000304",  # Traceable author statement
        "TAS", "NAS", "IC"
    ]
}

# Contradiction Scoring Weights (normalized sum to 1.0)
WEIGHTS = {
    "embedding_anomaly": 0.35,
    "sequence_similarity": 0.25,
    "kinase_feature": 0.25,
    "provenance_penalty": 0.15,
}

# Review Priority Thresholds
PRIORITY_THRESHOLDS = {
    "HIGH": 0.65,
    "MODERATE": 0.40,
    "LOW": 0.0,
}
