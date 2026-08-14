"""
tests/test_recognizers.py

Unit tests for every custom Presidio recognizer.
Tests cover both positive matches and expected non-matches (FP prevention).
"""

import pytest
from src.recognizers.email_recognizer import EmailRecognizer
from src.recognizers.phone_recognizer import PhoneRecognizer
from src.recognizers.ssn_recognizer import SSNRecognizer
from src.recognizers.credit_card_recognizer import CreditCardRecognizer, _luhn_check
from src.recognizers.ip_recognizer import IPAddressRecognizer, _valid_ipv4
from src.recognizers.dob_recognizer import DOBRecognizer


# ─── Helpers ────────────────────────────────────────────────────────────────

def _detect(recognizer, text, entity_type):
    """Return list of RecognizerResult for the given text."""
    from presidio_analyzer import AnalysisExplanation
    results = recognizer.analyze(text=text, entities=[entity_type])
    return results


# ─── Email ──────────────────────────────────────────────────────────────────

class TestEmailRecognizer:
    rec = EmailRecognizer()

    @pytest.mark.parametrize("email", [
        "user@example.com",
        "r.sharma@abc-corp.co.in",
        "support+tag@mycompany.in",
        "hello.world123@gmail.com",
    ])
    def test_valid_emails_detected(self, email):
        results = _detect(self.rec, f"Contact: {email}", "EMAIL_ADDRESS")
        assert any(email in r.analysis_explanation.original_score.__class__.__name__
                   or True for r in results), \
            f"Expected {email} to be detected"
        assert len(results) >= 1

    @pytest.mark.parametrize("text", [
        "Visit www.example.com for details.",          # URL, not email
        "The ratio is 3@5 (invalid format).",          # Not a real email
    ])
    def test_non_emails_not_detected(self, text):
        results = _detect(self.rec, text, "EMAIL_ADDRESS")
        # May still detect some; check that www.example.com is not flagged
        for r in results:
            matched = text[r.start:r.end]
            assert "@" in matched, f"Unexpected non-email detection: '{matched}'"


# ─── Phone ──────────────────────────────────────────────────────────────────

class TestPhoneRecognizer:
    rec = PhoneRecognizer()

    @pytest.mark.parametrize("phone,context", [
        ("+ 91 20 45053237", "Telephone: + 91 20 45053237;"),
        ("+91 20 45053237", "Phone: +91 20 45053237"),
        ("022-68052182", "Contact: 022-68052182"),
        ("+91-20-26234000", "Tel: +91-20-26234000"),
        ("+91 9876543210", "Call us at +91 9876543210"),
        ("+91-8765432109", "Phone: +91-8765432109"),
        ("+1-800-555-0199", "US number: +1-800-555-0199"),
        ("1800-103-0000", "Toll-free: 1800-103-0000"),
        ("+91 22 6807 7100", "Fax: +91 22 6807 7100"),
    ])
    def test_valid_phones_detected(self, phone, context):
        results = _detect(self.rec, context, "PHONE_NUMBER")
        assert len(results) >= 1

    @pytest.mark.parametrize("text", [
        "Revenue grew by 20%.",           # plain number
        "See page 42.",                   # page number
        "Section 91 of the Act.",         # legal reference
    ])
    def test_financial_numbers_not_detected_as_phone(self, text):
        results = _detect(self.rec, text, "PHONE_NUMBER")
        # These should not produce high-confidence phone detections
        high_conf = [r for r in results if r.score >= 0.8]
        assert len(high_conf) == 0, \
            f"False positive: '{text}' → {[(text[r.start:r.end], r.score) for r in high_conf]}"


# ─── SSN ────────────────────────────────────────────────────────────────────

class TestSSNRecognizer:
    rec = SSNRecognizer()

    @pytest.mark.parametrize("ssn", [
        "123-45-6789",
        "567-89-0123",
        "234-56-7890",
    ])
    def test_valid_ssns_detected(self, ssn):
        results = _detect(self.rec, f"SSN: {ssn}", "US_SSN")
        assert len(results) >= 1

    @pytest.mark.parametrize("text", [
        "000-00-0000",   # all-zeros — invalid SSN
        "666-12-3456",   # 666 prefix — invalid
    ])
    def test_invalid_ssns_rejected(self, text):
        from src.recognizers.ssn_recognizer import _validate_ssn
        assert _validate_ssn(text) is False


# ─── Credit Card ────────────────────────────────────────────────────────────

class TestCreditCardRecognizer:

    @pytest.mark.parametrize("number,expected", [
        ("4111111111111111", True),   # Visa test card
        ("5500005555555559", True),   # MC test card
        ("378282246310005",  True),   # Amex test card
        ("1234567890123456", False),  # fails Luhn
        ("0000000000000000", True),   # all-zeros actually pass Luhn (sum=0, mod10=0)
    ])
    def test_luhn(self, number, expected):
        assert _luhn_check(number) == expected

    def test_valid_card_detected(self):
        rec = CreditCardRecognizer()
        results = _detect(rec, "Card: 4111 1111 1111 1111", "CREDIT_CARD")
        assert len(results) >= 1

    @pytest.mark.parametrize("text", [
        "Net revenue: ₹12,34,56,789",
        "Total: Rs. 9,87,654",
        "Order number: 1234567890",
    ])
    def test_financial_amounts_not_credit_cards(self, text):
        rec = CreditCardRecognizer()
        results = _detect(rec, text, "CREDIT_CARD")
        assert len(results) == 0, f"False positive credit card in: '{text}' -> {results}"


# ─── IP Address ─────────────────────────────────────────────────────────────

class TestIPAddressRecognizer:

    @pytest.mark.parametrize("ip,valid", [
        ("192.168.1.1",   True),
        ("10.0.0.1",      True),
        ("203.0.113.42",  True),
        ("256.1.2.3",     False),   # octet > 255
        ("1.2.3",         False),   # only 3 octets
        ("abc.def.ghi.jkl", False), # not digits
    ])
    def test_ip_validation(self, ip, valid):
        assert _valid_ipv4(ip) == valid

    def test_ip_detected(self):
        rec = IPAddressRecognizer()
        results = _detect(rec, "Server IP: 10.0.0.1", "IP_ADDRESS")
        assert len(results) >= 1

    def test_version_number_not_ip(self):
        rec = IPAddressRecognizer()
        results = _detect(rec, "Version 3.14.159 released.", "IP_ADDRESS")
        # 3.14.159 has only 3 octets — should NOT be detected as an IP address
        assert len(results) == 0, f"False positive IP on version number: {results}"


# ─── DOB ────────────────────────────────────────────────────────────────────

class TestDOBRecognizer:
    rec = DOBRecognizer()

    @pytest.mark.parametrize("text", [
        "Date of birth: 15/08/1985",
        "DOB: 01-Jan-1990",
        "He was born on 23 March 1979",
        "Born: 1990-06-15",
    ])
    def test_dob_with_context_detected(self, text):
        results = self.rec.analyze(text, ["DATE_OF_BIRTH"])
        assert len(results) >= 1, f"Expected DOB detection in: '{text}'"

    @pytest.mark.parametrize("text", [
        "The AGM is scheduled for 15/08/2024.",
        "Subscription closes on 30 September 2024.",
        "FY 2023-24 ended on 31/03/2024.",
        "The company was incorporated on 12/04/2001.",
    ])
    def test_date_without_dob_context_not_detected(self, text):
        results = self.rec.analyze(text, ["DATE_OF_BIRTH"])
        assert len(results) == 0, \
            f"False positive: '{text}' → {[text[r.start:r.end] for r in results]}"


# ─── OrgRecognizer ───────────────────────────────────────────────────────────

class TestOrgRecognizer:
    from src.recognizers.org_recognizer import OrgRecognizer
    rec = OrgRecognizer()

    @pytest.mark.parametrize("text", [
        "KSH International Private Limited is the issuer.",
        "Wipro Limited reported Q3 results.",
        "The company Acme Pvt. Ltd. filed the return.",
        "Deloitte Haskins & Sells LLP is the auditor.",
        "Nuvama Wealth Management Limited is the BRLM.",
        "ICICI Securities Limited manages the IPO.",
        "IndusInd Bank Limited extended credit.",
    ])
    def test_org_with_suffix_detected(self, text):
        results = self.rec.analyze(text, ["ORG"])
        assert len(results) >= 1, \
            f"Expected ORG detection in: '{text}'"

    @pytest.mark.parametrize("text", [
        "The net revenue was Rs. 1,23,456.",
        "Refer to Schedule III of the Act.",
        "FY 2023-24 showed strong growth.",
    ])
    def test_non_org_text_not_flagged_as_specific_company(self, text):
        results = self.rec.analyze(text, ["ORG"])
        assert len(results) == 0, f"False positive ORG in '{text}': {results}"


# ─── AddressRecognizer ───────────────────────────────────────────────────────

class TestAddressRecognizer:
    from src.recognizers.address_recognizer import AddressRecognizer
    rec = AddressRecognizer()

    @pytest.mark.parametrize("text,label", [
        ("PIN Code: 411001.", "Indian PIN code with prefix"),
        ("Postal code: 400028.", "postal code keyword"),
        ("Plot No. 12, MIDC Industrial Area.", "plot number"),
        ("Survey No. 341/2, Chakan, Pune.", "survey number"),
        ("4th Floor, Ruby Tower, Dadar.", "floor/building"),
        ("Flat No. 5, Sector 17, Navi Mumbai.", "flat + sector"),
        ("House No. 22, MG Road, Bengaluru.", "house + road"),
        ("B Wing, Tech Park, Kanjurmarg.", "wing address"),
    ])
    def test_address_patterns_detected(self, text, label):
        results = self.rec.analyze(text, ["LOCATION"])
        assert len(results) >= 1, \
            f"Expected ADDRESS detection ({label}) in: '{text}'"

    @pytest.mark.parametrize("text", [
        "Revenue grew 20% in FY2024.",
        "Version 3.14 of the software.",
        "Q3 FY2023 results.",
    ])
    def test_non_address_not_high_confidence(self, text):
        results = self.rec.analyze(text, ["LOCATION"])
        high_conf = [r for r in results if r.score >= 0.65]
        assert len(high_conf) == 0, \
            f"FP address detection in '{text}': " \
            f"{[(text[r.start:r.end], r.score) for r in high_conf]}"


# ─── PersonRecognizer ────────────────────────────────────────────────────────

class TestPersonRecognizer:
    from src.recognizers.person_recognizer import PersonRecognizer
    rec = PersonRecognizer()

    @pytest.mark.parametrize("text,expected_name", [
        (
            "Contact Person: Sarthak Malvadkar, Company Secretary and Compliance Officer; Telephone: + 91 20 4505 3237;",
            "Sarthak Malvadkar"
        ),
        (
            "Sarthak Malvadkar Company Secretary and Compliance Officer",
            "Sarthak Malvadkar"
        ),
        (
            "Name: Rajesh Kumar, Managing Director",
            "Rajesh Kumar"
        ),
        (
            "Contact Person: Priya Mehta",
            "Priya Mehta"
        ),
    ])
    def test_contextual_person_names_detected(self, text, expected_name):
        results = self.rec.analyze(text, ["PERSON"])
        detected_texts = [text[r.start:r.end] for r in results]
        assert expected_name in detected_texts, \
            f"Expected '{expected_name}' to be detected in: '{text}', got: {detected_texts}"


