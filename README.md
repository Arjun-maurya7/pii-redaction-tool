# PII Redaction Tool — DOCX Anonymizer

A modular PII (Personally Identifiable Information) detection and synthetic replacement system for legal and financial DOCX documents. Built for the Scaler AI Labs assignment demonstration.

---

## Overview

The **PII Redaction Tool** is a hybrid natural language processing and pattern-matching system designed to scan Microsoft Word (`.docx`) documents, detect personally identifiable information across 9 standard and regulatory categories, and substitute each instance with a realistic, deterministic synthetic replacement while preserving document formatting and table layouts.

The tool provides both a **Command Line Interface (CLI)** for batch file processing and a **FastAPI Web Service** for cloud deployment and interactive browser uploads.

---

## Required PII Types

The system detects and redacts 9 distinct PII categories:

1. **PERSON**: Full personal names, promoter names, signatory names, and contextual designations (e.g., *Contact Person: Sarthak Malvadkar, Company Secretary*).
2. **EMAIL**: RFC 5321 compliant email addresses (e.g., *cs.connect@kshinternational.com*).
3. **PHONE**: Indian mobile numbers (`+91` 10-digit), Indian STD landlines (`+ 91 20 45053237`, `022-68052182`, `+91-20-26234000`), toll-free numbers (`1800-XXX-XXXX`), and international E.164 numbers.
4. **ORGANIZATION**: Indian and global corporate entities, statutory auditors, legal counsel, and banking partners with legal suffixes (`Limited`, `Private Limited`, `Pvt. Ltd.`, `LLP`, `Inc.`, `Corp.`, etc.).
5. **ADDRESS**: Physical addresses, Indian 6-digit PIN codes (`411001`), and multi-component building/plot/floor/road/sector patterns.
6. **SSN**: United States Social Security Numbers (`XXX-XX-XXXX`) with SSA area/group number validation.
7. **CREDIT_CARD**: 13–19 digit Visa, MasterCard, Amex, and RuPay card numbers verified via the **Luhn Algorithm**.
8. **DATE_OF_BIRTH**: Personal birth dates identified using a **semantic context window** to avoid redacting operational, incorporation, or financial dates.
9. **IP_ADDRESS**: IPv4 addresses with 4-octet numeric range verification ($0 \le \text{octet} \le 255$).

---

## Architecture

The system employs a modular, pipeline-based hybrid architecture:

```
                  ┌───────────────────────────────┐
                  │      Input DOCX Document      │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │ python-docx Document Iterator │
                  │  (Body Paragraphs & Tables)   │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │      PII Detection Engine     │
                  │   • Presidio Analyzer Engine  │
                  │   • spaCy en_core_web_lg NER  │
                  │   • 9 Custom Regex Recognizers│
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │  Validation & Context Guards  │
                  │   • Luhn Algorithm Checksum   │
                  │   • DOB Context Window (±120c)│
                  │   • Regulatory Blocklists     │
                  │   • Span Conflict Resolution  │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │  Faker Synthetic Generator    │
                  │   • Deterministic Key Mapping │
                  │   • Neutral Email Domains     │
                  │   • Regional Indian Phones    │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │   Redacted Output DOCX File   │
                  │   (Preserved Styles & Tables) │
                  └───────────────────────────────┘
```

---

## Detection Approach

1. **Microsoft Presidio Analyzer**: Coordinates recognizers, handles entity confidence scoring, and executes regex pattern matching.
2. **spaCy NER (`en_core_web_lg`)**: Detects unstructured `PERSON`, `ORG`, `LOCATION`, and `GPE` entities in natural prose.
3. **9 Custom Recognizers**:
   - `EmailRecognizer`: Pattern matching with RFC 5321 compliance and boundary guards against URLs and mathematical ratios.
   - `PhoneRecognizer`: Regex patterns matching Indian landlines with separated STD codes (`+ 91 20 ...`, `022-...`, `+91-20-...`), mobile numbers, toll-free, and international formats.
   - `SSNRecognizer`: Validates 9-digit SSN format (`XXX-XX-XXXX`) against US SSA area/group rules.
   - `CreditCardRecognizer`: Pattern extractor paired with strict **Luhn algorithm checksum** validation to prevent financial totals or order IDs from being falsely flagged.
   - `IPAddressRecognizer`: Validates IPv4 4-octet numeric ranges ($0 \le \text{octet} \le 255$).
   - `DOBRecognizer`: Evaluates candidate dates against a **$\pm 120$-character semantic context window** for keywords (`born`, `date of birth`, `DOB`, `birth date`), leaving ordinary financial/filing dates untouched.
   - `OrgRecognizer`: Captures corporate entities with statutory suffixes (`Private Limited`, `Limited`, `LLP`, `Pvt Ltd`) without over-filtering.
   - `AddressRecognizer`: Detects 6-digit Indian PIN codes and structured street/building/plot/floor patterns.
   - `PersonRecognizer`: Contextual detector for personal names preceding or following corporate positions (`Contact Person: ...`, `Company Secretary and Compliance Officer`).

---

## Replacement Strategy

- **Deterministic Global Mapping**: The system maintains an in-memory dictionary mapping `(original_text, entity_type)` to `synthetic_replacement`. The same person, company, email, or phone number receives the exact same synthetic replacement across every paragraph and table in the document.
- **Realistic Synthetic Generation**: Uses Faker (`en_IN` and `en_US` locales) to generate realistic names, addresses, and identifiers.
- **Neutral Synthetic Email Domains**: Synthetic email addresses are generated with neutral test domains (`example.com`, `example.org`, `example.net`) rather than preserving proprietary corporate domains.
- **Indian Phone Number Replacement**: Indian numbers (`+91` or STD landlines) receive realistic Indian synthetic replacements beginning with `+91` or valid STD prefixes, never US `+1` numbers.

---

## Evaluation Benchmark & Document Results

Evaluation is strictly partitioned into two separate levels to maintain mathematical rigor:

### 1. Synthetic Ground-Truth Benchmark (87 Curated Sentences)

#### Level 1: Sentence-Level Binary Classification (Accuracy)
- **Unit of Evaluation**: Individual sentence (69 positive containing $\ge 1$ PII entity, 18 negative distractor sentences).
- **Confusion Matrix**:
  - True Positives (TP): **69**
  - True Negatives (TN): **17**
  - False Positives (FP): **1**
  - False Negatives (FN): **0**
- **Accuracy**: **98.9%** ($\frac{\text{TP} + \text{TN}}{\text{Total}} = \frac{69 + 17}{87} = \frac{86}{87}$)
- **Precision**: **98.6%** ($\frac{69}{69 + 1}$)
- **Recall**: **100.0%** ($\frac{69}{69 + 0}$)
- **F1 Score**: **99.3%**

#### Level 2: Exact Entity / Span-Level Detection (74 Ground-Truth Targets)
- **Matching Rule**: True Positive requires exact start character offset, exact end character offset, and matching category (`det.start == gs and det.end == ge and det.entity_type == gt_type`).
- **Counts**:
  - True Positives (TP): **61**
  - False Positives (FP): **24**
  - False Negatives (FN): **13**
- **Precision**: **71.8%** ($\frac{61}{61 + 24} = \frac{61}{85}$)
- **Recall**: **82.4%** ($\frac{61}{61 + 13} = \frac{61}{74}$)
- **F1 Score**: **76.7%** ($\frac{2 \times \text{TP}}{2 \times \text{TP} + \text{FP} + \text{FN}}$)

### 2. Full Prospectus Processing Statistics (`Red Herring Prospectus (2).docx`)

- **Total Paragraphs Processed**: **5,205 paragraphs** (1,006 body paragraphs + 4,199 table cell paragraphs across 76 tables).
- **Paragraphs Modified**: **778 paragraphs**.
- **Total PII Entities Redacted**: **1,660 entities**:
  - **PERSON**: 605
  - **ADDRESS**: 521
  - **ORGANIZATION**: 414
  - **EMAIL**: 70
  - **PHONE**: 50

*Verification: Target prospectus entities (e.g. `+ 91 20 45053237`, `+91 20 45053237`, `022-68052182`, `+91-20-26234000`, `Sarthak Malvadkar`, `cs.connect@kshinternational.com`) are 100% absent in `redacted_output.docx`.*

---

## Known Limitations

1. **Exact Span Boundary Sensitivity**: Under strict exact span matching, compound address phrases (e.g. `B Wing, 4th Floor, Ruby Tower, Mumbai`) detected as individual constituent components register as component FPs and compound-span FNs.
2. **No Full Line-by-Line Ground Truth for Prospectus**: Due to the massive size of the legal document (5,205 paragraphs across 76 tables), the DOCX statistics report raw detection counts. Precision/recall cannot be claimed on the full DOCX without exhaustive manual annotation.
3. **General NER Domain Language**: spaCy's `en_core_web_lg` model is trained on news corpora and may occasionally misclassify unfamiliar Indian localities (e.g. `Baner`, `Kanjurmarg`) as personal names or miss company names lacking legal entity suffixes.
4. **DOCX Multi-Run XML Formatting**: When a detected entity spans across multiple internal XML runs with differing inline formatting (e.g. half-bold), the replacement text adopts the dominant paragraph style to avoid corrupted character boundaries.

---

## Local Setup

### 1. Clone & Environment Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Windows (cmd):
.venv\Scripts\activate.bat
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies (requirements.txt includes the spaCy en_core_web_lg model)
pip install -r requirements.txt
```

---

## Running the Application

### 1. Command Line Redactor (CLI)

```bash
# Redact default prospectus and generate evaluation_report.md
python pii_redactor.py --evaluate --verbose

# Custom input/output paths
python pii_redactor.py --input "my_document.docx" --output "my_redacted.docx" --verbose
```

### 2. FastAPI Web Application (Local Cloud Demo)

```bash
# Start FastAPI development server
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```
Open your browser and navigate to `http://127.0.0.1:8000` to access the web interface.

---

## Testing

Run the automated test suite with pytest:

```bash
python -m pytest -q
```
**Expected Result**: `117 passed in ~40s`

Test suite coverage across all 6 test modules:
- `tests/test_recognizers.py`: Unit tests for all 9 custom recognizers (Email, Phone, SSN, Credit Card, IP Address, DOB, Organization, Address, Person), Luhn validation, IP validation, SSN rules, DOB context rules, and Indian phone formats.
- `tests/test_detector.py`: Integration tests for Presidio + spaCy NER detection and confidence thresholds.
- `tests/test_replacer.py`: Deterministic replacement mapping, neutral email domains, and Indian phone formats.
- `tests/test_redactor.py`: End-to-end DOCX redaction and paragraph replacement.
- `tests/test_evaluator_helper.py`: Synthetic ground-truth span derivation and exact entity matching.
- `tests/test_app.py`: FastAPI endpoint tests (`GET /`, `GET /health`, `POST /redact`).

---

## Deploying to Render

This application is configured for deployment on [Render](https://render.com) via [`render.yaml`](render.yaml) or manual Web Service setup.

### Deployment Steps on Render:

1. **Push Clean Code to GitHub**:
   Ensure sensitive source documents (`Red Herring Prospectus*.docx`, `Enterprise Data*.docx`) are ignored by `.gitignore` and not committed.
2. **Create New Web Service on Render**:
   - Connect your GitHub repository.
   - **Environment**: `Python 3`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     uvicorn app:app --host 0.0.0.0 --port $PORT
     ```
   - **Plan**: Free
3. **Health Check Endpoint**: Set health check path to `/health`.
4. **Deploy**: Click **Create Web Service**. Once deployed, Render provides a public URL (e.g. `https://pii-redaction-service.onrender.com`).

---

## Cloud Security & Privacy Notice

- **Ephemeral Processing**: Uploaded documents are processed entirely in temporary isolated storage and immediately purged after the download stream finishes.
- **No PII Logging**: Document contents and detected PII entities are never logged to console or stored on disk.
- **File Limits**: Uploads are restricted to valid Word `.docx` documents up to 25 MB.
- **Demonstration Service**: This cloud deployment is provided as an assignment demonstration interface for academic evaluation.
