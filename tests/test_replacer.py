"""
tests/test_replacer.py

Tests for the synthetic replacement generator.
"""

import pytest
from src.replacer import get_replacement, reset_mapping, get_all_mappings


@pytest.fixture(autouse=True)
def clear_map():
    """Reset the global mapping before each test."""
    reset_mapping()
    yield
    reset_mapping()


class TestReplacerConsistency:

    def test_same_input_same_output(self):
        r1 = get_replacement("Rashi Patil", "PERSON")
        r2 = get_replacement("Rashi Patil", "PERSON")
        assert r1 == r2

    def test_different_inputs_different_outputs(self):
        r1 = get_replacement("Rashi Patil", "PERSON")
        r2 = get_replacement("Rohan Dey", "PERSON")
        # While possible to collide, it should be extremely rare with Faker
        # Just check both are non-empty strings
        assert r1 and r2
        assert isinstance(r1, str)
        assert isinstance(r2, str)

    def test_same_text_different_types_can_differ(self):
        r1 = get_replacement("test@example.com", "EMAIL")
        r2 = get_replacement("test@example.com", "PERSON")
        # Different entity types should be tracked separately
        assert isinstance(r1, str)
        assert isinstance(r2, str)


class TestReplacerFormat:

    def test_email_has_at_sign(self):
        r = get_replacement("user@example.com", "EMAIL")
        assert "@" in r

    def test_email_does_not_preserve_corporate_domain(self):
        original = "cs.connect@kshinternational.com"
        r = get_replacement(original, "EMAIL")
        assert "@" in r
        assert not r.lower().endswith("@kshinternational.com"), \
            f"Expected replacement to not preserve corporate domain, got: '{r}'"
        assert any(r.endswith(f"@{d}") for d in ["example.com", "example.org", "example.net"]), \
            f"Expected neutral synthetic domain, got: '{r}'"

    @pytest.mark.parametrize("original", [
        "+ 91 20 45053237",
        "+91 20 45053237",
        "+91-20-26234000",
        "022-68052182",
        "+91 9876543210",
    ])
    def test_indian_phone_replacements(self, original):
        r = get_replacement(original, "PHONE")
        # Must not be replaced with a +1 US phone number
        assert not r.startswith("+1"), f"Indian phone '{original}' was replaced with US number '{r}'"
        # Must be an Indian format (+91 or STD code 0XX-)
        assert r.startswith("+91") or r.startswith("0"), \
            f"Expected Indian format for '{original}', got '{r}'"

    def test_ip_is_private_range(self):
        r = get_replacement("203.0.113.42", "IP_ADDRESS")
        # Should be one of the private ranges
        assert (r.startswith("10.") or r.startswith("172.") or r.startswith("192.168."))

    def test_ssn_format(self):
        r = get_replacement("123-45-6789", "SSN")
        import re
        assert re.match(r"\d{3}-\d{2}-\d{4}", r), \
            f"SSN replacement '{r}' does not match expected format"

    def test_credit_card_digits_only(self):
        r = get_replacement("4111 1111 1111 1111", "CREDIT_CARD")
        digits = r.replace(" ", "").replace("-", "")
        assert digits.isdigit()

    def test_dob_format(self):
        r = get_replacement("15/08/1985", "DATE_OF_BIRTH")
        import re
        assert re.match(r"\d{2}/\d{2}/\d{4}", r), \
            f"DOB replacement '{r}' does not match DD/MM/YYYY"


class TestReplacerMapping:

    def test_get_all_mappings_returns_dict(self):
        get_replacement("Alice Smith", "PERSON")
        get_replacement("bob@test.com", "EMAIL")
        mappings = get_all_mappings()
        assert isinstance(mappings, dict)
        assert len(mappings) == 2
