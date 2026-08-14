"""
redactor.py — Orchestrates detection and redaction across a DOCX document.

For each paragraph (including table cells) it:
  1. Extracts the full text
  2. Runs the PII detector
  3. Generates synthetic replacements
  4. Applies replacements at Run level
  5. Collects a structured redaction log for evaluation/reporting
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

from docx import Document

from .detector import DetectedEntity, PIIDetector
from .document_processor import (
    apply_replacements_to_paragraph,
    iter_paragraphs,
    load_document,
)
from .replacer import get_replacement, get_all_mappings

logger = logging.getLogger(__name__)


@dataclass
class RedactionRecord:
    """Log entry for a single redacted PII instance."""
    entity_type: str
    original_text: str
    replacement_text: str
    paragraph_context: str   # first 80 chars of the paragraph for debugging


@dataclass
class RedactionResult:
    """Complete result of processing a document."""
    output_path: Path
    records: List[RedactionRecord] = field(default_factory=list)
    total_paragraphs: int = 0
    paragraphs_modified: int = 0

    @property
    def total_entities_found(self) -> int:
        return len(self.records)

    def summary_by_type(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for rec in self.records:
            counts[rec.entity_type] = counts.get(rec.entity_type, 0) + 1
        return counts


def redact_document(
    input_path: str | Path,
    output_path: str | Path,
    min_score: float = 0.5,
    verbose: bool = False,
    detector: Optional[PIIDetector] = None,
) -> RedactionResult:
    """
    Read *input_path*, redact PII, and save to *output_path*.

    Returns a :class:`RedactionResult` with full redaction log.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    logger.info("Loading document: %s", input_path)
    doc: Document = load_document(input_path)

    if detector is None:
        detector = PIIDetector(min_score=min_score)
    result = RedactionResult(output_path=output_path)

    for para, context_label in iter_paragraphs(doc):
        result.total_paragraphs += 1
        text = para.text
        if not text.strip():
            continue

        entities: List[DetectedEntity] = detector.detect(text)
        if not entities:
            continue

        # Build replacement pairs (maintain consistent mapping)
        pairs: List[Tuple[str, str]] = []
        for ent in entities:
            replacement = get_replacement(ent.original_text, ent.entity_type)
            pairs.append((ent.original_text, replacement))

            result.records.append(RedactionRecord(
                entity_type=ent.entity_type,
                original_text=ent.original_text,
                replacement_text=replacement,
                paragraph_context=text[:80],
            ))

            if verbose:
                logger.info(
                    "[%s] %-18s | %-40s → %s",
                    context_label,
                    ent.entity_type,
                    ent.original_text[:40],
                    replacement[:40],
                )

        # Apply to the paragraph — sorted longest-first to avoid substring issues
        pairs.sort(key=lambda p: len(p[0]), reverse=True)
        apply_replacements_to_paragraph(para, pairs)
        result.paragraphs_modified += 1

    logger.info("Saving redacted document to: %s", output_path)
    doc.save(str(output_path))

    logger.info(
        "Done. %d entities redacted across %d/%d paragraphs.",
        result.total_entities_found,
        result.paragraphs_modified,
        result.total_paragraphs,
    )
    return result
