"""
pii_redactor.py — CLI entry point for the PII Redaction Tool.

Usage:
    python pii_redactor.py [--input INPUT] [--output OUTPUT] [--evaluate] [--verbose]

Arguments:
    --input     Path to input DOCX (default: "Red Herring Prospectus (2).docx")
    --output    Path for redacted DOCX output (default: "redacted_output.docx")
    --evaluate  Run synthetic evaluation and generate evaluation_report.md
    --verbose   Print every detected entity during processing
    --min-score Minimum Presidio confidence threshold (default: 0.5)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# ── project modules ────────────────────────────────────────────────────────
from src.redactor import redact_document
from src.evaluator import run_synthetic_evaluation, format_report_markdown
from src.detector import PIIDetector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DEFAULT_INPUT  = "Red Herring Prospectus (2).docx"
DEFAULT_OUTPUT = "redacted_output.docx"
EVAL_REPORT    = "evaluation_report.md"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="PII Redaction Tool — Scaler AI Labs Assignment"
    )
    parser.add_argument("--input",  default=DEFAULT_INPUT,  help="Input DOCX path")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output DOCX path")
    parser.add_argument(
        "--evaluate", action="store_true",
        help="Run synthetic evaluation and write evaluation_report.md"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print every detected entity"
    )
    parser.add_argument(
        "--min-score", type=float, default=0.5,
        help="Minimum Presidio confidence score (0-1, default 0.5)"
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    input_path  = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        logger.error("Input file not found: %s", input_path)
        sys.exit(1)

    # ── Step 1: Redact the document ────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("PII Redaction Tool  |  Input: %s", input_path.name)
    logger.info("=" * 60)

    result = redact_document(
        input_path=input_path,
        output_path=output_path,
        min_score=args.min_score,
        verbose=args.verbose,
    )

    # Print summary
    print("\n" + "=" * 60)
    print(f"  Redaction complete!")
    print(f"  Output saved to: {output_path}")
    print(f"  Total paragraphs: {result.total_paragraphs}")
    print(f"  Paragraphs modified: {result.paragraphs_modified}")
    print(f"  Total PII entities redacted: {result.total_entities_found}")
    print()
    print("  Breakdown by category:")
    for cat, count in sorted(result.summary_by_type().items(), key=lambda x: -x[1]):
        print(f"    {cat:<20}: {count}")
    print("=" * 60)

    # ── Step 2: Evaluation ─────────────────────────────────────────────────
    if args.evaluate:
        logger.info("Running synthetic evaluation…")
        detector = PIIDetector(min_score=args.min_score)
        eval_report = run_synthetic_evaluation(detector=detector)

        redaction_summary = {
            "total_paragraphs":   result.total_paragraphs,
            "modified_paragraphs": result.paragraphs_modified,
            "total_entities_found": result.total_entities_found,
            "by_type":            result.summary_by_type(),
        }

        # Collect observed FPs from the document run (heuristic spot-check)
        observed_fps = _extract_observed_fps(result)

        markdown = format_report_markdown(
            eval_report=eval_report,
            redaction_summary=redaction_summary,
            observed_fps=observed_fps,
        )

        Path(EVAL_REPORT).write_text(markdown, encoding="utf-8")
        logger.info("Evaluation report written to: %s", EVAL_REPORT)

        print(f"\n  Synthetic Benchmark Evaluation Summary (87 Sentences / 74 Entity Targets):")
        print(f"    1. Sentence-Level Binary Classification (Accuracy):")
        print(f"       Accuracy  : {eval_report.sentence_classification.accuracy:.1%}")
        print(f"       Precision : {eval_report.sentence_classification.precision:.1%}")
        print(f"       Recall    : {eval_report.sentence_classification.recall:.1%}")
        print(f"       F1 Score  : {eval_report.sentence_classification.f1:.1%}")
        print(f"       Confusion Matrix (TP/TN/FP/FN): {eval_report.sentence_classification.tp} / {eval_report.sentence_classification.tn} / {eval_report.sentence_classification.fp} / {eval_report.sentence_classification.fn}")
        print(f"    2. Entity / Span-Level Detection:")
        print(f"       Precision : {eval_report.entity_overall.precision:.1%}")
        print(f"       Recall    : {eval_report.entity_overall.recall:.1%}")
        print(f"       F1 Score  : {eval_report.entity_overall.f1:.1%}")
        print(f"       Entity Counts (TP/FP/FN): {eval_report.entity_overall.tp} / {eval_report.entity_overall.fp} / {eval_report.entity_overall.fn}")


def _extract_observed_fps(result) -> list:
    """
    Heuristically identify likely false positives from the document run.
    Looks for entities that match known non-PII patterns.
    """
    import re

    # Patterns that strongly suggest the detected text is NOT PII
    non_pii_patterns = [
        (re.compile(r"^(?:SEBI|NSE|BSE|RBI|MCA|RERA|NCLT|CIN|DIN|LLPIN)$"), "Regulatory/legal abbreviation"),
        (re.compile(r"^(?:Pvt\.?|Ltd\.?|LLP|Inc\.?|Corp\.?)$"), "Legal entity suffix"),
        (re.compile(r"^(?:Schedule|Annexure|Exhibit|Section|Clause|Chapter)\s+\w+$", re.I), "Document structure reference"),
        (re.compile(r"^\d+(?:\.\d+)?$"), "Numeric value"),
        (re.compile(r"^(?:FY|Q[1-4]|H[12])\d{2,4}$"), "Fiscal period"),
    ]

    observed = []
    seen = set()
    for rec in result.records:
        text = rec.original_text.strip()
        if text in seen:
            continue
        seen.add(text)
        for pattern, reason in non_pii_patterns:
            if pattern.match(text):
                observed.append({
                    "text": text,
                    "entity_type": rec.entity_type,
                    "reason": reason,
                })
                break
    return observed


if __name__ == "__main__":
    main()
