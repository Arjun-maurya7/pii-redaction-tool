"""
replacer.py — Synthetic PII replacement generator.

Uses Faker to generate realistic fake values, with a global mapping so the
same original PII string always maps to the same synthetic replacement.
"""

from __future__ import annotations

import random
import re
import string
from typing import Dict

from faker import Faker


fake = Faker("en_IN")           # Indian locale for phone/address defaults
fake_en = Faker("en_US")        # US locale for SSN

# ---------------------------------------------------------------------------
# Global replacement registry — original text → synthetic replacement
# ---------------------------------------------------------------------------
_REPLACEMENT_MAP: Dict[str, str] = {}


def get_replacement(original: str, entity_type: str) -> str:
    """
    Return a synthetic replacement for *original*.

    The same *original* string (case-sensitive) will always return the same
    replacement within a single run.
    """
    key = (original, entity_type)
    if key not in _REPLACEMENT_MAP:
        _REPLACEMENT_MAP[key] = _generate(original, entity_type)
    return _REPLACEMENT_MAP[key]


def reset_mapping() -> None:
    """Clear the replacement map (useful for testing)."""
    _REPLACEMENT_MAP.clear()


def get_all_mappings() -> Dict[str, str]:
    """Return a copy of all replacements generated so far."""
    return {f"{k[1]}::{k[0]}": v for k, v in _REPLACEMENT_MAP.items()}


# ---------------------------------------------------------------------------
# Per-type generators
# ---------------------------------------------------------------------------

def _generate(original: str, entity_type: str) -> str:
    generators = {
        "PERSON":       _fake_person,
        "ORGANIZATION": _fake_org,
        "EMAIL":        _fake_email,
        "PHONE":        _fake_phone,
        "SSN":          _fake_ssn,
        "CREDIT_CARD":  _fake_credit_card,
        "IP_ADDRESS":   _fake_ip,
        "DATE_OF_BIRTH":_fake_dob,
        "ADDRESS":      _fake_address,
    }
    gen = generators.get(entity_type, _fake_generic)
    return gen(original)


def _fake_person(_: str) -> str:
    return fake_en.name()


def _fake_org(_: str) -> str:
    return fake_en.company()


def _fake_email(original: str) -> str:
    # Always use a neutral synthetic domain (e.g. example.com, example.org)
    # Never preserve original corporate domain (e.g. @kshinternational.com)
    domains = ["example.com", "example.org", "example.net"]
    domain = random.choice(domains)
    local = fake_en.user_name()
    return f"{local}@{domain}"


def _fake_phone(original: str) -> str:
    # Normalize whitespace, hyphens, dots, parentheses before checking prefix
    cleaned = re.sub(r"[\s\-\(\)\.]+", "", original)

    # 1. Indian +91 / + 91 / 091 / 91 prefix (landlines & mobiles)
    if cleaned.startswith("+91") or cleaned.startswith("091") or (cleaned.startswith("91") and len(cleaned) >= 12):
        digits = "".join(random.choices("6789", k=1) + random.choices(string.digits, k=9))
        return f"+91 {digits}"

    # 2. Indian STD landline starting with 0 (e.g. 022-68052182, 020-26234000)
    if cleaned.startswith("0") and 8 <= len(cleaned) <= 12:
        std = cleaned[:3] if cleaned[:3] in ["020", "022", "011", "040", "080", "044", "033"] else "020"
        rest = "".join(random.choices(string.digits, k=8))
        return f"{std}-{rest}"

    # 3. 10-digit Indian mobile starting with 6-9
    if len(cleaned) == 10 and cleaned[0] in "6789":
        digits = "".join(random.choices("6789", k=1) + random.choices(string.digits, k=9))
        return f"+91 {digits}"

    # 4. Indian Toll free (1800-XXX-XXXX)
    if cleaned.startswith("1800"):
        digits = "".join(random.choices(string.digits, k=6))
        return f"1800-{digits[:3]}-{digits[3:]}"

    # 5. International with country code (+CC ...)
    m = re.match(r"^\+(\d{1,3})", cleaned)
    if m:
        cc = m.group(1)
        digits = "".join(random.choices(string.digits, k=10))
        return f"+{cc} {digits}"

    # Fallback to realistic Indian phone
    digits = "".join(random.choices("6789", k=1) + random.choices(string.digits, k=9))
    return f"+91 {digits}"


def _fake_ssn(_: str) -> str:
    return fake_en.ssn()


def _fake_credit_card(_: str) -> str:
    # Generate a valid-looking (Luhn-passing) number
    return fake_en.credit_card_number()


def _fake_ip(_: str) -> str:
    # Use private IP ranges to avoid accidental real IPs
    a = random.choice([10, 172, 192])
    if a == 10:
        return f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
    if a == 172:
        return f"172.{random.randint(16,31)}.{random.randint(0,255)}.{random.randint(1,254)}"
    return f"192.168.{random.randint(0,255)}.{random.randint(1,254)}"


def _fake_dob(_: str) -> str:
    dob = fake_en.date_of_birth(minimum_age=18, maximum_age=80)
    return dob.strftime("%d/%m/%Y")


def _fake_address(_: str) -> str:
    return fake_en.address().replace("\n", ", ")


def _fake_generic(_: str) -> str:
    return "[REDACTED]"
