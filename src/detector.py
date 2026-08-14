"""
detector.py — PII detection engine.

Wraps Microsoft Presidio AnalyzerEngine with:
  - spaCy en_core_web_lg for NER (PERSON, ORG, GPE, LOC)
  - Custom recognizers for email, phone, SSN, credit card, IP, DOB
  - OrgRecognizer for pattern-based Indian company name detection
  - AddressRecognizer for PIN codes and street/building address fragments

False-positive reduction:
  - Minimum NER confidence threshold (PERSON/ORG)
  - Blocklist of common financial/legal abbreviations that are NOT PII
    * For PERSON: any blocklist match disqualifies the entity
    * For ORGANIZATION: only disqualified if the ENTIRE entity is a
      regulatory acronym or standalone legal term (not a company name
      that happens to end with "Limited", "LLP", etc.)
  - Dates are only flagged as DOB when DOB context keywords are nearby
  - Credit cards must pass Luhn validation
  - IPs must be valid octets (0-255)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider

from .recognizers import (
    AddressRecognizer,
    CreditCardRecognizer,
    DOBRecognizer,
    EmailRecognizer,
    IPAddressRecognizer,
    OrgRecognizer,
    PersonRecognizer,
    PhoneRecognizer,
    SSNRecognizer,
)


# ---------------------------------------------------------------------------
# Entity types we care about — mapped to friendly category names
# ---------------------------------------------------------------------------
ENTITY_MAP: Dict[str, str] = {
    "PERSON":        "PERSON",
    "ORG":           "ORGANIZATION",
    "EMAIL_ADDRESS": "EMAIL",
    "PHONE_NUMBER":  "PHONE",
    "US_SSN":        "SSN",
    "CREDIT_CARD":   "CREDIT_CARD",
    "IP_ADDRESS":    "IP_ADDRESS",
    "DATE_OF_BIRTH": "DATE_OF_BIRTH",
    "LOCATION":      "ADDRESS",
    "GPE":           "ADDRESS",      # geopolitical entity (presidio may use)
}

TARGET_ENTITIES = list(ENTITY_MAP.keys())

# Minimum Presidio score to keep a detection
MIN_SCORE: float = 0.5

# ---------------------------------------------------------------------------
# Blocklist for PERSON entities
# Tokens that NER may mark as PERSON but are clearly not personal names.
# ---------------------------------------------------------------------------
_PERSON_BLOCKLIST_RE = re.compile(
    r"""(?xi)
    ^\s*(?:
      SEBI | NSE | BSE | RBI | MCA | NCLT | NCLAT |   # regulators / exchanges
      RERA | GSTIN | PAN | CIN | DIN | LLPIN | GIN |  # legal IDs
      Rs | INR | USD | EUR | GBP |                    # currency
      Schedule | Annexure | Exhibit | Section |       # doc structure
      Chapter | Clause | Regulation | Rule |
      Table | Figure | Page | Para |
      FY | Q[1-4] | H[12] |                           # fiscal periods
      IPO | OFS | SME | DRHP | RHP |                  # doc-specific terms
      Email | Phone | Fax | Website | Contact         # field labels
    )\s*$
    """,
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Blocklist for ORGANIZATION entities
# Only blocks when the ENTIRE entity text is a known non-entity term —
# does NOT block company names like "Wipro Limited" or "Infosys Technologies".
# ---------------------------------------------------------------------------
_ORG_STANDALONE_BLOCKLIST_RE = re.compile(
    r"""(?xi)
    ^\s*(?:
      SEBI | NSE | BSE | RBI | MCA | NCLT | NCLAT |   # regulators
      RERA | GSTIN | PAN | CIN | DIN | LLPIN | GIN |  # legal ID acronyms
      Rs | INR | USD | EUR | GBP |                    # currency
      Schedule | Annexure | Exhibit | Section |
      Chapter | Clause | Regulation | Rule |
      Table | Figure | Page | Para |
      FY | Q[1-4] | H[12] |
      IPO | OFS | SME | DRHP | RHP
    )\s*$
    """,
    re.IGNORECASE,
)


@dataclass
class DetectedEntity:
    """Represents a single detected PII entity."""

    entity_type: str       # normalised category name
    original_text: str     # exact string from the document
    start: int             # character offset in the source text
    end: int               # character offset (exclusive)
    score: float           # confidence score


def _build_analyzer() -> AnalyzerEngine:
    """Construct and configure the Presidio AnalyzerEngine."""
    # Use spaCy en_core_web_sm as the NLP backend
    provider = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
    })
    nlp_engine = provider.create_engine()

    # Build an empty registry — we'll add recognizers manually to avoid
    # name collisions with Presidio's built-in CreditCardRecognizer during
    # load_predefined_recognizers(). We import Presidio's NLP-based recognizer
    # directly and add only what we need.
    from presidio_analyzer.predefined_recognizers import SpacyRecognizer

    registry = RecognizerRegistry()

    # Add spaCy NER recognizer for PERSON, ORG, LOCATION, GPE
    spacy_rec = SpacyRecognizer(
        supported_language="en",
        supported_entities=["PERSON", "ORG", "LOCATION", "GPE", "FAC"],
        ner_strength=0.85,
    )
    registry.add_recognizer(spacy_rec)

    # Add our custom recognizers
    for recognizer in [
        EmailRecognizer(),
        PhoneRecognizer(),
        SSNRecognizer(),
        CreditCardRecognizer(),
        IPAddressRecognizer(),
        DOBRecognizer(),
        OrgRecognizer(),       # pattern-based ORG for Indian company names
        AddressRecognizer(),   # PIN codes and street-address fragments
        PersonRecognizer(),    # contextual person names (e.g. Contact Person, CS)
    ]:
        registry.add_recognizer(recognizer)

    return AnalyzerEngine(
        nlp_engine=nlp_engine,
        registry=registry,
        supported_languages=["en"],
    )


class PIIDetector:
    """
    High-level PII detection interface.

    Usage::
        detector = PIIDetector()
        entities = detector.detect(text)
    """

    def __init__(self, min_score: float = MIN_SCORE) -> None:
        self._analyzer = _build_analyzer()
        self._min_score = min_score

    def detect(self, text: str) -> List[DetectedEntity]:
        """
        Return a deduplicated, sorted list of PII entities found in *text*.

        The list is sorted by start offset; overlapping spans with lower
        confidence are removed.
        """
        if not text or not text.strip():
            return []

        results = self._analyzer.analyze(
            text=text,
            entities=TARGET_ENTITIES,
            language="en",
        )

        entities: List[DetectedEntity] = []
        for r in results:
            if r.score < self._min_score:
                continue

            raw = text[r.start: r.end]
            category = ENTITY_MAP.get(r.entity_type, r.entity_type)

            # --- Per-category false-positive filtering ---
            if category == "PERSON":
                # Block anything that matches the person blocklist
                if _PERSON_BLOCKLIST_RE.match(raw):
                    continue
                # Skip single-token all-uppercase tokens (likely acronyms)
                if len(raw.split()) == 1 and raw.isupper() and len(raw) <= 6:
                    continue

            elif category == "ORGANIZATION":
                # Only block standalone regulatory/document terms.
                # Company names like "Wipro Limited" are NOT blocked.
                if _ORG_STANDALONE_BLOCKLIST_RE.match(raw):
                    continue
                # Skip single-token all-uppercase short acronyms
                if len(raw.split()) == 1 and raw.isupper() and len(raw) <= 6:
                    continue

            entities.append(DetectedEntity(
                entity_type=category,
                original_text=raw,
                start=r.start,
                end=r.end,
                score=r.score,
            ))

        return _deduplicate(entities)


def _deduplicate(entities: List[DetectedEntity]) -> List[DetectedEntity]:
    """
    Remove overlapping entities, keeping the one with the higher score.
    Sort remaining entities by start position.
    """
    # Sort by start, then by descending score
    entities.sort(key=lambda e: (e.start, -e.score))
    kept: List[DetectedEntity] = []
    for ent in entities:
        # Check against all already-kept entities
        overlaps = any(
            (ent.start < k.end and ent.end > k.start)
            for k in kept
        )
        if not overlaps:
            kept.append(ent)
    kept.sort(key=lambda e: e.start)
    return kept
