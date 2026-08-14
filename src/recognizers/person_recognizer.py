"""
person_recognizer.py — Pattern-based recognizer for contextual personal names.

Supplements spaCy NER for cases where name prefixes (such as "Contact Person:",
"Name:") or following designation titles (such as "Company Secretary",
"Compliance Officer", "Managing Director") interfere with general NER span
tagging.
"""

from presidio_analyzer import PatternRecognizer, Pattern

_TITLE_WORDS = {
    "Company", "Secretary", "Compliance", "Officer", "Managing", "Director",
    "Chief", "Executive", "Technical", "Whole", "Time", "Financial",
    "Corporate", "General", "Manager", "Legal", "Counsel", "Head", "Lead",
    "Senior", "Partner", "Auditor", "Advocate", "Contact", "Person", "Name",
    "Promoter", "Key", "Management", "Personnel", "Our", "The"
}


class PersonRecognizer(PatternRecognizer):
    """
    Detects personal names appearing with explicit context prefixes
    (e.g., 'Contact Person: Sarthak Malvadkar') or followed by professional
    designations (e.g., 'Sarthak Malvadkar Company Secretary').
    """

    PATTERNS = [
        # Match name after 'Contact Person:' prefix
        Pattern(
            name="contact_person_prefix",
            regex=r"(?<=(?i:Contact\sPerson:\s))[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3}",
            score=0.85,
        ),
        # Match name after 'Name:' or 'Promoter:' prefix
        Pattern(
            name="name_prefix",
            regex=r"(?<=(?i:(?:Name|Promoter|Director):\s))[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3}",
            score=0.85,
        ),
        # Match name immediately followed by known corporate designations
        Pattern(
            name="person_followed_by_designation",
            regex=r"\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3}(?=\s+(?:Company\s+Secretary|Compliance\s+Officer|Managing\s+Director|Chief\s+Executive|Technical\s+Director|Whole-Time\s+Director))",
            score=0.85,
        ),
    ]

    def __init__(self):
        super().__init__(
            supported_entity="PERSON",
            patterns=self.PATTERNS,
            name="PersonRecognizer",
        )

    def validate_result(self, pattern_text: str) -> bool:
        words = pattern_text.strip().split()
        if any(w in _TITLE_WORDS for w in words):
            return False
        return len(words) >= 2
