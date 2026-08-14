"""
US Social Security Number (SSN) recognizer.
Pattern: XXX-XX-XXXX — invalid SSNs (all-zeros sections) are excluded.
"""

import re
from presidio_analyzer import PatternRecognizer, Pattern


_INVALID_SSNS = {"000", "666"}
_INVALID_SECOND = {"00"}
_INVALID_LAST = {"0000"}


def _validate_ssn(text: str) -> bool:
    """Return True if text looks like a plausible SSN."""
    m = re.match(r"^(\d{3})-(\d{2})-(\d{4})$", text.strip())
    if not m:
        return False
    area, group, serial = m.group(1), m.group(2), m.group(3)
    if area in _INVALID_SSNS:
        return False
    if area.startswith("9"):          # ITIN range — treat as SSN-like
        pass
    if group in _INVALID_SECOND:
        return False
    if serial in _INVALID_LAST:
        return False
    return True


class SSNRecognizer(PatternRecognizer):
    """Detects Social Security Numbers in XXX-XX-XXXX format."""

    PATTERNS = [
        Pattern(
            name="ssn_pattern",
            regex=r"\b\d{3}-\d{2}-\d{4}\b",
            score=0.85,
        )
    ]
    CONTEXT = ["ssn", "social security", "social security number", "tin", "tax id"]

    def __init__(self):
        super().__init__(
            supported_entity="US_SSN",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            name="SSNRecognizer",
        )

    def validate_result(self, pattern_text: str) -> bool:  # type: ignore[override]
        return _validate_ssn(pattern_text)
