"""
Date of Birth recognizer.

Strategy:
  1. Detect date-like patterns (DD/MM/YYYY, MM-DD-YYYY, Month DD YYYY, etc.)
  2. Only confirm as DOB if one of the DOB_KEYWORDS appears within a
     CHARACTER_WINDOW on either side of the match.

This prevents ordinary prospectus dates (filing dates, meeting dates,
subscription periods, financial year boundaries) from being flagged as PII.
"""

import re
from typing import Optional, List

from presidio_analyzer import PatternRecognizer, Pattern, RecognizerResult
from presidio_analyzer.nlp_engine import NlpArtifacts
from presidio_analyzer import AnalysisExplanation


# How many characters left/right of the date we scan for DOB keywords
CHARACTER_WINDOW = 120

DOB_KEYWORDS = [
    "date of birth", "dob", "born on", "born", "birth date",
    "date of incorporation",   # sometimes used for company 'DOB'
    "age as on", "age:", "aged",
]

# Compiled keyword regex (case-insensitive)
_KW_RE = re.compile(
    r"(?i)\b(?:" + "|".join(re.escape(k) for k in DOB_KEYWORDS) + r")\b"
)

# Date patterns to detect
_DATE_PATTERNS = [
    # DD/MM/YYYY or MM/DD/YYYY
    r"\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4}\b",
    # YYYY-MM-DD (ISO)
    r"\b\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}\b",
    # Month DD, YYYY or DD Month YYYY
    (
        r"\b(?:January|February|March|April|May|June|July|August|September"
        r"|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct"
        r"|Nov|Dec)[\s,]+\d{1,2}[,\s]+\d{4}\b"
    ),
    r"\b\d{1,2}[\s]+(?:January|February|March|April|May|June|July|August"
    r"|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug"
    r"|Sep|Oct|Nov|Dec)[,\s]+\d{4}\b",
    # DD-Mon-YYYY
    r"\b\d{2}-[A-Za-z]{3}-\d{4}\b",
]

_DATE_RE = re.compile(
    r"(?:" + "|".join(_DATE_PATTERNS) + r")",
    re.IGNORECASE,
)


class DOBRecognizer(PatternRecognizer):
    """
    Detects dates-of-birth.
    A date is only flagged as DOB when a DOB keyword appears within
    CHARACTER_WINDOW characters of the match in the same text span.
    """

    PATTERNS = [
        Pattern(
            name="dob_date_pattern",
            regex=r"(?:" + "|".join(_DATE_PATTERNS) + r")",
            score=0.01,   # starts very low; bumped by context check
        )
    ]

    def __init__(self):
        super().__init__(
            supported_entity="DATE_OF_BIRTH",
            patterns=self.PATTERNS,
            context=DOB_KEYWORDS,
            name="DOBRecognizer",
        )

    def analyze(
        self,
        text: str,
        entities: List[str],
        nlp_artifacts: Optional[NlpArtifacts] = None,
    ) -> List[RecognizerResult]:
        results: List[RecognizerResult] = []

        if "DATE_OF_BIRTH" not in entities:
            return results

        for m in _DATE_RE.finditer(text):
            start, end = m.start(), m.end()
            # Examine the surrounding window for a DOB keyword
            window_start = max(0, start - CHARACTER_WINDOW)
            window_end = min(len(text), end + CHARACTER_WINDOW)
            window = text[window_start:window_end]
            if _KW_RE.search(window):
                results.append(
                    RecognizerResult(
                        entity_type="DATE_OF_BIRTH",
                        start=start,
                        end=end,
                        score=0.88,
                        analysis_explanation=AnalysisExplanation(
                            recognizer=self.__class__.__name__,
                            original_score=0.88,
                            pattern_name="dob_context_window",
                            pattern=_DATE_RE.pattern[:80],
                            validation_result=None,
                            textual_explanation="Date found near DOB keyword",
                        ),
                    )
                )
        return results
