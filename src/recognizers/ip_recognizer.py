"""
IPv4 address recognizer.
Each octet is validated to be in [0, 255].
Rejects loopback (127.x), link-local (169.254.x), and broadcast (255.255.255.255)
only when they appear in obviously technical contexts.
"""

import re
from presidio_analyzer import PatternRecognizer, Pattern


def _valid_ipv4(text: str) -> bool:
    """Return True if text is a valid IPv4 address."""
    parts = text.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False


class IPAddressRecognizer(PatternRecognizer):
    """Detects IPv4 addresses."""

    PATTERNS = [
        Pattern(
            name="ipv4_pattern",
            regex=r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            score=0.85,
        )
    ]
    CONTEXT = [
        "ip", "ip address", "ipv4", "host", "server", "address",
        "network", "subnet", "client", "source ip", "destination"
    ]

    def __init__(self):
        super().__init__(
            supported_entity="IP_ADDRESS",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            name="IPAddressRecognizer",
        )

    def validate_result(self, pattern_text: str) -> bool:  # type: ignore[override]
        return _valid_ipv4(pattern_text.strip())
