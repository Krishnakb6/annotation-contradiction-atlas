"""
Unit tests for database schema, models, constraints, and repositories.
Uses an in-memory SQLite database to ensure fast, isolated, reproducible execution.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

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
from database.repositories import (
    ProteinRepository,
    AnnotationRepository,
    SequenceFeatureRepository,
    ReviewFlagRepository,
    BenchmarkRepository,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_protein_creation_and_upsert(db_session):
    repo = ProteinRepository(db_session)
    prot_data = {
        "accession": "P00533",
        "protein_name": "Epidermal growth factor receptor",
        "gene_name": "EGFR",
        "organism": "Homo sapiens",
        "taxonomy_id": 9606,
        "sequence": "MRPSGTAGAALLALLAALCPASRALEEKKVCQGTSNKLTQLGTFEDHFLSLQRMFNNCEVVLGNLEITYVQRNYDLSFLKTIQEVAGYVLIALNTVERIPLENLQIIRGNMYYENSYALAVLSNYDANKTGLKELPMRNLQEILHGAVRFSNNPALCNVESIQWRDIVSSDFLSNMSMDFQNHLGSCQKCDPSCPNGSCWGAGEENCQKLTKIICAQQCSGRCRGKSPSDCCHNQCAAGCTGPRESDCLVCRKFRDEATCKDTCPPLMLYNPTTYQMDVNPEGKYSFGATCVKKCPRNYVVTDHGSCVRACGADSYEMEEDGVRKCKKCEGPCRKVCNGIGIGEFKDSLSINATNIKHFKNCTSISGDLHILPVAFRGDSFTHTPPLDPQELDILKTVKEITGFLLIQAWPENRTDLHAFENLEIIRGRTKQHGQFSLAVVSLNITSLGLRSLKEISDGDVIISGNKNLCYANTINWKKLFGTSGQKTKIISNRGENSCKATGQVCHALCSPEGCWGPEPRDCVSCRNVSRGRECVDKCNLLEGEPREFVENSECIQCHPECLPQAMNITCTGRGPDNCIQCAHYIDGPHCVKTCPAGVMGENNTLVWKYADAGHVCHLCHPNCTYGCTGPGLEGCPTNGPKIPSIATGMVGALLLLLVVALGIGLFMRRRHIVRKRTLRRLLQERELVEPLTPSGEAPNQALLRILKETEFKKIKVLGSGAFGTVYKGLWIPEGEKVKIPVAIKVLRENTSPKANKEILDEAYVMASVDNPHVCRLLGICLTSTVQLITQLMPFGCLLDYVREHKDNIGSQYLLNWCVQIAKGMNYLEDRRLVHRDLAARNVLVKTPQHVKITDFGLAKLLGAEEKEYHAEGGKVPIKWMALESILHRIYTHQSDVWSYGVTVWELMTFGSKPYDGIPASEISSILEKGERLPQPPICTIDVYMIMVKCWMIDADSRPKFRELIIEFSKMARDPQRYLVIQGDERMHLPSPTDSNFYRALMDEEDMDDVVDADEYLIPQQGFFSSPSTSRTPLLSSLSATSNNSTVACIDRNGLQSCPIKEDSFLQRYSSDPTGALTEDSIDDTFLPVPEYINQSVPKRPAGSVQNPVYHNQPLNPAPSRDPHYQDPHSTAVGNPEYLNTVQPTCVNSTFDSPAHWAQKGSHQISLDNPDYQQDFFPKEAKPNGIFKGSTAENAEYLRVAPQSSEFIGA",
        "reviewed": True,
        "source_url": "https://www.uniprot.org/uniprotkb/P00533/entry",
    }
    p1 = repo.upsert(prot_data)
    db_session.commit()
    assert p1.id is not None
    assert p1.accession == "P00533"
    assert p1.sequence_length == len(prot_data["sequence"])

    # Upsert with updated name
    prot_data["protein_name"] = "Receptor tyrosine-protein kinase erbB-1"
    p2 = repo.upsert(prot_data)
    db_session.commit()
    assert p2.id == p1.id
    assert p2.protein_name == "Receptor tyrosine-protein kinase erbB-1"


def test_unique_accession_constraint(db_session):
    p1 = Protein(
        accession="P12931",
        protein_name="Proto-oncogene tyrosine-protein kinase Src",
        gene_name="SRC",
        sequence="MGSSKSKPKDPSQRRRSLEPPDSTHHGGFPASQTPNKTAAPDTHRTPSRSFGTVATEPKLFGGFNTSDTVTSPQRAGALAGGVTTFVALYDYESRTETDLSFKKGERLQIVNNTEGDWWLAHSLSTGQTGYIPSNYVAPSDSIQAEEWYFGKITRRESERLLLNAENPRGTFLVRESETTKGAYCLSVSDFDNAKGLNVKHYKIRKLDSGGFYITSRTQFNSLQQLVAYYSKHADGLCHRLTTVCPTSKPQTQGLAKDAWEIPRESLRLEVKLGQGCFGEVWMGTWNGTTRVAIKTLKPGTMSPEAFLQEAQVMKKLRHEKLVQLYAVVSEEPIYIVTEYMSKGSLLDFLKGETGKYLRLPQLVDMAAQIASGMAYVERMNYVHRDLRAANILVGENLVCKVADFGLARLIEDNEYTARQGAKFPIKWTAPEAALYGRFTIKSDVWSFGILLTELTTKGRVPYPGMVNREVLDQVERGYRMPCPPECPESLHDLMCQCWRKEPEERPTFEYLQAFLEDYFTSTEPQYQPGENL",
        sequence_length=536,
        reviewed=True,
        source_url="https://www.uniprot.org/uniprotkb/P12931/entry",
    )
    db_session.add(p1)
    db_session.commit()

    p2 = Protein(
        accession="P12931",  # Duplicate accession
        protein_name="Duplicate Src",
        sequence="MGS...",
        sequence_length=6,
        reviewed=True,
        source_url="https://www.uniprot.org/uniprotkb/P12931/entry",
    )
    db_session.add(p2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_protein_annotations_relationship(db_session):
    repo = ProteinRepository(db_session)
    ann_repo = AnnotationRepository(db_session)

    prot = repo.upsert({
        "accession": "P31749",
        "protein_name": "RAC-alpha serine/threonine-protein kinase",
        "gene_name": "AKT1",
        "sequence": "MSDVAIVKEGWLHKRGEYIKTWRPRYFLLKNDGTFIGYKERPQDVDQREAPLNNFSVAQCQLMKTERPRPNTFIIRCLQWTTVIERTFHVETPEEREEWTTAIQTVADGLKKQEEEEMDFRSGSPSDNSGAEEMEVSLAKPKHRVTMNEFEYLKLLGKGTFGKVILVKEKATGRYYAMKILKKEVIVAKDEVAHTLTENRVLQNSRHPFLTALKYSFQTHDRLCFVMEYANGGELFFHLSRERVFSEDRARFYGAEIVSALDYLHSEKNVVYRDLKLENLMLDKDGHIKITDFGLCKEGIKDGATMKTFCGTPEYLAPEVLEDNDYGRAVDWWGLGVVMYEMMCGRLPFYNQDHEKLFELILMEEIRFPRTLGPEAKSLLSGLLKKDPKQRLGGGSEDAKEIMQHRFFAGIVWQHVYEKKLSPPFKPQVTSETDTRYFDEEFTAQMITITPPDQDDSMECVDSERRPHFPQFSYSASSTA",
        "reviewed": True,
        "source_url": "https://www.uniprot.org/uniprotkb/P31749/entry",
    })
    db_session.commit()

    annotations = [
        {
            "functional_label": "ATP + a protein = ADP + a phosphoprotein",
            "annotation_type": "catalytic_activity",
            "evidence_code": "ECO:0000269",
            "evidence_category": "EXPERIMENTAL",
            "supporting_reference": "PubMed:123456",
        },
        {
            "functional_label": "protein serine/threonine kinase activity",
            "annotation_type": "molecular_function",
            "evidence_code": "ECO:0000314",
            "evidence_category": "EXPERIMENTAL",
        }
    ]
    ann_repo.replace_annotations(prot.id, annotations)
    db_session.commit()

    retrieved = ann_repo.get_by_protein_id(prot.id)
    assert len(retrieved) == 2
    assert retrieved[0].evidence_category == "EXPERIMENTAL"

    # Test cascade delete
    db_session.delete(prot)
    db_session.commit()
    assert len(ann_repo.get_by_protein_id(prot.id)) == 0


def test_review_flag_and_counts(db_session):
    repo = ProteinRepository(db_session)
    flag_repo = ReviewFlagRepository(db_session)

    p1 = repo.upsert({
        "accession": "Q9Y616",
        "protein_name": "Inactive serine/threonine-protein kinase VRK3",
        "gene_name": "VRK3",
        "sequence": "MLPRLQLLAP...",
        "reviewed": True,
        "source_url": "https://www.uniprot.org/uniprotkb/Q9Y616/entry",
    })
    db_session.commit()

    flag_repo.upsert_flag({
        "protein_id": p1.id,
        "review_priority": "HIGH",
        "contradiction_score": 0.78,
        "flag_reason": "Catalytic loop motif HRD altered to HGN, lack of experimental catalytic verification.",
        "supporting_evidence_summary": "Known pseudokinase in VRK family.",
        "contradictory_signals": "Motif mutation HRD->HGN with unreviewed kinase activity annotation.",
        "limitations": "May retain non-catalytic scaffolding role.",
    })
    db_session.commit()

    counts = flag_repo.get_priority_counts()
    assert counts["HIGH"] == 1
    assert counts["MODERATE"] == 0
    assert counts["LOW"] == 0


def test_benchmark_synthetic_isolation(db_session):
    b_repo = BenchmarkRepository(db_session)

    b_repo.add_case({
        "synthetic_identifier": "SYNTH_MUT_001",
        "case_type": "CATEGORY_C_SYNTHETIC",
        "ground_truth_category": "INCONSISTENT_CATALYTIC",
        "is_inconsistent": True,
        "label_rationale": "Engineered K->A mutation in VAIK motif breaking ATP orientation",
        "synthetic_modification_details": {"type": "motif_mutation", "original": "VAIK", "modified": "VAIA"},
        "dataset_split": "TEST",
        "random_seed": 42,
    })
    db_session.commit()

    cases = b_repo.list_cases(case_type="CATEGORY_C_SYNTHETIC")
    assert len(cases) == 1
    assert cases[0].is_inconsistent is True

    deleted = b_repo.clear_synthetic_cases()
    db_session.commit()
    assert deleted == 1
    assert len(b_repo.list_cases(case_type="CATEGORY_C_SYNTHETIC")) == 0
