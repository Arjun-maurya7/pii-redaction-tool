"""
org_recognizer.py — Pattern-based recognizer for company/organization names.

Supplements spaCy NER for Indian company names that include legal suffixes
such as "Private Limited", "Limited", "LLP", "Pvt. Ltd.", etc.  These are
precisely the cases where the spaCy NER model (trained on news text) often
fails or where the detector's blocklist was previously over-filtering.

This recognizer uses regex patterns that look for a capitalised word sequence
followed by a known legal suffix.  Confidence is set conservatively (0.6) so
that very short single-word matches do not overwhelm the registry.
"""

from presidio_analyzer import PatternRecognizer, Pattern


# Any word sequence ending with an Indian/international legal suffix
_ORG_SUFFIXES = (
    r"(?:"
    r"Private\s+Limited"
    r"|Pvt\.?\s*Ltd\.?"
    r"|Public\s+Limited"
    r"|\bLimited\b"
    r"|\bLtd\.?"
    r"|\bLLP\b"
    r"|\bInc\.?"
    r"|\bCorp\.?"
    r"|\bCorporation\b"
    r"|\bEnterprises\b"
    r"|\bIndustries\b"
    r"|\bTechnologies\b"
    r"|\bSolutions\b"
    r"|\bServices\b"
    r"|\bHoldings\b"
    r"|\bGroup\b"
    r"|\bAssociates\b"
    r"|\bConsultants\b"
    r"|\bVentures\b"
    r"|\bInternational\b"
    r")"
)

# Pattern: one or more Title-cased words, then the suffix
# e.g. "KSH International Private Limited", "Wipro Limited", "Tata Corp."
_ORG_PATTERN = (
    r"\b(?:[A-Z][A-Za-z&\-\.]*(?:\s+[A-Z][A-Za-z&\-\.]*){0,5}\s+)"
    + _ORG_SUFFIXES
)


class OrgRecognizer(PatternRecognizer):
    """
    Detects company names that end with recognisable legal-entity suffixes.

    Works alongside spaCy NER — catches Indian company names that the NER
    model misses, especially when they appear without surrounding context.
    """

    PATTERNS = [
        Pattern(
            name="org_with_legal_suffix",
            regex=_ORG_PATTERN,
            score=0.65,
        )
    ]
    CONTEXT = [
        "company", "organization", "firm", "incorporated", "registered",
        "promoter", "director", "subsidiary", "associate", "partner",
        "issued by", "managed by", "owned by", "incorporated",
    ]

    def __init__(self):
        super().__init__(
            supported_entity="ORG",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            name="OrgRecognizer",
        )
