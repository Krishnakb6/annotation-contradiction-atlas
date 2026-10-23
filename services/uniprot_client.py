"""
UniProt REST API client with query construction, pagination, retry/backoff,
response caching, sequence validation, and structured evidence extraction.
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import requests

from config import (
    UNIPROT_SEARCH_ENDPOINT,
    CACHE_DIR,
    DEFAULT_TAXONOMY_ID,
    DEFAULT_MAX_RECORDS,
    EVIDENCE_CATEGORIES,
)

logger = logging.getLogger("contradiction_atlas.uniprot")
logging.basicConfig(level=logging.INFO)

# Standard amino acid 1-letter code alphabet
STANDARD_AMINO_ACIDS = set("ACDEFGHIKLMNPQRSTVWY")
EXTENDED_AMINO_ACIDS = set("ACDEFGHIKLMNPQRSTVWYUBZX")
ACCESSION_PATTERN = re.compile(r"^[A-N,R-Z][0-9][A-Z][A-Z0-9]{2}[0-9]$|^[O,P,Q][0-9][A-Z0-9]{3}[0-9]$")


def categorize_evidence_code(evidence_code: Optional[str]) -> str:
    """
    Categorizes UniProt/GO ECO evidence codes into standard Atlas tiers.
    """
    if not evidence_code:
        return "UNSPECIFIED"

    code = evidence_code.strip()
    for cat, codes in EVIDENCE_CATEGORIES.items():
        if code in codes or any(code.startswith(c) for c in codes):
            return cat

    if code.startswith("ECO:0000269") or code.startswith("ECO:0000314"):
        return "EXPERIMENTAL"
    if code.startswith("ECO:0000250") or code.startswith("ECO:0000255"):
        return "PHYLOGENETIC_CURATED"
    if code.startswith("ECO:0000256") or code.startswith("ECO:0000259"):
        return "COMPUTATIONAL_UNREVIEWED"

    return "AUTHOR_STATEMENT"


def validate_protein_sequence(seq: str) -> Tuple[bool, Optional[str]]:
    """
    Validates that a biological sequence consists of legal amino acid characters.
    """
    if not seq or len(seq) == 0:
        return False, "Sequence is empty"

    cleaned = seq.strip().upper()
    invalid_chars = set(cleaned) - EXTENDED_AMINO_ACIDS
    if invalid_chars:
        return False, f"Sequence contains invalid non-amino acid characters: {invalid_chars}"

    return True, None


class UniProtClient:
    """
    Robust REST client for UniProtKB API with local caching, rate limiting, and structured parsing.
    """

    def __init__(
        self,
        base_url: str = UNIPROT_SEARCH_ENDPOINT,
        cache_dir: Path = CACHE_DIR,
        timeout: int = 25,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
    ):
        self.base_url = base_url
        self.cache_dir = cache_dir
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "AnnotationContradictionAtlas/1.0 (Academic Bioinformatics Research; mailto:atlas-kinome@example.org)",
            "Accept": "application/json",
        })

    def _execute_request_with_retry(self, url: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        Executes HTTP GET with exponential backoff on network or server errors.
        """
        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 3))
                    logger.warning(f"Rate limited (429). Backing off for {retry_after}s...")
                    time.sleep(retry_after)
                elif response.status_code >= 500:
                    logger.warning(f"Server error {response.status_code} on attempt {attempt}/{self.max_retries}")
                    time.sleep(self.backoff_factor ** attempt)
                else:
                    response.raise_for_status()
            except (requests.RequestException, ConnectionError) as exc:
                last_exception = exc
                logger.warning(f"Network error on attempt {attempt}/{self.max_retries}: {exc}")
                time.sleep(self.backoff_factor ** attempt)

        raise RuntimeError(f"UniProt request failed after {self.max_retries} attempts: {last_exception}")

    def fetch_kinases(
        self,
        query: Optional[str] = None,
        max_records: int = DEFAULT_MAX_RECORDS,
        reviewed_only: bool = True,
        use_cache: bool = True,
        force_refresh: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Fetches human protein kinase records from UniProt, handling pagination and caching.
        """
        cache_file = self.cache_dir / f"uniprot_kinases_cache_{'reviewed' if reviewed_only else 'all'}.json"

        # Check local cache
        if use_cache and not force_refresh and cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_payload = json.load(f)
                logger.info(f"Loaded {len(cached_payload.get('records', []))} records from cache ({cache_file.name})")
                return cached_payload.get("records", [])[:max_records]
            except Exception as e:
                logger.warning(f"Failed to read cache file {cache_file}: {e}. Falling back to live query.")

        # Default query construction
        if not query:
            rev_str = "true" if reviewed_only else "*"
            query = f'taxonomy_id:{DEFAULT_TAXONOMY_ID} AND reviewed:{rev_str} AND (family:"protein kinase" OR keyword:"Kinase [KW-0418]" OR ec:2.7.10.* OR ec:2.7.11.*)'

        records: List[Dict[str, Any]] = []
        page_size = min(max_records, 250)
        params = {
            "query": query,
            "size": page_size,
            "format": "json",
        }
        next_url = self.base_url

        logger.info(f"Initiating UniProt query: '{query}' (Target records: {max_records})")

        while next_url and len(records) < max_records:
            response = self._execute_request_with_retry(next_url, params=params if next_url == self.base_url else None)
            data = response.json()
            raw_entries = data.get("results", [])

            for raw in raw_entries:
                parsed = self.parse_uniprot_entry(raw)
                if parsed:
                    records.append(parsed)
                    if len(records) >= max_records:
                        break

            # Check pagination via Link header or next URL
            link_header = response.headers.get("Link", "")
            next_url = None
            if 'rel="next"' in link_header:
                match = re.search(r'<([^>]+)>;\s*rel="next"', link_header)
                if match:
                    next_url = match.group(1)

            # Prevent excessive hammering
            time.sleep(0.1)

        logger.info(f"Successfully retrieved and parsed {len(records)} valid protein records.")

        # Save to disk cache
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({
                    "retrieved_at": datetime.utcnow().isoformat(),
                    "source_query": query,
                    "count": len(records),
                    "records": records,
                }, f, indent=2, default=str)
            logger.info(f"Cached records to {cache_file.name}")
        except Exception as e:
            logger.error(f"Failed to write cache file: {e}")

        return records

    def parse_uniprot_entry(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extracts strongly typed attributes from a raw UniProt JSON entry.
        Filters out invalid sequences or missing essential identifiers.
        """
        accession = entry.get("primaryAccession")
        if not accession:
            return None

        # Sequence validation
        seq_info = entry.get("sequence", {})
        raw_sequence = seq_info.get("value", "").replace(" ", "").replace("\n", "").upper()
        is_valid, err = validate_protein_sequence(raw_sequence)
        if not is_valid:
            logger.debug(f"Skipping {accession}: {err}")
            return None

        # Protein name
        desc = entry.get("proteinDescription", {})
        rec_name = (
            desc.get("recommendedName", {}).get("fullName", {}).get("value")
            or desc.get("submissionNames", [{}])[0].get("fullName", {}).get("value")
            or desc.get("alternativeNames", [{}])[0].get("fullName", {}).get("value")
            or "Uncharacterized protein kinase"
        )

        # Gene name
        genes = entry.get("genes", [])
        gene_name = genes[0].get("geneName", {}).get("value") if genes else None

        # Organism
        org = entry.get("organism", {})
        organism_name = org.get("scientificName", "Homo sapiens")
        taxonomy_id = org.get("taxonId", DEFAULT_TAXONOMY_ID)

        # Reviewed status
        entry_type = entry.get("entryType", "")
        reviewed = "reviewed" in entry_type.lower() or entry_type == "UniProtKB reviewed (Swiss-Prot)"

        protein_existence = entry.get("proteinExistence", "Evidence at protein level")
        source_url = f"https://www.uniprot.org/uniprotkb/{accession}/entry"

        # Parse functional annotations and catalytic activities
        annotations: List[Dict[str, Any]] = []
        comments = entry.get("comments", [])
        for c in comments:
            ctype = c.get("commentType", "")
            if ctype == "CATALYTIC ACTIVITY":
                reaction = c.get("reaction", {})
                rxn_name = reaction.get("name")
                ec_num = reaction.get("ecNumber")
                label = rxn_name or (f"EC:{ec_num}" if ec_num else "Kinase catalytic activity")

                evidences = reaction.get("evidences", [])
                if evidences:
                    for ev in evidences:
                        ecode = ev.get("evidenceCode")
                        ref = f"{ev.get('source')}:{ev.get('id')}" if ev.get("id") else ev.get("source")
                        annotations.append({
                            "functional_label": label,
                            "annotation_type": "catalytic_activity",
                            "evidence_code": ecode,
                            "evidence_category": categorize_evidence_code(ecode),
                            "supporting_reference": ref,
                            "source_field": "comments.CATALYTIC_ACTIVITY",
                            "provenance_details": json.dumps({"ecNumber": ec_num, "reaction": rxn_name}),
                        })
                else:
                    annotations.append({
                        "functional_label": label,
                        "annotation_type": "catalytic_activity",
                        "evidence_code": None,
                        "evidence_category": "UNSPECIFIED",
                        "supporting_reference": None,
                        "source_field": "comments.CATALYTIC_ACTIVITY",
                        "provenance_details": json.dumps({"ecNumber": ec_num, "reaction": rxn_name}),
                    })

            elif ctype == "FUNCTION":
                texts = c.get("texts", [])
                for t in texts:
                    val = t.get("value", "").strip()
                    if not val:
                        continue
                    evidences = t.get("evidences", [])
                    if evidences:
                        for ev in evidences:
                            ecode = ev.get("evidenceCode")
                            ref = f"{ev.get('source')}:{ev.get('id')}" if ev.get("id") else ev.get("source")
                            annotations.append({
                                "functional_label": val[:250],
                                "annotation_type": "function_description",
                                "evidence_code": ecode,
                                "evidence_category": categorize_evidence_code(ecode),
                                "supporting_reference": ref,
                                "source_field": "comments.FUNCTION",
                                "provenance_details": val,
                            })
                    else:
                        annotations.append({
                            "functional_label": val[:250],
                            "annotation_type": "function_description",
                            "evidence_code": None,
                            "evidence_category": "UNSPECIFIED",
                            "supporting_reference": None,
                            "source_field": "comments.FUNCTION",
                            "provenance_details": val,
                        })

        # Parse families / domain cross-references (Pfam, InterPro)
        families: List[Dict[str, Any]] = []
        cross_refs = entry.get("uniProtKBCrossReferences", [])
        for xref in cross_refs:
            db = xref.get("database")
            xid = xref.get("id")
            if db in ("Pfam", "InterPro", "PROSITE"):
                props = {p.get("key"): p.get("value") for p in xref.get("properties", [])}
                fam_name = props.get("EntryName") or props.get("Description") or f"{db}:{xid}"
                families.append({
                    "family_name": fam_name,
                    "classification_source": db,
                    "external_identifier": xid,
                    "description": props.get("Description"),
                })

        return {
            "accession": accession,
            "protein_name": rec_name,
            "gene_name": gene_name,
            "organism": organism_name,
            "taxonomy_id": taxonomy_id,
            "sequence": raw_sequence,
            "sequence_length": len(raw_sequence),
            "reviewed": reviewed,
            "protein_existence": protein_existence,
            "source_url": source_url,
            "retrieval_timestamp": datetime.utcnow(),
            "annotations": annotations,
            "families": families,
        }
