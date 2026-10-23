"""
Unit tests for UniProt REST client, parsing, sequence validation, and caching.
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from services.uniprot_client import (
    validate_protein_sequence,
    categorize_evidence_code,
    UniProtClient,
)


def test_sequence_validation():
    # Valid canonical sequences
    ok, err = validate_protein_sequence("VAIKTLKPGTMSPEAFLQEAQVMKKLRHEKLVQLYAVVSEEPIYIV")
    assert ok is True
    assert err is None

    # Empty sequence
    ok, err = validate_protein_sequence("")
    assert ok is False
    assert "empty" in err.lower()

    # Invalid sequence with digits or illegal characters
    ok, err = validate_protein_sequence("MKT123*#XYZ")
    assert ok is False
    assert "invalid non-amino acid" in err.lower()


def test_evidence_code_categorization():
    assert categorize_evidence_code("ECO:0000269") == "EXPERIMENTAL"
    assert categorize_evidence_code("ECO:0000314") == "EXPERIMENTAL"
    assert categorize_evidence_code("ECO:0000250") == "PHYLOGENETIC_CURATED"
    assert categorize_evidence_code("ECO:0000256") == "COMPUTATIONAL_UNREVIEWED"
    assert categorize_evidence_code("ECO:0000305") == "AUTHOR_STATEMENT"
    assert categorize_evidence_code(None) == "UNSPECIFIED"


def test_uniprot_entry_parsing():
    client = UniProtClient()

    mock_entry = {
        "primaryAccession": "P00533",
        "entryType": "UniProtKB reviewed (Swiss-Prot)",
        "proteinDescription": {
            "recommendedName": {"fullName": {"value": "Epidermal growth factor receptor"}}
        },
        "genes": [{"geneName": {"value": "EGFR"}}],
        "organism": {"scientificName": "Homo sapiens", "taxonId": 9606},
        "sequence": {"value": "MRPSGTAGAALLALLAALCPASRALEEKKVCQ", "length": 32},
        "proteinExistence": "Evidence at protein level",
        "comments": [
            {
                "commentType": "CATALYTIC ACTIVITY",
                "reaction": {
                    "name": "ATP + a protein = ADP + a phosphoprotein",
                    "ecNumber": "2.7.10.1",
                    "evidences": [{"evidenceCode": "ECO:0000269", "source": "PubMed", "id": "15374980"}]
                }
            },
            {
                "commentType": "FUNCTION",
                "texts": [{"value": "Receptor tyrosine kinase", "evidences": []}]
            }
        ],
        "uniProtKBCrossReferences": [
            {
                "database": "Pfam",
                "id": "PF00069",
                "properties": [{"key": "EntryName", "value": "Pkinase"}]
            }
        ]
    }

    parsed = client.parse_uniprot_entry(mock_entry)
    assert parsed is not None
    assert parsed["accession"] == "P00533"
    assert parsed["gene_name"] == "EGFR"
    assert parsed["sequence_length"] == 32
    assert parsed["reviewed"] is True
    assert len(parsed["annotations"]) == 2
    assert parsed["annotations"][0]["evidence_category"] == "EXPERIMENTAL"
    assert parsed["annotations"][0]["supporting_reference"] == "PubMed:15374980"
    assert len(parsed["families"]) == 1


def test_client_caching_and_mock_fallback(tmp_path):
    client = UniProtClient(cache_dir=tmp_path)
    sample_records = [
        {
            "accession": "P12931",
            "protein_name": "Proto-oncogene tyrosine-protein kinase Src",
            "gene_name": "SRC",
            "organism": "Homo sapiens",
            "taxonomy_id": 9606,
            "sequence": "MGSSKSKPKDPSQRRRSLEP",
            "sequence_length": 20,
            "reviewed": True,
            "source_url": "https://www.uniprot.org/uniprotkb/P12931/entry",
            "annotations": [],
            "families": [],
        }
    ]

    cache_file = tmp_path / "uniprot_kinases_cache_reviewed.json"
    with open(cache_file, "w") as f:
        json.dump({"records": sample_records}, f)

    # Should read from cache without network request
    results = client.fetch_kinases(reviewed_only=True, use_cache=True, force_refresh=False)
    assert len(results) == 1
    assert results[0]["accession"] == "P12931"
