"""
SQLAlchemy models for The Annotation Contradiction Atlas.
Strictly normalized relational schema representing proteins, functional annotations,
provenance, sequence features, embeddings, model anomaly results, review flags,
benchmark ground truth, and analysis execution runs.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Protein(Base):
    """
    Core human protein kinase entity.
    Stores stable accession, primary sequence, verification status, and retrieval source.
    """
    __tablename__ = "proteins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    accession = Column(String(32), unique=True, nullable=False, index=True)
    protein_name = Column(String(255), nullable=False)
    gene_name = Column(String(64), nullable=True, index=True)
    organism = Column(String(128), nullable=False, default="Homo sapiens")
    taxonomy_id = Column(Integer, nullable=False, default=9606)
    sequence = Column(Text, nullable=False)
    sequence_length = Column(Integer, nullable=False)
    reviewed = Column(Boolean, nullable=False, default=True, index=True)
    protein_existence = Column(String(64), nullable=True)
    source_url = Column(String(255), nullable=False)
    retrieval_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    annotations = relationship(
        "FunctionAnnotation", back_populates="protein", cascade="all, delete-orphan"
    )
    family_memberships = relationship(
        "ProteinFamilyMembership", back_populates="protein", cascade="all, delete-orphan"
    )
    sequence_features = relationship(
        "SequenceFeature", back_populates="protein", cascade="all, delete-orphan"
    )
    embeddings = relationship(
        "EmbeddingRecord", back_populates="protein", cascade="all, delete-orphan"
    )
    model_results = relationship(
        "ModelResult", back_populates="protein", cascade="all, delete-orphan"
    )
    review_flags = relationship(
        "ReviewFlag", back_populates="protein", cascade="all, delete-orphan"
    )
    benchmark_cases = relationship(
        "BenchmarkCase", back_populates="protein", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_protein_accession_reviewed", "accession", "reviewed"),
    )

    def __repr__(self) -> str:
        return f"<Protein(id={self.id}, accession='{self.accession}', gene='{self.gene_name}', len={self.sequence_length})>"


class FunctionAnnotation(Base):
    """
    Functional annotation records associated with a protein, tracking evidence and provenance.
    """
    __tablename__ = "function_annotations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    protein_id = Column(Integer, ForeignKey("proteins.id", ondelete="CASCADE"), nullable=False, index=True)
    functional_label = Column(String(255), nullable=False, index=True)
    annotation_type = Column(String(64), nullable=False)  # e.g., catalytic_activity, function_description, ec_number
    evidence_code = Column(String(64), nullable=True)     # e.g., ECO:0000269, ECO:0000250, ECO:0000256
    evidence_category = Column(String(64), nullable=False, default="UNSPECIFIED")  # EXPERIMENTAL, PHYLOGENETIC_CURATED, COMPUTATIONAL_UNREVIEWED, AUTHOR_STATEMENT
    supporting_reference = Column(String(255), nullable=True)  # PubMed ID, UniRule ID, etc.
    source_field = Column(String(128), nullable=True)
    provenance_details = Column(Text, nullable=True)

    protein = relationship("Protein", back_populates="annotations")

    def __repr__(self) -> str:
        return f"<FunctionAnnotation(id={self.id}, protein_id={self.protein_id}, label='{self.functional_label[:30]}', cat='{self.evidence_category}')>"


class ProteinFamily(Base):
    """
    Kinase family or domain classification (e.g. Protein kinase domain, AGC, CAMK, TK).
    """
    __tablename__ = "protein_families"

    id = Column(Integer, primary_key=True, autoincrement=True)
    family_name = Column(String(128), nullable=False, index=True)
    classification_source = Column(String(64), nullable=False)  # e.g. Pfam, InterPro, UniProt
    external_identifier = Column(String(64), nullable=True, index=True)  # e.g. PF00069, IPR000719
    description = Column(Text, nullable=True)

    memberships = relationship(
        "ProteinFamilyMembership", back_populates="family", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("family_name", "classification_source", "external_identifier", name="uq_family_source"),
    )

    def __repr__(self) -> str:
        return f"<ProteinFamily(id={self.id}, name='{self.family_name}', ext='{self.external_identifier}')>"


class ProteinFamilyMembership(Base):
    """
    Link table between proteins and kinase families/domains.
    """
    __tablename__ = "protein_family_memberships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    protein_id = Column(Integer, ForeignKey("proteins.id", ondelete="CASCADE"), nullable=False, index=True)
    family_id = Column(Integer, ForeignKey("protein_families.id", ondelete="CASCADE"), nullable=False, index=True)
    membership_source = Column(String(64), nullable=False)
    membership_evidence = Column(String(128), nullable=True)

    protein = relationship("Protein", back_populates="family_memberships")
    family = relationship("ProteinFamily", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("protein_id", "family_id", name="uq_protein_family"),
    )


class SequenceFeature(Base):
    """
    Biological sequence features: conserved catalytic motifs (VAIK, HRD, DFG),
    catalytic loops, activation segments, or pseudokinase deviations.
    """
    __tablename__ = "sequence_features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    protein_id = Column(Integer, ForeignKey("proteins.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_name = Column(String(64), nullable=False, index=True)  # e.g. VAIK, HRD, DFG
    start_position = Column(Integer, nullable=True)
    end_position = Column(Integer, nullable=True)
    detected_sequence = Column(String(64), nullable=True)
    detected_status = Column(String(32), nullable=False)  # canonical, variant, absent, indeterminate
    detection_method = Column(String(64), nullable=False)  # regex_heuristic, alignment_profile
    expected_context = Column(String(128), nullable=True)
    evidence_or_limitation = Column(Text, nullable=True)

    protein = relationship("Protein", back_populates="sequence_features")

    def __repr__(self) -> str:
        return f"<SequenceFeature(protein_id={self.protein_id}, motif='{self.feature_name}', status='{self.detected_status}')>"


class EmbeddingRecord(Base):
    """
    Metadata pointer to dense protein language model embedding artifacts.
    Stored on disk in .npy binary format to keep relational DB fast and lean.
    """
    __tablename__ = "embedding_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    protein_id = Column(Integer, ForeignKey("proteins.id", ondelete="CASCADE"), nullable=False, index=True)
    model_name = Column(String(128), nullable=False)
    model_version = Column(String(64), nullable=False)
    pooling_method = Column(String(32), nullable=False, default="mean_pool")
    embedding_dim = Column(Integer, nullable=False)
    artifact_path = Column(String(255), nullable=False)
    computation_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    preprocessing_details = Column(Text, nullable=True)

    protein = relationship("Protein", back_populates="embeddings")

    __table_args__ = (
        UniqueConstraint("protein_id", "model_name", "model_version", name="uq_protein_model_embedding"),
    )


class AnalysisRun(Base):
    """
    Tracks computational runs, configurations, seeds, and execution telemetry.
    """
    __tablename__ = "analysis_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_identifier = Column(String(64), unique=True, nullable=False, index=True)
    dataset_version = Column(String(64), nullable=False)
    configuration = Column(Text, nullable=False)  # JSON serialized
    model_versions = Column(Text, nullable=False)  # JSON serialized
    random_seed = Column(Integer, nullable=False, default=42)
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    completion_time = Column(DateTime, nullable=True)
    run_status = Column(String(32), nullable=False, default="RUNNING")  # RUNNING, COMPLETED, FAILED
    evaluation_summary = Column(Text, nullable=True)  # JSON serialized metrics

    model_results = relationship(
        "ModelResult", back_populates="analysis_run", cascade="all, delete-orphan"
    )
    review_flags = relationship(
        "ReviewFlag", back_populates="analysis_run", cascade="all, delete-orphan"
    )


class ModelResult(Base):
    """
    Output of individual analytical methods (sequence similarity baseline,
    ESM-2 embedding anomaly, motif checks) for each protein in an analysis run.
    """
    __tablename__ = "model_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    protein_id = Column(Integer, ForeignKey("proteins.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    method_name = Column(String(64), nullable=False, index=True)  # sequence_similarity, esm2_anomaly, motif_integrity
    model_version = Column(String(64), nullable=False)
    anomaly_score = Column(Float, nullable=False)
    similarity_score = Column(Float, nullable=True)
    reference_protein_accession = Column(String(32), nullable=True)
    threshold = Column(Float, nullable=True)
    is_outlier = Column(Boolean, nullable=False, default=False)
    result_explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    protein = relationship("Protein", back_populates="model_results")
    analysis_run = relationship("AnalysisRun", back_populates="model_results")


class ReviewFlag(Base):
    """
    Multi-evidence synthesized contradiction flags for prioritization.
    Explicitly articulates potential inconsistency, reason, and scientific limitations.
    """
    __tablename__ = "review_flags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    protein_id = Column(Integer, ForeignKey("proteins.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    review_priority = Column(String(32), nullable=False, index=True)  # LOW, MODERATE, HIGH
    contradiction_score = Column(Float, nullable=False, default=0.0)
    flag_reason = Column(Text, nullable=False)
    supporting_evidence_summary = Column(Text, nullable=False)
    contradictory_signals = Column(Text, nullable=False)
    limitations = Column(Text, nullable=False)
    review_status = Column(String(32), nullable=False, default="PENDING")  # PENDING, INSPECTED, CONFIRMED_ANOMALY, FALSE_ALARM
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    protein = relationship("Protein", back_populates="review_flags")
    analysis_run = relationship("AnalysisRun", back_populates="review_flags")

    __table_args__ = (
        Index("idx_flag_priority_protein", "review_priority", "protein_id"),
    )


class BenchmarkCase(Base):
    """
    Ground truth and controlled evaluation benchmark instances:
    - Category A: High-confidence reference proteins
    - Category B: Naturally occurring cases / pseudokinases
    - Category C: Controlled synthetic perturbations
    """
    __tablename__ = "benchmark_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    protein_id = Column(Integer, ForeignKey("proteins.id", ondelete="CASCADE"), nullable=True, index=True)
    synthetic_identifier = Column(String(64), nullable=True, unique=True)
    case_type = Column(String(64), nullable=False, index=True)  # CATEGORY_A_REFERENCE, CATEGORY_B_NATURAL_EXCEPTION, CATEGORY_C_SYNTHETIC
    ground_truth_category = Column(String(64), nullable=False)  # CONGRUENT, INCONSISTENT_CATALYTIC, LABEL_MISMATCH, NATURAL_PSEUDOKINASE
    is_inconsistent = Column(Boolean, nullable=False)  # True = contradiction target, False = consistent reference
    label_rationale = Column(Text, nullable=False)
    source_reference = Column(String(255), nullable=True)
    synthetic_modification_details = Column(Text, nullable=True)  # JSON
    dataset_split = Column(String(32), nullable=False, default="TEST")  # REFERENCE, CALIBRATION, TEST
    random_seed = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    protein = relationship("Protein", back_populates="benchmark_cases")
