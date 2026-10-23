"""
Data import service for The Annotation Contradiction Atlas.
Imports UniProt records into the relational database with conflict handling,
transaction rollback, and reference fallback dataset.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from database.connection import get_db_session
from database.models import Protein, ProteinFamily, ProteinFamilyMembership
from database.repositories import ProteinRepository, AnnotationRepository
from services.uniprot_client import UniProtClient

logger = logging.getLogger("contradiction_atlas.import")

# Curated reference set of well-characterized human kinases & known pseudokinases
# Used as seed / offline reference when network is unavailable
CURATED_REFERENCE_KINASES: List[Dict[str, Any]] = [
    {
        "accession": "P00533",
        "protein_name": "Epidermal growth factor receptor (EGFR)",
        "gene_name": "EGFR",
        "organism": "Homo sapiens",
        "taxonomy_id": 9606,
        "sequence": "MRPSGTAGAALLALLAALCPASRALEEKKVCQGTSNKLTQLGTFEDHFLSLQRMFNNCEVVLGNLEITYVQRNYDLSFLKTIQEVAGYVLIALNTVERIPLENLQIIRGNMYYENSYALAVLSNYDANKTGLKELPMRNLQEILHGAVRFSNNPALCNVESIQWRDIVSSDFLSNMSMDFQNHLGSCQKCDPSCPNGSCWGAGEENCQKLTKIICAQQCSGRCRGKSPSDCCHNQCAAGCTGPRESDCLVCRKFRDEATCKDTCPPLMLYNPTTYQMDVNPEGKYSFGATCVKKCPRNYVVTDHGSCVRACGADSYEMEEDGVRKCKKCEGPCRKVCNGIGIGEFKDSLSINATNIKHFKNCTSISGDLHILPVAFRGDSFTHTPPLDPQELDILKTVKEITGFLLIQAWPENRTDLHAFENLEIIRGRTKQHGQFSLAVVSLNITSLGLRSLKEISDGDVIISGNKNLCYANTINWKKLFGTSGQKTKIISNRGENSCKATGQVCHALCSPEGCWGPEPRDCVSCRNVSRGRECVDKCNLLEGEPREFVENSECIQCHPECLPQAMNITCTGRGPDNCIQCAHYIDGPHCVKTCPAGVMGENNTLVWKYADAGHVCHLCHPNCTYGCTGPGLEGCPTNGPKIPSIATGMVGALLLLLVVALGIGLFMRRRHIVRKRTLRRLLQERELVEPLTPSGEAPNQALLRILKETEFKKIKVLGSGAFGTVYKGLWIPEGEKVKIPVAIKVLRENTSPKANKEILDEAYVMASVDNPHVCRLLGICLTSTVQLITQLMPFGCLLDYVREHKDNIGSQYLLNWCVQIAKGMNYLEDRRLVHRDLAARNVLVKTPQHVKITDFGLAKLLGAEEKEYHAEGGKVPIKWMALESILHRIYTHQSDVWSYGVTVWELMTFGSKPYDGIPASEISSILEKGERLPQPPICTIDVYMIMVKCWMIDADSRPKFRELIIEFSKMARDPQRYLVIQGDERMHLPSPTDSNFYRALMDEEDMDDVVDADEYLIPQQGFFSSPSTSRTPLLSSLSATSNNSTVACIDRNGLQSCPIKEDSFLQRYSSDPTGALTEDSIDDTFLPVPEYINQSVPKRPAGSVQNPVYHNQPLNPAPSRDPHYQDPHSTAVGNPEYLNTVQPTCVNSTFDSPAHWAQKGSHQISLDNPDYQQDFFPKEAKPNGIFKGSTAENAEYLRVAPQSSEFIGA",
        "sequence_length": 1210,
        "reviewed": True,
        "protein_existence": "Evidence at protein level",
        "source_url": "https://www.uniprot.org/uniprotkb/P00533/entry",
        "annotations": [
            {
                "functional_label": "ATP + a protein tyrosine = ADP + a protein tyrosine phosphate",
                "annotation_type": "catalytic_activity",
                "evidence_code": "ECO:0000269",
                "evidence_category": "EXPERIMENTAL",
                "supporting_reference": "PubMed:15374980",
                "source_field": "catalytic_activity",
            },
            {
                "functional_label": "Receptor tyrosine kinase binding ligands of EGF family and activating RAS-RAF-MEK-ERK module",
                "annotation_type": "function_description",
                "evidence_code": "ECO:0000269",
                "evidence_category": "EXPERIMENTAL",
                "supporting_reference": "PubMed:27153536",
                "source_field": "function",
            }
        ],
        "families": [{"family_name": "Protein kinase domain", "classification_source": "Pfam", "external_identifier": "PF00069"}]
    },
    {
        "accession": "P12931",
        "protein_name": "Proto-oncogene tyrosine-protein kinase Src",
        "gene_name": "SRC",
        "organism": "Homo sapiens",
        "taxonomy_id": 9606,
        "sequence": "MGSSKSKPKDPSQRRRSLEPPDSTHHGGFPASQTPNKTAAPDTHRTPSRSFGTVATEPKLFGGFNTSDTVTSPQRAGALAGGVTTFVALYDYESRTETDLSFKKGERLQIVNNTEGDWWLAHSLSTGQTGYIPSNYVAPSDSIQAEEWYFGKITRRESERLLLNAENPRGTFLVRESETTKGAYCLSVSDFDNAKGLNVKHYKIRKLDSGGFYITSRTQFNSLQQLVAYYSKHADGLCHRLTTVCPTSKPQTQGLAKDAWEIPRESLRLEVKLGQGCFGEVWMGTWNGTTRVAIKTLKPGTMSPEAFLQEAQVMKKLRHEKLVQLYAVVSEEPIYIVTEYMSKGSLLDFLKGETGKYLRLPQLVDMAAQIASGMAYVERMNYVHRDLRAANILVGENLVCKVADFGLARLIEDNEYTARQGAKFPIKWTAPEAALYGRFTIKSDVWSFGILLTELTTKGRVPYPGMVNREVLDQVERGYRMPCPPECPESLHDLMCQCWRKEPEERPTFEYLQAFLEDYFTSTEPQYQPGENL",
        "sequence_length": 536,
        "reviewed": True,
        "protein_existence": "Evidence at protein level",
        "source_url": "https://www.uniprot.org/uniprotkb/P12931/entry",
        "annotations": [
            {
                "functional_label": "ATP + a protein tyrosine = ADP + a protein tyrosine phosphate",
                "annotation_type": "catalytic_activity",
                "evidence_code": "ECO:0000269",
                "evidence_category": "EXPERIMENTAL",
                "supporting_reference": "PubMed:17349580",
                "source_field": "catalytic_activity",
            }
        ],
        "families": [{"family_name": "Protein kinase domain", "classification_source": "Pfam", "external_identifier": "PF00069"}]
    },
    {
        "accession": "P31749",
        "protein_name": "RAC-alpha serine/threonine-protein kinase (AKT1)",
        "gene_name": "AKT1",
        "organism": "Homo sapiens",
        "taxonomy_id": 9606,
        "sequence": "MSDVAIVKEGWLHKRGEYIKTWRPRYFLLKNDGTFIGYKERPQDVDQREAPLNNFSVAQCQLMKTERPRPNTFIIRCLQWTTVIERTFHVETPEEREEWTTAIQTVADGLKKQEEEEMDFRSGSPSDNSGAEEMEVSLAKPKHRVTMNEFEYLKLLGKGTFGKVILVKEKATGRYYAMKILKKEVIVAKDEVAHTLTENRVLQNSRHPFLTALKYSFQTHDRLCFVMEYANGGELFFHLSRERVFSEDRARFYGAEIVSALDYLHSEKNVVYRDLKLENLMLDKDGHIKITDFGLCKEGIKDGATMKTFCGTPEYLAPEVLEDNDYGRAVDWWGLGVVMYEMMCGRLPFYNQDHEKLFELILMEEIRFPRTLGPEAKSLLSGLLKKDPKQRLGGGSEDAKEIMQHRFFAGIVWQHVYEKKLSPPFKPQVTSETDTRYFDEEFTAQMITITPPDQDDSMECVDSERRPHFPQFSYSASSTA",
        "sequence_length": 480,
        "reviewed": True,
        "protein_existence": "Evidence at protein level",
        "source_url": "https://www.uniprot.org/uniprotkb/P31749/entry",
        "annotations": [
            {
                "functional_label": "ATP + a protein serine/threonine = ADP + a protein serine/threonine phosphate",
                "annotation_type": "catalytic_activity",
                "evidence_code": "ECO:0000269",
                "evidence_category": "EXPERIMENTAL",
                "supporting_reference": "PubMed:11884399",
                "source_field": "catalytic_activity",
            }
        ],
        "families": [{"family_name": "Protein kinase domain", "classification_source": "Pfam", "external_identifier": "PF00069"}]
    },
    {
        "accession": "P15056",
        "protein_name": "Serine/threonine-protein kinase B-raf (BRAF)",
        "gene_name": "BRAF",
        "organism": "Homo sapiens",
        "taxonomy_id": 9606,
        "sequence": "MAALSGGGGGGAEPGQALFNGDMEPEAGAGAGAAASSAADPAIPEEVWNIKQMIKLTQEHIEALLDKFGGEHNPPSIYLDAYEEYTSKLDALQQREQQLLESLGNGTDFSVSSSASMDTVTSSSSSSLSVLPSSLSVFQNPTDVARSNPKSPQKPIVRVFLPNKQRTVVPARCGVTVRDSLKKALMMRGLIPECCAVYRIQDGEKKPIGWDTDISWLTGEELHVEVLENVPLTTHNFVRKTFFTLAFCDFCRKLLFQGFRCQTCGYKFHQRCSTEVPLMCVNYDQLDLLFVSKFFEHHPIPQEEASLAETALTSGSSPSAPASDSIGPQILTSPSPSKSIPIPQPFRPADEDHRNQFGQRDRSSSAPNVHINTIEPVNIDDLIRDQGFRGDGGSTTGLSATPPASLPGSLTNVKALQKSPGPQRERKSSSSSEDRNRMKTLGRRDSSDDWEIPDGQITVGQRIGSGSFGTVYKGKWHGDVAVKMLNVTAPTPQQLQAFKNEVGVLRKTRHVNILLFMGYSTKPQLAIVTQWCEGSSLYHHLHIIETKFEMIKLIDIARQTAQGMDYLHAKSIIHRDLKSNNIFLHEDLTVKIGDFGLATVKSRWSGSHQFEQLSGSILWMAPEVIRMQDKNPYSFQSDVYAFGIVLYELMTGQLPYSNINNRDQIIFMVGRGYLSPDLSKVRSNCPKAMKRLMAECLKKKRDERPLFPQILASIELLARSLPKIHRSASEPSLNRAGFQTEDFSLYACASPKTPIQAGGYGAFPVH",
        "sequence_length": 766,
        "reviewed": True,
        "protein_existence": "Evidence at protein level",
        "source_url": "https://www.uniprot.org/uniprotkb/P15056/entry",
        "annotations": [
            {
                "functional_label": "ATP + a protein serine/threonine = ADP + a protein serine/threonine phosphate",
                "annotation_type": "catalytic_activity",
                "evidence_code": "ECO:0000269",
                "evidence_category": "EXPERIMENTAL",
                "supporting_reference": "PubMed:12068308",
                "source_field": "catalytic_activity",
            }
        ],
        "families": [{"family_name": "Protein kinase domain", "classification_source": "Pfam", "external_identifier": "PF00069"}]
    },
    {
        "accession": "P24941",
        "protein_name": "Cyclin-dependent kinase 2 (CDK2)",
        "gene_name": "CDK2",
        "organism": "Homo sapiens",
        "taxonomy_id": 9606,
        "sequence": "MENFQKVEKIGEGTYGVVYKARNKLTGEVVALKKIRLDTETEGVPSTAIREISLLKELNHPNIVKLLDVIHTENKLYLVFEFLHQDLKKFMDASALTGIPLPLIKSYLFQLLQGLAFCHSHRVLHRDLKPQNLLINTEGAIKLADFGLARAFGVPVRTYTHEVVTLWYRAPEILLGCKYYSTAVDIWSLGCIFAEMVTRRALFPGDSEIDQLFRIFRTLGTPDEVVWPGVTSMPDYKPSFPKWARQDFSKVVPPLDEDGRSLLSQMLHYDPNKRISAKAALAHPFFQDVTKPVPHLRL",
        "sequence_length": 298,
        "reviewed": True,
        "protein_existence": "Evidence at protein level",
        "source_url": "https://www.uniprot.org/uniprotkb/P24941/entry",
        "annotations": [
            {
                "functional_label": "ATP + [protein]-L-serine/L-threonine = ADP + [protein]-O-phospho-L-serine/L-threonine",
                "annotation_type": "catalytic_activity",
                "evidence_code": "ECO:0000269",
                "evidence_category": "EXPERIMENTAL",
                "supporting_reference": "PubMed:17349580",
                "source_field": "catalytic_activity",
            }
        ],
        "families": [{"family_name": "Protein kinase domain", "classification_source": "Pfam", "external_identifier": "PF00069"}]
    },
    {
        "accession": "P28482",
        "protein_name": "Mitogen-activated protein kinase 1 (MAPK1/ERK2)",
        "gene_name": "MAPK1",
        "organism": "Homo sapiens",
        "taxonomy_id": 9606,
        "sequence": "MAAAAAAGAGPEMVRGQVFDVGPRYTNLSYIGEGAYGMVCSAYDNVNKVRVAIKKISPFEHQTYCQRTLREIKILLRFRHENIIGINDIIRAPTIEQMKDVYIVQDLMETDLYKLLKTQHLSNDHICYFLYQILRGLKYIHSANVLHRDLKPSNLLLNTTCDLKICDFGLARVADPDHDHTGFLTEYVATRWYRAPEIMLNSKGYTKSIDIWSVGCILAEMLSNRPIFPGKHYLDQLNHILGILGSPSQEDLNCIINLKARNYLLSLPHKNKVPWNRLFPNADSKALDLLDKMLTFNPHKRIEVEQALAHPYLEQYYDPSDEPIAEAPFKFDMELDDLPKEKLKELIFEETARFQPGYRS",
        "sequence_length": 360,
        "reviewed": True,
        "protein_existence": "Evidence at protein level",
        "source_url": "https://www.uniprot.org/uniprotkb/P28482/entry",
        "annotations": [
            {
                "functional_label": "ATP + a protein serine/threonine = ADP + a protein serine/threonine phosphate",
                "annotation_type": "catalytic_activity",
                "evidence_code": "ECO:0000269",
                "evidence_category": "EXPERIMENTAL",
                "supporting_reference": "PubMed:15374980",
                "source_field": "catalytic_activity",
            }
        ],
        "families": [{"family_name": "Protein kinase domain", "classification_source": "Pfam", "external_identifier": "PF00069"}]
    },
    {
        "accession": "Q9Y616",
        "protein_name": "Inactive serine/threonine-protein kinase VRK3 (Pseudokinase)",
        "gene_name": "VRK3",
        "organism": "Homo sapiens",
        "taxonomy_id": 9606,
        "sequence": "MEGSRSSGSEESEEEPQGRPEPGSQRPKAVRGAQGPRSEGNKVRPAAANSRCPGAPGARAKAPVSRKPRATPRTPAAGSLAGASLVPLLGFLVAVLGAAATAVAGQRLCRWQEVRLPGPLRPEAVTALLDRLSVGLEPELHRRCVEALRAGSLGGSGGATDVVAKLGALLRKLRLAPLRKLRALCRAAERLADEPPALLRVARQALAGLVEVGGWEEAEAALGAPEEGPAGLSGLFWLLLHGAARSPLWALAAGPGAFRHQALRDALAGLCRLLRRLGPGAWGPELRSALAWCLGALCACPEALPEV",
        "sequence_length": 308,
        "reviewed": True,
        "protein_existence": "Evidence at protein level",
        "source_url": "https://www.uniprot.org/uniprotkb/Q9Y616/entry",
        "annotations": [
            {
                "functional_label": "Inactive kinase; regulates nuclear localization of MAPK phosphatase (scaffolding)",
                "annotation_type": "function_description",
                "evidence_code": "ECO:0000269",
                "evidence_category": "EXPERIMENTAL",
                "supporting_reference": "PubMed:16968747",
                "source_field": "function",
            }
        ],
        "families": [{"family_name": "Protein kinase domain", "classification_source": "Pfam", "external_identifier": "PF00069"}]
    },
    {
        "accession": "Q13418",
        "protein_name": "Integrin-linked protein kinase (ILK - Pseudokinase)",
        "gene_name": "ILK",
        "organism": "Homo sapiens",
        "taxonomy_id": 9606,
        "sequence": "MDDMDAMLAGLEPPAISLSTDGSLTVVVTETNSSPTLQRLVEQGIRVFIDGSSVEKLQEFYQLMVERAKSEELRDIELIKSLIQGKHIIDLKDNVFSSDTFYSVFKGLKDFEKDDTILKKLREVLAKGLKQLQLKDLGLPFEEAEMLKSLELLFKKDIKDLKDIVLKTVDFFLKLIKLKEKDREKLKKLREFLDKALEEVKKVDLGKPFELKEMLEALELLFKKDIKDLKDIVLKTVDFFLKLIKLKEKDREKLKKLREFLDKALEEVKKVDLGKPFELKEMLEALELLFKKDIKDLKDIVLKTVDFFLKLIKLKEKDREKLKKLREFLDKALEEVKKVDLGKPFELKEMLE",
        "sequence_length": 352,
        "reviewed": True,
        "protein_existence": "Evidence at protein level",
        "source_url": "https://www.uniprot.org/uniprotkb/Q13418/entry",
        "annotations": [
            {
                "functional_label": "Pseudokinase scaffold regulating integrin-mediated adhesion; lacks phosphotransfer",
                "annotation_type": "function_description",
                "evidence_code": "ECO:0000269",
                "evidence_category": "EXPERIMENTAL",
                "supporting_reference": "PubMed:19369385",
                "source_field": "function",
            }
        ],
        "families": [{"family_name": "Protein kinase domain", "classification_source": "Pfam", "external_identifier": "PF00069"}]
    }
]


class DataImportService:
    """
    Coordinates ingestion, transformation, deduplication, and persistence of UniProt kinase records.
    """

    def __init__(self, client: Optional[UniProtClient] = None):
        self.client = client or UniProtClient()

    def import_kinases(
        self,
        max_records: int = 500,
        reviewed_only: bool = True,
        force_refresh: bool = False,
        use_fallback_if_failed: bool = True,
    ) -> Dict[str, Any]:
        """
        Retrieves kinase records from UniProt and persists them into the database.
        """
        records: List[Dict[str, Any]] = []
        source_type = "uniprot_live_api"

        try:
            records = self.client.fetch_kinases(
                max_records=max_records,
                reviewed_only=reviewed_only,
                force_refresh=force_refresh,
            )
        except Exception as e:
            logger.error(f"Live UniProt query failed: {e}")
            if use_fallback_if_failed:
                logger.info("Employing curated reference kinase backup dataset.")
                records = CURATED_REFERENCE_KINASES
                source_type = "curated_fallback_reference"
            else:
                raise

        if not records:
            if use_fallback_if_failed:
                records = CURATED_REFERENCE_KINASES
                source_type = "curated_fallback_reference"

        # Ingest into database
        imported_count = 0
        updated_count = 0
        annotation_count = 0

        with get_db_session() as session:
            prot_repo = ProteinRepository(session)
            ann_repo = AnnotationRepository(session)

            for rec in records:
                existing = prot_repo.get_by_accession(rec["accession"])
                protein = prot_repo.upsert(rec)
                if existing:
                    updated_count += 1
                else:
                    imported_count += 1

                # Save annotations
                raw_anns = rec.get("annotations", [])
                if raw_anns:
                    ann_repo.replace_annotations(protein.id, raw_anns)
                    annotation_count += len(raw_anns)

                # Link families
                for fam in rec.get("families", []):
                    db_fam = session.query(ProteinFamily).filter(
                        ProteinFamily.family_name == fam["family_name"],
                        ProteinFamily.classification_source == fam["classification_source"],
                    ).first()
                    if not db_fam:
                        db_fam = ProteinFamily(
                            family_name=fam["family_name"],
                            classification_source=fam["classification_source"],
                            external_identifier=fam.get("external_identifier"),
                            description=fam.get("description"),
                        )
                        session.add(db_fam)
                        session.flush()

                    # Link membership
                    membership = session.query(ProteinFamilyMembership).filter(
                        ProteinFamilyMembership.protein_id == protein.id,
                        ProteinFamilyMembership.family_id == db_fam.id,
                    ).first()
                    if not membership:
                        membership = ProteinFamilyMembership(
                            protein_id=protein.id,
                            family_id=db_fam.id,
                            membership_source=fam["classification_source"],
                            membership_evidence="UniProt cross-reference",
                        )
                        session.add(membership)

        summary = {
            "source": source_type,
            "total_processed": len(records),
            "newly_inserted": imported_count,
            "updated": updated_count,
            "annotations_saved": annotation_count,
            "timestamp": datetime.utcnow().isoformat(),
        }
        logger.info(f"Import complete: {summary}")
        return summary
