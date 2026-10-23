"""
Data Access Repositories for The Annotation Contradiction Atlas.
Encapsulates CRUD, search, aggregation, and atomic transaction routines.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, or_

from database.models import (
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


class ProteinRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert(self, data: Dict[str, Any]) -> Protein:
        """
        Create or update a protein record by UniProt accession.
        Prevents duplicate records upon refreshed imports.
        """
        accession = data["accession"].strip().upper()
        protein = self.session.query(Protein).filter(Protein.accession == accession).first()
        if not protein:
            protein = Protein(
                accession=accession,
                protein_name=data.get("protein_name", "Unknown kinase"),
                gene_name=data.get("gene_name"),
                organism=data.get("organism", "Homo sapiens"),
                taxonomy_id=data.get("taxonomy_id", 9606),
                sequence=data.get("sequence", ""),
                sequence_length=len(data.get("sequence", "")),
                reviewed=data.get("reviewed", True),
                protein_existence=data.get("protein_existence"),
                source_url=data.get("source_url", f"https://www.uniprot.org/uniprotkb/{accession}/entry"),
                retrieval_timestamp=data.get("retrieval_timestamp", datetime.utcnow()),
            )
            self.session.add(protein)
            self.session.flush()
        else:
            # Update fields
            protein.protein_name = data.get("protein_name", protein.protein_name)
            protein.gene_name = data.get("gene_name", protein.gene_name)
            protein.sequence = data.get("sequence", protein.sequence)
            protein.sequence_length = len(protein.sequence)
            protein.reviewed = data.get("reviewed", protein.reviewed)
            protein.protein_existence = data.get("protein_existence", protein.protein_existence)
            protein.source_url = data.get("source_url", protein.source_url)
            protein.retrieval_timestamp = datetime.utcnow()
            self.session.flush()
        return protein

    def get_by_accession(self, accession: str, eager: bool = False) -> Optional[Protein]:
        q = self.session.query(Protein).filter(Protein.accession == accession.strip().upper())
        if eager:
            q = q.options(
                joinedload(Protein.annotations),
                joinedload(Protein.sequence_features),
                joinedload(Protein.review_flags),
                joinedload(Protein.family_memberships).joinedload(ProteinFamilyMembership.family),
            )
        return q.first()

    def get_by_id(self, protein_id: int, eager: bool = False) -> Optional[Protein]:
        q = self.session.query(Protein).filter(Protein.id == protein_id)
        if eager:
            q = q.options(
                joinedload(Protein.annotations),
                joinedload(Protein.sequence_features),
                joinedload(Protein.review_flags),
                joinedload(Protein.family_memberships).joinedload(ProteinFamilyMembership.family),
            )
        return q.first()

    def list_proteins(
        self,
        search: Optional[str] = None,
        reviewed_only: Optional[bool] = None,
        priority_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "accession",
    ) -> List[Protein]:
        q = self.session.query(Protein)

        if priority_filter:
            q = q.join(ReviewFlag).filter(ReviewFlag.review_priority == priority_filter)

        if reviewed_only is not None:
            q = q.filter(Protein.reviewed == reviewed_only)

        if search:
            s = f"%{search.strip()}%"
            q = q.filter(
                or_(
                    Protein.accession.ilike(s),
                    Protein.gene_name.ilike(s),
                    Protein.protein_name.ilike(s),
                )
            )

        if order_by == "sequence_length":
            q = q.order_by(desc(Protein.sequence_length))
        elif order_by == "gene_name":
            q = q.order_by(Protein.gene_name.asc())
        else:
            q = q.order_by(Protein.accession.asc())

        return q.slice(offset, offset + limit).all()

    def count_proteins(
        self,
        search: Optional[str] = None,
        reviewed_only: Optional[bool] = None,
        priority_filter: Optional[str] = None,
    ) -> int:
        q = self.session.query(func.count(Protein.id))
        if priority_filter:
            q = q.join(ReviewFlag).filter(ReviewFlag.review_priority == priority_filter)
        if reviewed_only is not None:
            q = q.filter(Protein.reviewed == reviewed_only)
        if search:
            s = f"%{search.strip()}%"
            q = q.filter(
                or_(
                    Protein.accession.ilike(s),
                    Protein.gene_name.ilike(s),
                    Protein.protein_name.ilike(s),
                )
            )
        return q.scalar() or 0

    def get_all_with_sequence(self, limit: Optional[int] = None) -> List[Protein]:
        q = self.session.query(Protein).filter(Protein.sequence != "")
        if limit:
            q = q.limit(limit)
        return q.all()


class AnnotationRepository:
    def __init__(self, session: Session):
        self.session = session

    def replace_annotations(self, protein_id: int, annotations: List[Dict[str, Any]]) -> None:
        self.session.query(FunctionAnnotation).filter(FunctionAnnotation.protein_id == protein_id).delete()
        for ann in annotations:
            record = FunctionAnnotation(
                protein_id=protein_id,
                functional_label=ann.get("functional_label", "Unknown"),
                annotation_type=ann.get("annotation_type", "catalytic_activity"),
                evidence_code=ann.get("evidence_code"),
                evidence_category=ann.get("evidence_category", "UNSPECIFIED"),
                supporting_reference=ann.get("supporting_reference"),
                source_field=ann.get("source_field"),
                provenance_details=ann.get("provenance_details"),
            )
            self.session.add(record)
        self.session.flush()

    def get_by_protein_id(self, protein_id: int) -> List[FunctionAnnotation]:
        return self.session.query(FunctionAnnotation).filter(FunctionAnnotation.protein_id == protein_id).all()


class SequenceFeatureRepository:
    def __init__(self, session: Session):
        self.session = session

    def replace_features(self, protein_id: int, features: List[Dict[str, Any]]) -> None:
        self.session.query(SequenceFeature).filter(SequenceFeature.protein_id == protein_id).delete()
        for f in features:
            record = SequenceFeature(
                protein_id=protein_id,
                feature_name=f["feature_name"],
                start_position=f.get("start_position"),
                end_position=f.get("end_position"),
                detected_sequence=f.get("detected_sequence"),
                detected_status=f.get("detected_status", "indeterminate"),
                detection_method=f.get("detection_method", "regex_heuristic"),
                expected_context=f.get("expected_context"),
                evidence_or_limitation=f.get("evidence_or_limitation"),
            )
            self.session.add(record)
        self.session.flush()

    def get_by_protein_id(self, protein_id: int) -> List[SequenceFeature]:
        return self.session.query(SequenceFeature).filter(SequenceFeature.protein_id == protein_id).all()


class EmbeddingRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert_record(self, data: Dict[str, Any]) -> EmbeddingRecord:
        rec = self.session.query(EmbeddingRecord).filter(
            EmbeddingRecord.protein_id == data["protein_id"],
            EmbeddingRecord.model_name == data["model_name"],
            EmbeddingRecord.model_version == data["model_version"],
        ).first()

        if not rec:
            rec = EmbeddingRecord(
                protein_id=data["protein_id"],
                model_name=data["model_name"],
                model_version=data["model_version"],
                pooling_method=data.get("pooling_method", "mean_pool"),
                embedding_dim=data["embedding_dim"],
                artifact_path=data["artifact_path"],
                computation_timestamp=datetime.utcnow(),
                preprocessing_details=data.get("preprocessing_details"),
            )
            self.session.add(rec)
        else:
            rec.artifact_path = data["artifact_path"]
            rec.embedding_dim = data["embedding_dim"]
            rec.computation_timestamp = datetime.utcnow()
            rec.preprocessing_details = data.get("preprocessing_details")
        self.session.flush()
        return rec

    def get_by_protein_and_model(self, protein_id: int, model_name: str, model_version: str) -> Optional[EmbeddingRecord]:
        return self.session.query(EmbeddingRecord).filter(
            EmbeddingRecord.protein_id == protein_id,
            EmbeddingRecord.model_name == model_name,
            EmbeddingRecord.model_version == model_version,
        ).first()

    def get_all_records_for_model(self, model_name: str) -> List[EmbeddingRecord]:
        return self.session.query(EmbeddingRecord).filter(EmbeddingRecord.model_name == model_name).all()


class ModelResultRepository:
    def __init__(self, session: Session):
        self.session = session

    def save_result(self, data: Dict[str, Any]) -> ModelResult:
        res = ModelResult(
            protein_id=data["protein_id"],
            run_id=data.get("run_id"),
            method_name=data["method_name"],
            model_version=data["model_version"],
            anomaly_score=data["anomaly_score"],
            similarity_score=data.get("similarity_score"),
            reference_protein_accession=data.get("reference_protein_accession"),
            threshold=data.get("threshold"),
            is_outlier=data.get("is_outlier", False),
            result_explanation=data.get("result_explanation"),
            created_at=datetime.utcnow(),
        )
        self.session.add(res)
        self.session.flush()
        return res

    def get_by_protein_id(self, protein_id: int, run_id: Optional[int] = None) -> List[ModelResult]:
        q = self.session.query(ModelResult).filter(ModelResult.protein_id == protein_id)
        if run_id:
            q = q.filter(ModelResult.run_id == run_id)
        return q.all()


class ReviewFlagRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert_flag(self, data: Dict[str, Any]) -> ReviewFlag:
        flag = self.session.query(ReviewFlag).filter(
            ReviewFlag.protein_id == data["protein_id"]
        ).first()

        if not flag:
            flag = ReviewFlag(
                protein_id=data["protein_id"],
                run_id=data.get("run_id"),
                review_priority=data["review_priority"],
                contradiction_score=data.get("contradiction_score", 0.0),
                flag_reason=data["flag_reason"],
                supporting_evidence_summary=data["supporting_evidence_summary"],
                contradictory_signals=data["contradictory_signals"],
                limitations=data["limitations"],
                review_status=data.get("review_status", "PENDING"),
                timestamp=datetime.utcnow(),
            )
            self.session.add(flag)
        else:
            flag.run_id = data.get("run_id", flag.run_id)
            flag.review_priority = data["review_priority"]
            flag.contradiction_score = data.get("contradiction_score", flag.contradiction_score)
            flag.flag_reason = data["flag_reason"]
            flag.supporting_evidence_summary = data["supporting_evidence_summary"]
            flag.contradictory_signals = data["contradictory_signals"]
            flag.limitations = data["limitations"]
            flag.timestamp = datetime.utcnow()
        self.session.flush()
        return flag

    def get_by_protein_id(self, protein_id: int) -> Optional[ReviewFlag]:
        return self.session.query(ReviewFlag).filter(ReviewFlag.protein_id == protein_id).first()

    def list_flags(
        self,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ReviewFlag]:
        q = self.session.query(ReviewFlag).options(joinedload(ReviewFlag.protein))
        if priority:
            q = q.filter(ReviewFlag.review_priority == priority)
        if status:
            q = q.filter(ReviewFlag.review_status == status)
        q = q.order_by(desc(ReviewFlag.contradiction_score))
        return q.slice(offset, offset + limit).all()

    def get_priority_counts(self) -> Dict[str, int]:
        counts = {"HIGH": 0, "MODERATE": 0, "LOW": 0}
        results = self.session.query(
            ReviewFlag.review_priority, func.count(ReviewFlag.id)
        ).group_by(ReviewFlag.review_priority).all()
        for p, count in results:
            if p in counts:
                counts[p] = count
        return counts


class BenchmarkRepository:
    def __init__(self, session: Session):
        self.session = session

    def add_case(self, data: Dict[str, Any]) -> BenchmarkCase:
        case = BenchmarkCase(
            protein_id=data.get("protein_id"),
            synthetic_identifier=data.get("synthetic_identifier"),
            case_type=data["case_type"],
            ground_truth_category=data["ground_truth_category"],
            is_inconsistent=data["is_inconsistent"],
            label_rationale=data["label_rationale"],
            source_reference=data.get("source_reference"),
            synthetic_modification_details=json.dumps(data.get("synthetic_modification_details")) if isinstance(data.get("synthetic_modification_details"), (dict, list)) else data.get("synthetic_modification_details"),
            dataset_split=data.get("dataset_split", "TEST"),
            random_seed=data.get("random_seed"),
            created_at=datetime.utcnow(),
        )
        self.session.add(case)
        self.session.flush()
        return case

    def list_cases(self, case_type: Optional[str] = None, split: Optional[str] = None) -> List[BenchmarkCase]:
        q = self.session.query(BenchmarkCase).options(joinedload(BenchmarkCase.protein))
        if case_type:
            q = q.filter(BenchmarkCase.case_type == case_type)
        if split:
            q = q.filter(BenchmarkCase.dataset_split == split)
        return q.all()

    def clear_synthetic_cases(self) -> int:
        deleted = self.session.query(BenchmarkCase).filter(
            BenchmarkCase.case_type == "CATEGORY_C_SYNTHETIC"
        ).delete()
        self.session.flush()
        return deleted


class AnalysisRunRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_run(self, identifier: str, dataset_version: str, config_dict: Dict[str, Any], seed: int) -> AnalysisRun:
        run = AnalysisRun(
            run_identifier=identifier,
            dataset_version=dataset_version,
            configuration=json.dumps(config_dict),
            model_versions=json.dumps({"esm": config_dict.get("esm_model", "esm2_t6_8M_UR50D")}),
            random_seed=seed,
            start_time=datetime.utcnow(),
            run_status="RUNNING",
        )
        self.session.add(run)
        self.session.flush()
        return run

    def complete_run(self, run_id: int, summary: Dict[str, Any], status: str = "COMPLETED") -> AnalysisRun:
        run = self.session.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        if run:
            run.completion_time = datetime.utcnow()
            run.run_status = status
            run.evaluation_summary = json.dumps(summary)
            self.session.flush()
        return run

    def get_latest_completed_run(self) -> Optional[AnalysisRun]:
        return self.session.query(AnalysisRun).filter(
            AnalysisRun.run_status == "COMPLETED"
        ).order_by(desc(AnalysisRun.completion_time)).first()
