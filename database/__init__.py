"""
Database package for The Annotation Contradiction Atlas.
"""
from database.connection import get_db, init_db, SessionLocal, engine
from database.models import (
    Base,
    Protein,
    FunctionAnnotation,
    ProteinFamily,
    ProteinFamilyMembership,
    SequenceFeature,
    EmbeddingRecord,
    ModelResult,
    ReviewFlag,
    BenchmarkCase,
    AnalysisRun,
)

__all__ = [
    "get_db",
    "init_db",
    "SessionLocal",
    "engine",
    "Base",
    "Protein",
    "FunctionAnnotation",
    "ProteinFamily",
    "ProteinFamilyMembership",
    "SequenceFeature",
    "EmbeddingRecord",
    "ModelResult",
    "ReviewFlag",
    "BenchmarkCase",
    "AnalysisRun",
]
