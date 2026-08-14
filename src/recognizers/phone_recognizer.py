"""
Phone number recognizer covering Indian (+91), Indian STD landlines, and international formats.
Does NOT match plain 4-digit or 5-digit numbers (page numbers, financial codes).
"""

from presidio_analyzer import PatternRecognizer, Pattern


class PhoneRecognizer(PatternRecognizer):
    """Detects Indian mobile, Indian landline, and international phone numbers."""

    PATTERNS = [
        # Indian +91 or + 91 landlines/mobiles with flexible spacing and grouping:
        # e.g., "+ 91 20 45053237", "+91 20 45053237", "+91-20-26234000", "+91 9876543210", "+91 22 6807 7100"
        Pattern(
            name="india_intl_landline_mobile",
            regex=r"(?:\+\s*91|091|\b91)[\s\-]*(?:\(?\d{2,4}\)?[\s\-]*)?\d{3,5}[\s\-]?\d{4,5}\b",
            score=0.95,
        ),
        # Indian STD landlines: 0XX-XXXXXXXX or 0XXX-XXXXXXX (e.g. 022-68052182, 020-26234000)
        Pattern(
            name="india_std_landline",
            regex=r"\b0\d{2,4}[\s\-]\d{6,8}\b",
            score=0.85,
        ),
        # Indian 10-digit mobile starting with 6-9 (standalone)
        Pattern(
            name="india_mobile_10",
            regex=r"(?<!\d)[6-9]\d{9}(?!\d)",
            score=0.65,
        ),
        # Indian Toll-free numbers: 1800-XXX-XXXX or 1800XXXXXX
        Pattern(
            name="india_toll_free",
            regex=r"\b1800[\s\-]?\d{3}[\s\-]?\d{3,4}\b",
            score=0.85,
        ),
        # International E.164: +CC followed by grouped digits (e.g. +1-800-555-0199)
        Pattern(
            name="intl_phone",
            regex=r"\+\d{1,3}[\s\-]?\(?\d{1,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4}\b",
            score=0.8,
        ),
        # US/Canada standard: (XXX) XXX-XXXX or XXX-XXX-XXXX
        Pattern(
            name="us_phone",
            regex=r"(?<!\d)\(?\d{3}\)?[\s\.\-]\d{3}[\s\.\-]\d{4}(?!\d)",
            score=0.75,
        ),
    ]
    CONTEXT = [
        "phone", "mobile", "cell", "contact", "tel", "telephone",
        "call", "reach", "whatsapp", "number", "fax", "helpline"
    ]

    def __init__(self):
        super().__init__(
            supported_entity="PHONE_NUMBER",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            name="PhoneRecognizer",
        )
