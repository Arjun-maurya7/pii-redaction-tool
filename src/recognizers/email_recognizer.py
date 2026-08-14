"""
Email address recognizer using a strict RFC-5321-flavoured regex.
Registered as a custom Presidio PatternRecognizer.
"""

from presidio_analyzer import PatternRecognizer, Pattern


class EmailRecognizer(PatternRecognizer):
    """Detects email addresses."""

    PATTERNS = [
        Pattern(
            name="email_pattern",
            regex=(
                r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
            ),
            score=0.95,
        )
    ]
    CONTEXT = ["email", "e-mail", "mail", "contact", "reach", "write to"]

    def __init__(self):
        super().__init__(
            supported_entity="EMAIL_ADDRESS",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            name="EmailRecognizer",
        )
