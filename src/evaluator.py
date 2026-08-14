"""
evaluator.py — PII detection evaluation and reporting.

Two evaluation modes:

1. **Synthetic Ground-Truth Benchmark** (curated 87-sentence corpus):
   Evaluated at TWO distinct, methodologically separated levels:

   A. **Entity / Span-Level Evaluation** (evaluation unit = individual entity spans):
      - Positive targets: 74 ground-truth PII entity spans across 69 positive sentences.
      - Exact entity-span matching: True Positive requires start offset, end offset,
        and entity category to match ground truth exactly.
      - TP: Ground-truth target span correctly identified (exact span + category match).
      - FP: Detected entity span that does not exactly match any ground-truth PII entity.
      - FN: Ground-truth target span not matched by the detector.
      - Metrics: Precision, Recall, F1 (overall and per PII category).
      - Note: TN and Accuracy are not defined at the span level because the space
        of non-entity character spans is unbounded.

   B. **Sentence-Level Binary Classification** (evaluation unit = whole sentences):
      - Test cases: 87 total sentences (69 positive sentences with PII, 18 negative distractor sentences without PII).
      - Positive sentence: Ground truth contains >= 1 target entity.
      - Negative sentence: Ground truth contains 0 target entities.
      - Predicted positive: Detector produced >= 1 entity detection in the sentence.
      - Predicted negative: Detector produced 0 entity detections in the sentence.
      - Metrics: Accuracy = (TP + TN) / (TP + TN + FP + FN), plus Precision, Recall, F1.

2. **Document-Level Statistics** (actual Red Herring Prospectus):
   - Raw counts per PII category from the 5,205 paragraphs (1,006 body + 4,199 table paragraphs across 76 tables).
   - Qualitative spot-check observations of false positives.
   - NOTE: Metrics in §1 apply strictly to the synthetic ground-truth benchmark and
     are NOT claimed to be exact metrics for the full prospectus document.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .detector import PIIDetector
from .evaluator_helper import resolve_entity_spans


# ---------------------------------------------------------------------------
# Raw synthetic test corpus (87 sentences: 69 positive with 74 entity targets, 18 negative)
# Ground truth entities are defined by (entity_text, category) pairs.
# Start and end character offsets are derived automatically via resolve_entity_spans.
# ---------------------------------------------------------------------------

RAW_SYNTHETIC_CORPUS: List[Tuple[str, List[Tuple[str, str]]]] = [

    # ══════════════════════════════════════════════════════════════════════
    # PERSON  (12 positive sentences, 15 entity targets)
    # ══════════════════════════════════════════════════════════════════════
    (
        "The CEO Rajesh Kumar will present the financials.",
        [("Rajesh Kumar", "PERSON")],
    ),
    (
        "Please contact Priya Mehta at your earliest convenience.",
        [("Priya Mehta", "PERSON")],
    ),
    (
        "Mr. Anil Gupta signed the agreement on behalf of the company.",
        [("Anil Gupta", "PERSON")],
    ),
    (
        "Sunita Sharma and Vikram Nair are the co-founders.",
        [("Sunita Sharma", "PERSON"), ("Vikram Nair", "PERSON")],
    ),
    (
        "The director Sarthak Malvadkar resigned last month.",
        [("Sarthak Malvadkar", "PERSON")],
    ),
    (
        "Abhijit Diwan heads the compliance department.",
        [("Abhijit Diwan", "PERSON")],
    ),
    (
        "Kishan Rastogi and Varun Badai attended the board meeting.",
        [("Kishan Rastogi", "PERSON"), ("Varun Badai", "PERSON")],
    ),
    (
        "Contact the nodal officer Prakash Boricha for queries.",
        [("Prakash Boricha", "PERSON")],
    ),
    (
        "Siddharth Jadhav and Eric Bacha co-lead the project.",
        [("Siddharth Jadhav", "PERSON"), ("Eric Bacha", "PERSON")],
    ),
    (
        "The chairman is Anand Soni.",
        [("Anand Soni", "PERSON")],
    ),
    (
        "Chitra Raste is the legal counsel.",
        [("Chitra Raste", "PERSON")],
    ),
    (
        "Ashish Mathew Pulloor submitted the compliance report.",
        [("Ashish Mathew Pulloor", "PERSON")],
    ),

    # ══════════════════════════════════════════════════════════════════════
    # ORGANIZATION  (10 positive sentences, 10 entity targets)
    # ══════════════════════════════════════════════════════════════════════
    (
        "The company Infosys Technologies submitted the filing.",
        [("Infosys Technologies", "ORGANIZATION")],
    ),
    (
        "Wipro Limited and TCS have signed an MOU.",
        [("Wipro Limited", "ORGANIZATION")],
    ),
    (
        "KSH International Private Limited is the issuer.",
        [("KSH International Private Limited", "ORGANIZATION")],
    ),
    (
        "The promoter is Acme Pvt. Ltd.",
        [("Acme Pvt. Ltd.", "ORGANIZATION")],
    ),
    (
        "Nuvama Wealth Management Limited managed the book.",
        [("Nuvama Wealth Management Limited", "ORGANIZATION")],
    ),
    (
        "ICICI Securities Limited is the lead manager.",
        [("ICICI Securities Limited", "ORGANIZATION")]),
    (
        "Bajaj Finserv Limited reported strong quarterly results.",
        [("Bajaj Finserv Limited", "ORGANIZATION")],
    ),
    (
        "The auditor is Deloitte Haskins & Sells LLP.",
        [("Deloitte Haskins & Sells LLP", "ORGANIZATION")],
    ),
    (
        "IndusInd Bank Limited extended a credit facility.",
        [("IndusInd Bank Limited", "ORGANIZATION")],
    ),
    (
        "Kirtane & Pandit LLP is the statutory auditor.",
        [("Kirtane & Pandit LLP", "ORGANIZATION")],
    ),

    # ══════════════════════════════════════════════════════════════════════
    # EMAIL  (8 positive sentences, 9 entity targets)
    # ══════════════════════════════════════════════════════════════════════
    (
        "Send the report to arjun.patel@example.com before Monday.",
        [("arjun.patel@example.com", "EMAIL")],
    ),
    (
        "Contact us at support@mycompany.in or sales@mycompany.in.",
        [("support@mycompany.in", "EMAIL"), ("sales@mycompany.in", "EMAIL")],
    ),
    (
        "The director's email is r.sharma@abc-corp.co.in.",
        [("r.sharma@abc-corp.co.in", "EMAIL")],
    ),
    (
        "Reach Prakash at prakash.boricha@nuvama.com for IPO queries.",
        [("prakash.boricha@nuvama.com", "EMAIL")],
    ),
    (
        "Email ksh.ipo@nuvama.com for application forms.",
        [("ksh.ipo@nuvama.com", "EMAIL")],
    ),
    (
        "Grievances: customercare@icicisecurities.com",
        [("customercare@icicisecurities.com", "EMAIL")],
    ),
    (
        "Send documents to sarthak.malvadkar@kshinternational.com.",
        [("sarthak.malvadkar@kshinternational.com", "EMAIL")],
    ),
    (
        "For legal queries: ipo@trilegal.com",
        [("ipo@trilegal.com", "EMAIL")],
    ),

    # ══════════════════════════════════════════════════════════════════════
    # PHONE  (8 positive sentences, 8 entity targets)
    # ══════════════════════════════════════════════════════════════════════
    (
        "Call me on +91 9876543210 for more details.",
        [("+91 9876543210", "PHONE")],
    ),
    (
        "Registered mobile: 9123456789.",
        [("9123456789", "PHONE")],
    ),
    (
        "International: +1-800-555-0199.",
        [("+1-800-555-0199", "PHONE")],
    ),
    (
        "Office: +91 22 40094400.",
        [("+91 22 40094400", "PHONE")],
    ),
    (
        "Fax: +91 22 6807 7100.",
        [("+91 22 6807 7100", "PHONE")],
    ),
    (
        "Toll-free: 1800-103-0000.",
        [("1800-103-0000", "PHONE")],
    ),
    (
        "Mobile: +91 81081 14949.",
        [("+91 81081 14949", "PHONE")],
    ),
    (
        "Contact: +91 20 6606 4494.",
        [("+91 20 6606 4494", "PHONE")],
    ),

    # ══════════════════════════════════════════════════════════════════════
    # SSN  (5 positive sentences, 5 entity targets)
    # ══════════════════════════════════════════════════════════════════════
    (
        "The employee's SSN is 123-45-6789.",
        [("123-45-6789", "SSN")],
    ),
    (
        "Social security number: 567-89-0123.",
        [("567-89-0123", "SSN")],
    ),
    (
        "SSN on file: 234-56-7890.",
        [("234-56-7890", "SSN")],
    ),
    (
        "Please provide your SSN 345-67-8901 for verification.",
        [("345-67-8901", "SSN")],
    ),
    (
        "Tax ID (SSN): 456-78-9012.",
        [("456-78-9012", "SSN")],
    ),

    # ══════════════════════════════════════════════════════════════════════
    # CREDIT CARD  (6 positive sentences, 6 entity targets)
    # ══════════════════════════════════════════════════════════════════════
    (
        "My card number is 4111 1111 1111 1111.",
        [("4111 1111 1111 1111", "CREDIT_CARD")],
    ),
    (
        "Charged to: 5500 0055 0055 0002.",
        [("5500 0055 0055 0002", "CREDIT_CARD")],
    ),
    (
        "Amex card: 3782 822463 10005.",
        [("3782 822463 10005", "CREDIT_CARD")],
    ),
    (
        "Visa: 4012888888881881.",
        [("4012888888881881", "CREDIT_CARD")],
    ),
    (
        "Payment via card 5105 1051 0510 5100.",
        [("5105 1051 0510 5100", "CREDIT_CARD")],
    ),
    (
        "Rupay card ending 6011 1111 1111 1117.",
        [("6011 1111 1111 1117", "CREDIT_CARD")],
    ),

    # ══════════════════════════════════════════════════════════════════════
    # IP ADDRESS  (6 positive sentences, 7 entity targets)
    # ══════════════════════════════════════════════════════════════════════
    (
        "The server IP address is 203.0.113.42.",
        [("203.0.113.42", "IP_ADDRESS")],
    ),
    (
        "Requests originated from 10.0.0.15 and 192.168.1.1.",
        [("10.0.0.15", "IP_ADDRESS"), ("192.168.1.1", "IP_ADDRESS")],
    ),
    (
        "Blocked IP: 198.51.100.5.",
        [("198.51.100.5", "IP_ADDRESS")],
    ),
    (
        "Logged in from 172.16.0.100.",
        [("172.16.0.100", "IP_ADDRESS")],
    ),
    (
        "Source address: 100.64.1.200.",
        [("100.64.1.200", "IP_ADDRESS")],
    ),
    (
        "The attacker used 8.8.8.8 as an exit node.",
        [("8.8.8.8", "IP_ADDRESS")],
    ),

    # ══════════════════════════════════════════════════════════════════════
    # DATE OF BIRTH  (6 positive sentences, 6 entity targets)
    # ══════════════════════════════════════════════════════════════════════
    (
        "Date of birth: 15/08/1985.",
        [("15/08/1985", "DATE_OF_BIRTH")],
    ),
    (
        "He was born on 23 March 1979.",
        [("23 March 1979", "DATE_OF_BIRTH")],
    ),
    (
        "DOB: 01-Jan-1990",
        [("01-Jan-1990", "DATE_OF_BIRTH")],
    ),
    (
        "Born: 1990-06-15.",
        [("1990-06-15", "DATE_OF_BIRTH")],
    ),
    (
        "Her date of birth is 12/04/1988.",
        [("12/04/1988", "DATE_OF_BIRTH")],
    ),
    (
        "Applicant DOB: 05 July 1975.",
        [("05 July 1975", "DATE_OF_BIRTH")],
    ),

    # ══════════════════════════════════════════════════════════════════════
    # ADDRESS  (8 positive sentences, 8 entity targets)
    # ══════════════════════════════════════════════════════════════════════
    (
        "Registered office: B Wing, 4th Floor, Ruby Tower, Mumbai.",
        [("B Wing, 4th Floor, Ruby Tower, Mumbai", "ADDRESS")],
    ),
    (
        "Address: Plot No. 12, MIDC Industrial Area, Pune.",
        [("Plot No. 12, MIDC Industrial Area, Pune", "ADDRESS")],
    ),
    (
        "Situated at Survey No. 341/2, Chakan, Pune - 411003.",
        [("Survey No. 341/2, Chakan, Pune - 411003", "ADDRESS")],
    ),
    (
        "Flat No. 5, Sector 17, Navi Mumbai - 400706.",
        [("Flat No. 5, Sector 17, Navi Mumbai - 400706", "ADDRESS")],
    ),
    (
        "House No. 22, MG Road, Bengaluru.",
        [("House No. 22, MG Road, Bengaluru", "ADDRESS")],
    ),
    (
        "The PIN code is 411001.",
        [("411001", "ADDRESS")],
    ),
    (
        "Postal code: 400028.",
        [("400028", "ADDRESS")],
    ),
    (
        "Unit 8693 Box 0403, DPO AE 22546.",
        [("Unit 8693 Box 0403, DPO AE 22546", "ADDRESS")],
    ),

    # ══════════════════════════════════════════════════════════════════════
    # NEGATIVE CASES — 18 sentences (0 PII targets, distractor non-PII)
    # ══════════════════════════════════════════════════════════════════════
    ("The net revenue was ₹12,34,56,789 for FY 2023.", []),
    ("Total assets: Rs. 9,87,654.", []),
    ("EBITDA margin improved to 18.5%.", []),
    ("Face value: Rs. 2 per share.", []),
    ("See page 42 for details.", []),
    ("Refer to Section 91 of the Companies Act.", []),
    ("As per Clause 49 of the Listing Agreement.", []),
    ("Chapter 3 covers the risk factors.", []),
    ("CIN: L12345MH2000PLC123456.", []),
    ("LLPIN: AAA-0000.", []),
    ("GSTIN: 27AAKCS1234H1Z0.", []),
    ("The AGM is scheduled for 15/08/2024.", []),
    ("The subscription period closes on 30 September 2024.", []),
    ("FY 2023-24 ended on 31/03/2024.", []),
    ("The company was incorporated on 12/04/2001.", []),
    ("Software version 3.14.159 was released.", []),
    ("Python 3.11.2 is the minimum supported version.", []),
    ("Order number: 1234567890.", []),
]

# Derived corpus with validated character offsets
SYNTHETIC_CORPUS: List[Tuple[str, List[Tuple[int, int, str]]]] = [
    (text, resolve_entity_spans(text, raw_ents))
    for text, raw_ents in RAW_SYNTHETIC_CORPUS
]


# ---------------------------------------------------------------------------
# Evaluation data structures
# ---------------------------------------------------------------------------

@dataclass
class CategoryMetrics:
    """Entity/Span-level evaluation metrics."""
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) > 0 else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) > 0 else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


@dataclass
class SentenceClassificationMetrics:
    """Sentence-level binary classification metrics."""
    tp: int = 0
    tn: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def accuracy(self) -> float:
        total = self.tp + self.tn + self.fp + self.fn
        return (self.tp + self.tn) / total if total > 0 else 0.0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) > 0 else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) > 0 else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


@dataclass
class EvaluationReport:
    entity_overall: CategoryMetrics = field(default_factory=CategoryMetrics)
    per_category: Dict[str, CategoryMetrics] = field(default_factory=dict)
    sentence_classification: SentenceClassificationMetrics = field(default_factory=SentenceClassificationMetrics)
    false_positives: List[Dict] = field(default_factory=list)
    false_negatives: List[Dict] = field(default_factory=list)
    total_sentences: int = 0
    positive_sentences: int = 0
    negative_sentences: int = 0
    total_target_entities: int = 0

    def to_dict(self) -> dict:
        return {
            "corpus": {
                "total_sentences": self.total_sentences,
                "positive_sentences": self.positive_sentences,
                "negative_sentences": self.negative_sentences,
                "total_target_entities": self.total_target_entities,
            },
            "sentence_level_binary_classification": {
                "tp": self.sentence_classification.tp,
                "tn": self.sentence_classification.tn,
                "fp": self.sentence_classification.fp,
                "fn": self.sentence_classification.fn,
                "accuracy": round(self.sentence_classification.accuracy, 4),
                "precision": round(self.sentence_classification.precision, 4),
                "recall": round(self.sentence_classification.recall, 4),
                "f1": round(self.sentence_classification.f1, 4),
            },
            "entity_level_metrics": {
                "tp": self.entity_overall.tp,
                "fp": self.entity_overall.fp,
                "fn": self.entity_overall.fn,
                "precision": round(self.entity_overall.precision, 4),
                "recall": round(self.entity_overall.recall, 4),
                "f1": round(self.entity_overall.f1, 4),
            },
            "per_category": {
                cat: {
                    "tp": m.tp, "fp": m.fp, "fn": m.fn,
                    "precision": round(m.precision, 4),
                    "recall": round(m.recall, 4),
                    "f1": round(m.f1, 4),
                }
                for cat, m in sorted(self.per_category.items())
            },
            "false_positives": self.false_positives[:20],
            "false_negatives": self.false_negatives[:20],
        }


# ---------------------------------------------------------------------------
# Evaluation runner
# ---------------------------------------------------------------------------

def run_synthetic_evaluation(
    detector: Optional[PIIDetector] = None,
    min_score: float = 0.5,
) -> EvaluationReport:
    """
    Run the detector on the synthetic corpus and compute both exact entity-level
    and sentence-level binary classification metrics.
    """
    if detector is None:
        detector = PIIDetector(min_score=min_score)

    pos_sents = sum(1 for _, gt in SYNTHETIC_CORPUS if len(gt) > 0)
    neg_sents = sum(1 for _, gt in SYNTHETIC_CORPUS if len(gt) == 0)
    total_targets = sum(len(gt) for _, gt in SYNTHETIC_CORPUS)

    report = EvaluationReport(
        total_sentences=len(SYNTHETIC_CORPUS),
        positive_sentences=pos_sents,
        negative_sentences=neg_sents,
        total_target_entities=total_targets,
    )

    for text, ground_truth in SYNTHETIC_CORPUS:
        detected = detector.detect(text)

        # ── 1. Sentence-Level Binary Classification Evaluation ────────────────
        has_gt = len(ground_truth) > 0
        has_det = len(detected) > 0

        if has_gt and has_det:
            report.sentence_classification.tp += 1
        elif has_gt and not has_det:
            report.sentence_classification.fn += 1
        elif not has_gt and has_det:
            report.sentence_classification.fp += 1
        else:  # not has_gt and not has_det
            report.sentence_classification.tn += 1

        # ── 2. Exact Entity / Span-Level Evaluation ───────────────────────────
        # Exact match rule: start == gs AND end == ge AND entity_type == gt_type
        gt_matched = [False] * len(ground_truth)
        det_matched = [False] * len(detected)

        for d_idx, det in enumerate(detected):
            for g_idx, (gs, ge, gt_type) in enumerate(ground_truth):
                if gt_matched[g_idx]:
                    continue
                if det.start == gs and det.end == ge and det.entity_type == gt_type:
                    gt_matched[g_idx] = True
                    det_matched[d_idx] = True
                    report.entity_overall.tp += 1

                    if gt_type not in report.per_category:
                        report.per_category[gt_type] = CategoryMetrics()
                    report.per_category[gt_type].tp += 1
                    break

        # Unmatched detections are False Positives
        for d_idx, matched in enumerate(det_matched):
            if not matched:
                det = detected[d_idx]
                report.entity_overall.fp += 1
                cat = det.entity_type
                if cat not in report.per_category:
                    report.per_category[cat] = CategoryMetrics()
                report.per_category[cat].fp += 1
                report.false_positives.append({
                    "text": text,
                    "matched_text": text[det.start:det.end],
                    "entity_type": det.entity_type,
                    "score": round(det.score, 3),
                })

        # Unmatched ground-truth entities are False Negatives
        for g_idx, matched in enumerate(gt_matched):
            if not matched:
                gs, ge, gt_type = ground_truth[g_idx]
                report.entity_overall.fn += 1
                if gt_type not in report.per_category:
                    report.per_category[gt_type] = CategoryMetrics()
                report.per_category[gt_type].fn += 1
                report.false_negatives.append({
                    "text": text,
                    "missed_text": text[gs:ge],
                    "entity_type": gt_type,
                })

    return report


# ---------------------------------------------------------------------------
# Markdown report formatter
# ---------------------------------------------------------------------------

def format_report_markdown(
    eval_report: EvaluationReport,
    redaction_summary: Optional[Dict] = None,
    observed_fps: Optional[List[Tuple[str, str, str]]] = None,
) -> str:
    """Format the evaluation results as a submission-grade markdown report."""
    lines: List[str] = [
        "# PII Redaction Tool — Evaluation Report",
        "",
        "> **Methodology & Scope Notice**: Quantitative metrics in §1 are computed",
        f"> strictly against a curated synthetic ground-truth benchmark of {eval_report.total_sentences} sentences",
        f"> ({eval_report.positive_sentences} positive sentences containing {eval_report.total_target_entities} entity targets + {eval_report.negative_sentences} negative distractor sentences).",
        "> The actual Red Herring Prospectus was NOT hand-annotated line-by-line;",
        "> doing so for a full-length legal document (5,205 paragraphs across 76 tables) is not feasible.",
        "> Therefore §2 reports document-level *counts* only — NOT accuracy, precision, or recall —",
        "> and §3 provides qualitative observations from a manual spot-check of the redacted output.",
        "> **Do not interpret §1 synthetic benchmark metrics as real-document performance.**",
        "",
        "---",
        "",
        "## §1 — Synthetic Ground-Truth Evaluation",
        "",
        "**Test Corpus Composition**:",
        f"- Total sentences: **{eval_report.total_sentences}**",
        f"- Positive sentences (containing $\\ge 1$ PII entity): **{eval_report.positive_sentences}** (totaling **{eval_report.total_target_entities}** target entity spans)",
        f"- Negative sentences (containing 0 PII entities): **{eval_report.negative_sentences}** (distractor non-PII patterns)",
        "",
        "### Methodology: Separation of Evaluation Levels",
        "",
        "To ensure methodological rigor, evaluation is conducted at two distinct levels:",
        "1. **Sentence-Level Binary Classification** (Evaluation unit = *sentence*): Measures whether the system correctly decides if a sentence requires redaction or contains no PII. Because negative sentences provide well-defined negative instances, **Accuracy** and a full 2x2 confusion matrix (TP, TN, FP, FN) are calculated here.",
        "2. **Exact Entity / Span-Level Evaluation** (Evaluation unit = *entity span*): Measures exact span boundaries (`det.start == gs` and `det.end == ge`) and category classifications for each PII instance. True Negatives are mathematically undefined in unbounded text character span space, so **Precision**, **Recall**, and **F1 Score** are reported here without mixing sentence units.",
        "",
        "---",
        "",
        "### §1.1 — Sentence-Level Binary Classification (Accuracy)",
        "",
        "- **Positive Sentence**: Ground truth contains $\\ge 1$ PII target.",
        "- **Negative Sentence**: Ground truth contains 0 PII targets.",
        "- **Predicted Positive**: Detector found $\\ge 1$ PII entity.",
        "- **Predicted Negative**: Detector found 0 PII entities.",
        "",
        "| Metric | Value | Definition / Formula |",
        "|--------|-------|----------------------|",
        f"| True Positives (TP)  | {eval_report.sentence_classification.tp} | Positive sentences correctly identified as containing PII |",
        f"| True Negatives (TN)  | {eval_report.sentence_classification.tn} | Negative sentences correctly identified with 0 detections |",
        f"| False Positives (FP) | {eval_report.sentence_classification.fp} | Negative sentences falsely triggered by >= 1 detection |",
        f"| False Negatives (FN) | {eval_report.sentence_classification.fn} | Positive sentences where all PII entities were missed |",
        f"| **Accuracy**         | **{eval_report.sentence_classification.accuracy:.1%}** | $\\frac{{\\text{{TP}} + \\text{{TN}}}}{{\\text{{TP}} + \\text{{TN}} + \\text{{FP}} + \\text{{FN}}}} = \\frac{{{eval_report.sentence_classification.tp + eval_report.sentence_classification.tn}}}{{{eval_report.total_sentences}}}$ |",
        f"| **Precision**        | **{eval_report.sentence_classification.precision:.1%}** | $\\frac{{\\text{{TP}}}}{{\\text{{TP}} + \\text{{FP}}}} = \\frac{{{eval_report.sentence_classification.tp}}}{{{eval_report.sentence_classification.tp + eval_report.sentence_classification.fp}}}$ |",
        f"| **Recall**           | **{eval_report.sentence_classification.recall:.1%}** | $\\frac{{\\text{{TP}}}}{{\\text{{TP}} + \\text{{FN}}}} = \\frac{{{eval_report.sentence_classification.tp}}}{{{eval_report.sentence_classification.tp + eval_report.sentence_classification.fn}}}$ |",
        f"| **F1 Score**         | **{eval_report.sentence_classification.f1:.1%}** | $\\frac{{2 \\times P \\times R}}{{P + R}}$ |",
        "",
        "---",
        "",
        "### §1.2 — Exact Entity / Span-Level Evaluation (Precision, Recall, F1)",
        "",
        f"- **Total Target Entities**: {eval_report.total_target_entities} ground-truth spans",
        "- **Exact Matching Rule**: A True Positive requires exact start offset match, exact end offset match, and exact category match (`start == gs`, `end == ge`, `category == gt_type`).",
        "- **True Positives (TP)**: Ground-truth target entity correctly identified with exact span boundaries.",
        "- **False Positives (FP)**: Detected entity span that does not exactly match any ground-truth target entity.",
        "- **False Negatives (FN)**: Ground-truth target entity missed or detected with non-matching boundaries.",
        "",
        "| Metric | Value | Formula |",
        "|--------|-------|---------|",
        f"| True Positives (TP)  | {eval_report.entity_overall.tp} | Correctly detected target entity spans (exact boundary match) |",
        f"| False Positives (FP) | {eval_report.entity_overall.fp} | Erroneous / extra entity detections |",
        f"| False Negatives (FN) | {eval_report.entity_overall.fn} | Missed ground-truth entity spans |",
        f"| **Precision**        | **{eval_report.entity_overall.precision:.1%}** | $\\frac{{\\text{{TP}}}}{{\\text{{TP}} + \\text{{FP}}}} = \\frac{{{eval_report.entity_overall.tp}}}{{{eval_report.entity_overall.tp + eval_report.entity_overall.fp}}}$ |",
        f"| **Recall**           | **{eval_report.entity_overall.recall:.1%}** | $\\frac{{\\text{{TP}}}}{{\\text{{TP}} + \\text{{FN}}}} = \\frac{{{eval_report.entity_overall.tp}}}{{{eval_report.entity_overall.tp + eval_report.entity_overall.fn}}}$ |",
        f"| **F1 Score**         | **{eval_report.entity_overall.f1:.1%}** | $\\frac{{2 \\times \\text{{TP}}}}{{2 \\times \\text{{TP}} + \\text{{FP}} + \\text{{FN}}}}$ |",
        "",
        "#### Per-Category Exact Entity Breakdown",
        "",
        "| Category | TP | FP | FN | Precision | Recall | F1 |",
        "|----------|----|----|----|-----------:|-------:|---:|",
    ]

    for cat in sorted(eval_report.per_category.keys()):
        m = eval_report.per_category[cat]
        lines.append(
            f"| {cat} | {m.tp} | {m.fp} | {m.fn} | "
            f"{m.precision:.1%} | {m.recall:.1%} | {m.f1:.1%} |"
        )

    if eval_report.false_positives:
        lines += [
            "",
            "#### Entity-Level False Positives (FP)",
            "",
            "| Text excerpt | Detected as | Score |",
            "|---|---|---|",
        ]
        for fp in eval_report.false_positives[:15]:
            lines.append(f"| `{fp['text']}` | {fp['entity_type']} | {fp.get('score', 'N/A')} |")

    if eval_report.false_negatives:
        lines += [
            "",
            "#### Entity-Level False Negatives (FN)",
            "",
            "| Text excerpt | Missed | Entity type |",
            "|---|---|---|",
        ]
        for fn in eval_report.false_negatives[:15]:
            lines.append(f"| `{fn['text']}` | `{fn.get('missed_text', '')}` | {fn['entity_type']} |")

    lines += [
        "",
        "---",
        "",
        "## §2 — Document-Level Statistics (Red Herring Prospectus)",
        "",
        "> **Important**: The counts below are raw detection counts from",
        "> processing the full Red Herring Prospectus document (5,205 total paragraphs).",
        "> No manual line-by-line ground-truth annotation was performed on this",
        "> full document, so precision/recall/accuracy cannot be computed for the DOCX file.",
        "> Some detections may be false positives (see §3 for qualitative review).",
        "",
    ]

    if redaction_summary:
        lines += [
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total paragraphs processed | {redaction_summary.get('total_paragraphs', 5205)} (1,006 body + 4,199 in 76 tables) |",
            f"| Paragraphs with PII redacted | {redaction_summary.get('modified_paragraphs', 'N/A')} |",
            f"| Total PII instances redacted | {redaction_summary.get('total_entities_found', 'N/A')} |",
            "",
            "### PII Counts by Category",
            "",
            "| Category | Count |",
            "|----------|------:|",
        ]
        by_type = redaction_summary.get("by_type", {})
        for cat, cnt in sorted(by_type.items()):
            lines.append(f"| {cat} | {cnt} |")
    else:
        lines.append("*Run with `--evaluate` alongside the prospectus document to populate this section.*")

    lines += [
        "",
        "---",
        "",
        "## §3 — Qualitative False-Positive Observations (Prospectus Spot-Check)",
        "",
        "> These are qualitative observations from reviewing the verbose log",
        "> of the actual prospectus run. They are NOT computed metrics.",
        "> The real-document false-positive rate is unknown without full",
        "> hand-annotation of the 5,205 paragraphs.",
        "",
    ]

    if observed_fps:
        lines += [
            "| Original text | Entity type | Reason it's a FP |",
            "|---|---|---|",
        ]
        for item in observed_fps[:10]:
            if isinstance(item, dict):
                text, cat, reason = item.get("text", ""), item.get("entity_type", ""), item.get("reason", "")
            else:
                text, cat, reason = item
            lines.append(f"| `{text}` | {cat} | {reason} |")
    else:
        lines += [
            "| Original text | Entity type | Reason it's a FP |",
            "|---|---|---|",
            "| `141032` | ADDRESS | Numeric value |",
            "| `400083` | ADDRESS | Numeric value |",
            "| `400042` | ADDRESS | Numeric value |",
            "| `400020` | ADDRESS | Numeric value |",
            "| `400051` | ADDRESS | Numeric value |",
            "| `400025` | ADDRESS | Numeric value |",
            "| `140388` | ADDRESS | Numeric value |",
            "| `Schedule XIII` | PERSON | Document structure reference |",
        ]

    lines += [
        "",
        "---",
        "",
        "## §4 — Methodology Limitations",
        "",
        "1. **Synthetic corpus bias**: The test corpus was constructed by the",
        "   same team that built the tool. It may not fully represent the",
        "   distribution of PII in real legal/financial documents.",
        "",
        "2. **No ground-truth annotation for the full prospectus**: Because the",
        "   document contains 5,205 paragraphs and 76 tables, it was not hand-annotated.",
        "   Precision/recall/accuracy against the real document cannot be reported honestly.",
        "",
        "3. **Exact entity-span boundary sensitivity**: Exact span matching requires",
        "   both start and end offsets to match. For compound addresses (e.g.",
        "   `B Wing, 4th Floor, Ruby Tower, Mumbai`), the detector may identify",
        "   individual components separately, which registers as component false positives",
        "   and full-span false negatives under strict exact span evaluation.",
        "",
        "4. **NER sensitivity to domain language**: spaCy en_core_web_lg was",
        "   trained on news/web text. Legal/financial jargon may cause the NER",
        "   to miss or misclassify entities (e.g., Indian personal names,",
        "   company names in all-caps, or building/locality names).",
        "",
        "5. **Context window for DOB**: The 120-character context window for",
        "   DOB keyword detection is a heuristic. DOB references more than",
        "   120 chars from a keyword will be missed.",
        "",
        "6. **ORG recall on NER**: spaCy has lower recall for Indian company",
        "   names not well-represented in its training data. The OrgRecognizer",
        "   pattern recognizer supplements this but relies on legal-suffix",
        "   patterns and may miss names without a standard suffix.",
    ]

    return "\n".join(lines)
