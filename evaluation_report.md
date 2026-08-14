# PII Redaction Tool — Evaluation Report

> **Methodology & Scope Notice**: Quantitative metrics in §1 are computed
> strictly against a curated synthetic ground-truth benchmark of 87 sentences
> (69 positive sentences containing 74 entity targets + 18 negative distractor sentences).
> The actual Red Herring Prospectus was NOT hand-annotated line-by-line;
> doing so for a full-length legal document (5,205 paragraphs across 76 tables) is not feasible.
> Therefore §2 reports document-level *counts* only — NOT accuracy, precision, or recall —
> and §3 provides qualitative observations from a manual spot-check of the redacted output.
> **Do not interpret §1 synthetic benchmark metrics as real-document performance.**

---

## §1 — Synthetic Ground-Truth Evaluation

**Test Corpus Composition**:
- Total sentences: **87**
- Positive sentences (containing $\ge 1$ PII entity): **69** (totaling **74** target entity spans)
- Negative sentences (containing 0 PII entities): **18** (distractor non-PII patterns)

### Methodology: Separation of Evaluation Levels

To ensure methodological rigor, evaluation is conducted at two distinct levels:
1. **Sentence-Level Binary Classification** (Evaluation unit = *sentence*): Measures whether the system correctly decides if a sentence requires redaction or contains no PII. Because negative sentences provide well-defined negative instances, **Accuracy** and a full 2x2 confusion matrix (TP, TN, FP, FN) are calculated here.
2. **Exact Entity / Span-Level Evaluation** (Evaluation unit = *entity span*): Measures exact span boundaries (`det.start == gs` and `det.end == ge`) and category classifications for each PII instance. True Negatives are mathematically undefined in unbounded text character span space, so **Precision**, **Recall**, and **F1 Score** are reported here without mixing sentence units.

---

### §1.1 — Sentence-Level Binary Classification (Accuracy)

- **Positive Sentence**: Ground truth contains $\ge 1$ PII target.
- **Negative Sentence**: Ground truth contains 0 PII targets.
- **Predicted Positive**: Detector found $\ge 1$ PII entity.
- **Predicted Negative**: Detector found 0 PII entities.

| Metric | Value | Definition / Formula |
|--------|-------|----------------------|
| True Positives (TP)  | 69 | Positive sentences correctly identified as containing PII |
| True Negatives (TN)  | 17 | Negative sentences correctly identified with 0 detections |
| False Positives (FP) | 1 | Negative sentences falsely triggered by >= 1 detection |
| False Negatives (FN) | 0 | Positive sentences where all PII entities were missed |
| **Accuracy**         | **98.9%** | $\frac{\text{TP} + \text{TN}}{\text{TP} + \text{TN} + \text{FP} + \text{FN}} = \frac{86}{87}$ |
| **Precision**        | **98.6%** | $\frac{\text{TP}}{\text{TP} + \text{FP}} = \frac{69}{70}$ |
| **Recall**           | **100.0%** | $\frac{\text{TP}}{\text{TP} + \text{FN}} = \frac{69}{69}$ |
| **F1 Score**         | **99.3%** | $\frac{2 \times P \times R}{P + R}$ |

---

### §1.2 — Exact Entity / Span-Level Evaluation (Precision, Recall, F1)

- **Total Target Entities**: 74 ground-truth spans
- **Exact Matching Rule**: A True Positive requires exact start offset match, exact end offset match, and exact category match (`start == gs`, `end == ge`, `category == gt_type`).
- **True Positives (TP)**: Ground-truth target entity correctly identified with exact span boundaries.
- **False Positives (FP)**: Detected entity span that does not exactly match any ground-truth target entity.
- **False Negatives (FN)**: Ground-truth target entity missed or detected with non-matching boundaries.

| Metric | Value | Formula |
|--------|-------|---------|
| True Positives (TP)  | 61 | Correctly detected target entity spans (exact boundary match) |
| False Positives (FP) | 24 | Erroneous / extra entity detections |
| False Negatives (FN) | 13 | Missed ground-truth entity spans |
| **Precision**        | **71.8%** | $\frac{\text{TP}}{\text{TP} + \text{FP}} = \frac{61}{85}$ |
| **Recall**           | **82.4%** | $\frac{\text{TP}}{\text{TP} + \text{FN}} = \frac{61}{74}$ |
| **F1 Score**         | **76.7%** | $\frac{2 \times \text{TP}}{2 \times \text{TP} + \text{FP} + \text{FN}}$ |

#### Per-Category Exact Entity Breakdown

| Category | TP | FP | FN | Precision | Recall | F1 |
|----------|----|----|----|-----------:|-------:|---:|
| ADDRESS | 1 | 17 | 7 | 5.6% | 12.5% | 7.7% |
| CREDIT_CARD | 5 | 0 | 1 | 100.0% | 83.3% | 90.9% |
| DATE_OF_BIRTH | 6 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| EMAIL | 8 | 0 | 1 | 100.0% | 88.9% | 94.1% |
| IP_ADDRESS | 7 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| ORGANIZATION | 6 | 5 | 4 | 54.5% | 60.0% | 57.1% |
| PERSON | 15 | 2 | 0 | 88.2% | 100.0% | 93.8% |
| PHONE | 8 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| SSN | 5 | 0 | 0 | 100.0% | 100.0% | 100.0% |

#### Entity-Level False Positives (FP)

| Text excerpt | Detected as | Score |
|---|---|---|
| `The company Infosys Technologies submitted the filing.` | ORGANIZATION | 1.0 |
| `The promoter is Acme Pvt. Ltd.` | ORGANIZATION | 1.0 |
| `The auditor is Deloitte Haskins & Sells LLP.` | ORGANIZATION | 0.65 |
| `Kirtane & Pandit LLP is the statutory auditor.` | ORGANIZATION | 0.65 |
| `Reach Prakash at prakash.boricha@nuvama.com for IPO queries.` | PERSON | 0.85 |
| `Email ksh.ipo@nuvama.com for application forms.` | PERSON | 0.85 |
| `Amex card: 3782 822463 10005.` | ADDRESS | 0.75 |
| `Blocked IP: 198.51.100.5.` | ADDRESS | 0.95 |
| `Registered office: B Wing, 4th Floor, Ruby Tower, Mumbai.` | ADDRESS | 0.6 |
| `Registered office: B Wing, 4th Floor, Ruby Tower, Mumbai.` | ADDRESS | 0.95 |
| `Registered office: B Wing, 4th Floor, Ruby Tower, Mumbai.` | ADDRESS | 0.95 |
| `Registered office: B Wing, 4th Floor, Ruby Tower, Mumbai.` | ADDRESS | 0.85 |
| `Address: Plot No. 12, MIDC Industrial Area, Pune.` | ADDRESS | 0.95 |
| `Address: Plot No. 12, MIDC Industrial Area, Pune.` | ADDRESS | 0.85 |
| `Situated at Survey No. 341/2, Chakan, Pune - 411003.` | ADDRESS | 0.6 |

#### Entity-Level False Negatives (FN)

| Text excerpt | Missed | Entity type |
|---|---|---|
| `The company Infosys Technologies submitted the filing.` | `Infosys Technologies` | ORGANIZATION |
| `The promoter is Acme Pvt. Ltd.` | `Acme Pvt. Ltd.` | ORGANIZATION |
| `The auditor is Deloitte Haskins & Sells LLP.` | `Deloitte Haskins & Sells LLP` | ORGANIZATION |
| `Kirtane & Pandit LLP is the statutory auditor.` | `Kirtane & Pandit LLP` | ORGANIZATION |
| `Email ksh.ipo@nuvama.com for application forms.` | `ksh.ipo@nuvama.com` | EMAIL |
| `Amex card: 3782 822463 10005.` | `3782 822463 10005` | CREDIT_CARD |
| `Registered office: B Wing, 4th Floor, Ruby Tower, Mumbai.` | `B Wing, 4th Floor, Ruby Tower, Mumbai` | ADDRESS |
| `Address: Plot No. 12, MIDC Industrial Area, Pune.` | `Plot No. 12, MIDC Industrial Area, Pune` | ADDRESS |
| `Situated at Survey No. 341/2, Chakan, Pune - 411003.` | `Survey No. 341/2, Chakan, Pune - 411003` | ADDRESS |
| `Flat No. 5, Sector 17, Navi Mumbai - 400706.` | `Flat No. 5, Sector 17, Navi Mumbai - 400706` | ADDRESS |
| `House No. 22, MG Road, Bengaluru.` | `House No. 22, MG Road, Bengaluru` | ADDRESS |
| `Postal code: 400028.` | `400028` | ADDRESS |
| `Unit 8693 Box 0403, DPO AE 22546.` | `Unit 8693 Box 0403, DPO AE 22546` | ADDRESS |

---

## §2 — Document-Level Statistics (Red Herring Prospectus)

> **Important**: The counts below are raw detection counts from
> processing the full Red Herring Prospectus document (5,205 total paragraphs).
> No manual line-by-line ground-truth annotation was performed on this
> full document, so precision/recall/accuracy cannot be computed for the DOCX file.
> Some detections may be false positives (see §3 for qualitative review).

| Metric | Value |
|--------|-------|
| Total paragraphs processed | 5205 (1,006 body + 4,199 in 76 tables) |
| Paragraphs with PII redacted | 778 |
| Total PII instances redacted | 1660 |

### PII Counts by Category

| Category | Count |
|----------|------:|
| ADDRESS | 521 |
| EMAIL | 70 |
| ORGANIZATION | 414 |
| PERSON | 605 |
| PHONE | 50 |

---

## §3 — Qualitative False-Positive Observations (Prospectus Spot-Check)

> These are qualitative observations from reviewing the verbose log
> of the actual prospectus run. They are NOT computed metrics.
> The real-document false-positive rate is unknown without full
> hand-annotation of the 5,205 paragraphs.

| Original text | Entity type | Reason it's a FP |
|---|---|---|
| `141032` | ADDRESS | Numeric value |
| `400083` | ADDRESS | Numeric value |
| `400042` | ADDRESS | Numeric value |
| `400020` | ADDRESS | Numeric value |
| `400051` | ADDRESS | Numeric value |
| `400025` | ADDRESS | Numeric value |
| `140388` | ADDRESS | Numeric value |
| `Schedule XIII` | PERSON | Document structure reference |

---

## §4 — Methodology Limitations

1. **Synthetic corpus bias**: The test corpus was constructed by the
   same team that built the tool. It may not fully represent the
   distribution of PII in real legal/financial documents.

2. **No ground-truth annotation for the full prospectus**: Because the
   document contains 5,205 paragraphs and 76 tables, it was not hand-annotated.
   Precision/recall/accuracy against the real document cannot be reported honestly.

3. **Exact entity-span boundary sensitivity**: Exact span matching requires
   both start and end offsets to match. For compound addresses (e.g.
   `B Wing, 4th Floor, Ruby Tower, Mumbai`), the detector may identify
   individual components separately, which registers as component false positives
   and full-span false negatives under strict exact span evaluation.

4. **NER sensitivity to domain language**: spaCy en_core_web_lg was
   trained on news/web text. Legal/financial jargon may cause the NER
   to miss or misclassify entities (e.g., Indian personal names,
   company names in all-caps, or building/locality names).

5. **Context window for DOB**: The 120-character context window for
   DOB keyword detection is a heuristic. DOB references more than
   120 chars from a keyword will be missed.

6. **ORG recall on NER**: spaCy has lower recall for Indian company
   names not well-represented in its training data. The OrgRecognizer
   pattern recognizer supplements this but relies on legal-suffix
   patterns and may miss names without a standard suffix.