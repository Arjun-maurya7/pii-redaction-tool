"""
Credit card number recognizer with Luhn algorithm validation.

Only 13-19 digit sequences (with optional spaces/dashes between groups) that
pass the Luhn check are flagged. This prevents financial amounts, account
numbers, and CIN/LLPIN identifiers from being redacted.
"""

import re
from presidio_analyzer import PatternRecognizer, Pattern


def _luhn_check(number: str) -> bool:
    """Return True if *number* (digits only) passes the Luhn algorithm."""
    digits = [int(d) for d in number]
    digits.reverse()
    total = 0
    for i, d in enumerate(digits):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


# Matches 13-19 digit groups separated by spaces or dashes
_CC_REGEX = (
    r"(?<!\d)"
    r"(?:\d{4}[\s\-]){3}\d{1,4}"       # 4-4-4-4 (most common)
    r"|(?:\d{4}[\s\-]){2}\d{4,6}"       # Amex: 4-4-6
    r"|\d{13,19}"                         # Unseparated
    r"(?!\d)"
)

# Negative: if preceded/followed by ₹, $, %, or 'Rs' it's a financial amount
_AMOUNT_PREFIX = re.compile(r"(?:₹|Rs\.?|\$|€|£|\bINR\b)\s*$")


class CreditCardRecognizer(PatternRecognizer):
    """Detects credit/debit card numbers; validates with Luhn check."""

    PATTERNS = [
        Pattern(
            name="credit_card_pattern",
            regex=_CC_REGEX,
            score=0.75,
        )
    ]
    CONTEXT = [
        "card", "credit", "debit", "visa", "mastercard", "amex", "rupay",
        "payment", "card number", "pan", "cvv"
    ]

    def __init__(self):
        super().__init__(
            supported_entity="CREDIT_CARD",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            name="CreditCardRecognizer",
        )

    def validate_result(self, pattern_text: str) -> bool:  # type: ignore[override]
        digits_only = re.sub(r"[\s\-]", "", pattern_text)
        if not digits_only.isdigit():
            return False
        if not (13 <= len(digits_only) <= 19):
            return False
        return _luhn_check(digits_only)
