"""
tests/test_detector.py

Integration tests for the PIIDetector class.
"""

import pytest
from src.detector import PIIDetector


@pytest.fixture(scope="module")
def detector():
    """Shared detector instance (expensive to construct due to NLP model load)."""
    return PIIDetector(min_score=0.5)


class TestDetectorPositives:

    def test_detects_email(self, detector):
        entities = detector.detect("Email us at hello@example.com today.")
        types = [e.entity_type for e in entities]
        assert "EMAIL" in types

    def test_detects_phone_indian(self, detector):
        entities = detector.detect("Call us on +91 9876543210.")
        types = [e.entity_type for e in entities]
        assert "PHONE" in types

    def test_detects_ip_address(self, detector):
        entities = detector.detect("Server running at 192.168.0.1.")
        types = [e.entity_type for e in entities]
        assert "IP_ADDRESS" in types

    def test_detects_credit_card(self, detector):
        entities = detector.detect("Card number: 4111 1111 1111 1111.")
        types = [e.entity_type for e in entities]
        assert "CREDIT_CARD" in types

    def test_detects_ssn(self, detector):
        entities = detector.detect("SSN: 123-45-6789.")
        types = [e.entity_type for e in entities]
        assert "SSN" in types

    def test_detects_dob(self, detector):
        entities = detector.detect("Date of birth: 15/08/1985.")
        types = [e.entity_type for e in entities]
        assert "DATE_OF_BIRTH" in types


class TestDetectorFalsePositivePrevention:

    def test_currency_not_flagged(self, detector):
        entities = detector.detect("Revenue: ₹12,34,56,789 for FY2023.")
        types = [e.entity_type for e in entities]
        assert "CREDIT_CARD" not in types
        assert "PHONE" not in types

    def test_ordinary_date_not_dob(self, detector):
        entities = detector.detect("The AGM is on 15/08/2024.")
        types = [e.entity_type for e in entities]
        assert "DATE_OF_BIRTH" not in types

    def test_version_number_not_ip(self, detector):
        entities = detector.detect("Version 3.14 is available.")
        types = [e.entity_type for e in entities]
        # 3.14 has only 2 parts — cannot be flagged as IP
        assert "IP_ADDRESS" not in types

    def test_page_number_not_flagged(self, detector):
        entities = detector.detect("See page 42 for the financial summary.")
        # No PII here
        assert all(e.entity_type not in ("CREDIT_CARD", "PHONE", "SSN")
                   for e in entities)


class TestDetectorDeduplication:

    def test_no_overlapping_entities(self, detector):
        text = "Contact ravi.kumar@example.com for help."
        entities = detector.detect(text)
        spans = [(e.start, e.end) for e in entities]
        for i, (s1, e1) in enumerate(spans):
            for j, (s2, e2) in enumerate(spans):
                if i != j:
                    assert not (s1 < e2 and e1 > s2), \
                        f"Overlapping spans: ({s1},{e1}) and ({s2},{e2})"

    def test_consistency_same_entity(self, detector):
        text = "Send to alice@test.com and cc alice@test.com."
        entities = detector.detect(text)
        email_texts = [e.original_text for e in entities if e.entity_type == "EMAIL"]
        # Both occurrences must be detected
        assert len(email_texts) == 2
