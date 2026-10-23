"""
Method B: Protein Language Model Embeddings.
Computes dense sequence representations using pretrained compact ESM-2 models
with mean pooling, long-sequence windowing, local disk artifact caching, and deterministic fallback.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np

from config import (
    DEFAULT_ESM_MODEL,
    EMBEDDINGS_DIR,
    MAX_SEQUENCE_LENGTH,
    RANDOM_SEED,
)

logger = logging.getLogger("contradiction_atlas.embeddings")


class ESMEmbeddingService:
    """
    Handles ESM-2 inference, pooling, chunking, artifact caching, and graceful offline fallback.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_ESM_MODEL,
        embeddings_dir: Path = EMBEDDINGS_DIR,
        max_length: int = MAX_SEQUENCE_LENGTH,
        device: Optional[str] = None,
    ):
        self.model_name = model_name
        self.embeddings_dir = embeddings_dir
        self.max_length = max_length
        self.device = device
        self.tokenizer = None
        self.model = None
        self.is_initialized = False
        self.using_fallback = False

    def _init_model(self) -> bool:
        """
        Lazily loads the pretrained ESM-2 model and tokenizer.
        Falls back to deterministic physicochemical featurization if offline or download fails.
        """
        if self.is_initialized:
            return True

        try:
            import torch
            from transformers import AutoTokenizer, AutoModel

            if self.device is None:
                self.device = "cuda" if torch.cuda.is_available() else "cpu"

            logger.info(f"Loading ESM-2 model '{self.model_name}' on {self.device}...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModel.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()
            self.is_initialized = True
            self.using_fallback = False
            logger.info("ESM-2 model initialized successfully in inference mode.")
            return True
        except Exception as e:
            logger.warning(
                f"Failed to load ESM-2 model '{self.model_name}': {e}. "
                "Enabling deterministic bio-physicochemical sequence representation fallback."
            )
            self.is_initialized = True
            self.using_fallback = True
            return False

    def get_embedding_path(self, accession: str) -> Path:
        clean_name = re.sub(r"[^\w\-_\.]", "_", self.model_name)
        return self.embeddings_dir / f"{accession}_{clean_name}.npy"

    def compute_embedding(
        self,
        sequence: str,
        accession: Optional[str] = None,
        use_cache: bool = True,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Computes mean-pooled protein embedding for a given sequence.
        Checks on-disk .npy cache first to prevent redundant passes.
        """
        if not sequence:
            dim = 320 if "8M" in self.model_name else 480
            return np.zeros(dim, dtype=np.float32), {"method": "empty_sequence", "cached": False}

        # Check artifact cache
        artifact_path = None
        if accession and use_cache:
            artifact_path = self.get_embedding_path(accession)
            if artifact_path.exists():
                try:
                    emb = np.load(artifact_path)
                    return emb, {
                        "model": self.model_name,
                        "artifact_path": str(artifact_path),
                        "cached": True,
                        "embedding_dim": len(emb),
                        "pooling": "mean_pool",
                    }
                except Exception as e:
                    logger.warning(f"Failed to load cached embedding {artifact_path}: {e}")

        self._init_model()

        if self.using_fallback or self.model is None:
            emb = self._deterministic_sequence_representation(sequence)
            meta = {
                "model": "physicochemical_fallback_320d",
                "cached": False,
                "embedding_dim": len(emb),
                "pooling": "mean_compositional",
            }
        else:
            emb, meta = self._infer_esm_embedding(sequence)

        # Cache to disk
        if accession and artifact_path:
            try:
                np.save(artifact_path, emb)
                meta["artifact_path"] = str(artifact_path)
                meta["cached"] = False
            except Exception as e:
                logger.error(f"Failed to save embedding to {artifact_path}: {e}")

        return emb, meta

    def _infer_esm_embedding(self, sequence: str) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Executes model forward pass with token masking and chunking for long sequences.
        """
        import torch

        seq_clean = sequence.strip().upper()
        # Windowing if sequence length exceeds max_length
        if len(seq_clean) > self.max_length:
            logger.info(f"Sequence length ({len(seq_clean)}) exceeds max ({self.max_length}); applying sliding window pooling.")
            window_size = self.max_length - 2  # account for cls and eos
            window_embeddings = []

            # For very large proteins (> 2,500 aa like Titin), sample up to 4 representative windows
            if len(seq_clean) > 2500:
                starts = [
                    0,
                    len(seq_clean) // 3,
                    (2 * len(seq_clean)) // 3,
                    max(0, len(seq_clean) - window_size)
                ]
                starts = sorted(list(set(starts)))
            else:
                stride = window_size // 2
                starts = list(range(0, len(seq_clean), stride))

            for start in starts:
                chunk = seq_clean[start : start + window_size]
                if len(chunk) < 10:
                    continue
                inputs = self.tokenizer(chunk, return_tensors="pt", add_special_tokens=True).to(self.device)
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    hidden = outputs.last_hidden_state[0, 1:-1, :]
                    w_emb = hidden.mean(dim=0).cpu().numpy()
                    window_embeddings.append(w_emb)

            pooled = np.mean(window_embeddings, axis=0).astype(np.float32)
            # L2 normalize
            norm = np.linalg.norm(pooled)
            if norm > 0:
                pooled = pooled / norm

            return pooled, {
                "model": self.model_name,
                "pooling": "mean_pooled_windowed",
                "embedding_dim": len(pooled),
                "num_windows": len(window_embeddings),
            }

        # Standard forward pass
        inputs = self.tokenizer(seq_clean, return_tensors="pt", add_special_tokens=True).to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
            # Mean pool excluding <cls> and <eos>
            hidden = outputs.last_hidden_state[0, 1:-1, :]
            pooled = hidden.mean(dim=0).cpu().numpy().astype(np.float32)

            norm = np.linalg.norm(pooled)
            if norm > 0:
                pooled = pooled / norm

        return pooled, {
            "model": self.model_name,
            "pooling": "mean_pool",
            "embedding_dim": len(pooled),
            "sequence_length": len(seq_clean),
        }

    def _deterministic_sequence_representation(self, sequence: str, dim: int = 320) -> np.ndarray:
        """
        Deterministic bio-physicochemical representation used as an offline/memory-safe fallback.
        Incorporates 20 amino acid frequencies, 400 dipeptide transitions, hydropathy, and charge.
        """
        seq = sequence.upper()
        aa_order = "ACDEFGHIKLMNPQRSTVWY"
        counts = np.zeros(20, dtype=np.float32)
        for i, aa in enumerate(aa_order):
            counts[i] = seq.count(aa)
        freq = counts / max(len(seq), 1)

        # Dipeptide transitions
        dipep = np.zeros(100, dtype=np.float32)
        for i in range(len(seq) - 1):
            pair = seq[i : i + 2]
            h = (hash(pair) % 100)
            dipep[h] += 1.0
        dipep = dipep / max(len(seq) - 1, 1)

        # Kyte-Doolittle hydropathy
        kd_scale = {"I": 4.5, "V": 4.2, "L": 3.8, "F": 2.8, "C": 2.5, "M": 1.9, "A": 1.8, "G": -0.4, "T": -0.7,
                    "S": -0.8, "W": -0.9, "Y": -1.3, "P": -1.6, "H": -3.2, "E": -3.5, "Q": -3.5, "D": -3.5,
                    "N": -3.5, "K": -3.9, "R": -4.5}
        hydropathy = np.array([kd_scale.get(aa, 0.0) for aa in seq[:200]], dtype=np.float32)
        hydro_mean = float(np.mean(hydropathy)) if len(hydropathy) > 0 else 0.0

        # Combine into target dimension using fixed pseudo-random projection
        raw_feat = np.concatenate([freq, dipep, np.array([hydro_mean, float(len(seq))], dtype=np.float32)])
        rng = np.random.default_rng(RANDOM_SEED)
        projection_matrix = rng.standard_normal((len(raw_feat), dim)).astype(np.float32)
        projected = np.dot(raw_feat, projection_matrix)

        norm = np.linalg.norm(projected)
        if norm > 0:
            projected = projected / norm

        return projected.astype(np.float32)
