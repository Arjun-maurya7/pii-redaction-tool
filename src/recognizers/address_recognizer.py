"""
address_recognizer.py — Contextual recognizer for physical/mailing addresses.

Extends the NER-based LOCATION/GPE detection with two complementary patterns:

1. **PIN-code pattern** – Indian 6-digit postal codes (with PIN/Postal keyword
   or standalone 6-digit codes).

2. **Street/building address pattern** – Sequences that combine floor, plot,
   survey, flat, house, wing, sector, or road/street/nagar/colony keywords.

Both patterns use word-boundary guards to avoid matching financial figures,
section numbers, or version numbers.
"""

from presidio_analyzer import PatternRecognizer, Pattern


# ── 1. Indian PIN code ────────────────────────────────────────────────────────
_PIN_REGEX = (
    r"(?i)"
    r"(?:pin(?:\s*code)?|postal(?:\s*code)?|pin)\s*[:\-]?\s*[1-9]\d{5}"
    r"|\b[1-9]\d{5}\b"
)

# ── 2. Street / building address phrases ─────────────────────────────────────
_STREET_REGEX = (
    r"(?i)\b(?:"
    r"(?:\d{1,2}(?:st|nd|rd|th)?\s+Floor|[A-Z\d]+\s+Floor|Floor\s+[A-Z\d]+)"
    r"|(?:Plot|Survey|Khasra|Gat|House|Flat|Shop|Unit)\s*(?:No\.?|Number|#)?\s*[\w\d/]+(?:\s*,\s*[\w\s]+)?"
    r"|[A-Z\d]\s*[-–]?\s*Wing\b"
    r"|(?:Sector|Phase|Block)\s*[-–]?\s*[A-Z\d]+"
    r"|(?:[A-Z][\w\.\s]{1,30}?(?:Road|Street|Marg|Path|Lane|Avenue|Nagar|Colony|Vihar|Enclave|Industrial Area|Complex|Tower|Towers))\b"
    r")"
)


class AddressRecognizer(PatternRecognizer):
    """
    Detects Indian physical/mailing addresses that NER misses:
      - 6-digit PIN codes (with or without "PIN" keyword)
      - Street/plot/floor/sector/road style address fragments
    """

    PATTERNS = [
        Pattern(
            name="indian_pin_code",
            regex=_PIN_REGEX,
            score=0.75,
        ),
        Pattern(
            name="street_address_fragment",
            regex=_STREET_REGEX,
            score=0.60,
        ),
    ]
    CONTEXT = [
        "address", "located", "registered office", "corporate office",
        "correspondence", "premises", "situated", "residing", "resident",
        "road", "street", "nagar", "colony", "floor", "plot", "wing",
        "sector", "phase", "block", "pin", "pincode", "postal",
    ]

    def __init__(self):
        super().__init__(
            supported_entity="LOCATION",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            name="AddressRecognizer",
        )
