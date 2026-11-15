"""NANP phone normalization for store + request validation."""

from __future__ import annotations


def digits_only(value: str) -> str:
    return "".join(c for c in value if c.isdigit())


def normalize_phone(value: str) -> str:
    """Strip non-digits; drop leading US country code 1 when 11 digits."""
    digits = digits_only(value)
    if len(digits) < 7:
        raise ValueError("phone must contain at least 7 digits")
    if len(digits) == 11 and digits.startswith("1"):
        return digits[1:]
    return digits


def phones_match(stored: str, query: str) -> bool:
    """Match stored vs query allowing optional leading 1 / suffix overlap."""
    a = digits_only(stored)
    b = digits_only(query)
    if not a or not b:
        return False
    if len(a) == 11 and a.startswith("1"):
        a = a[1:]
    if len(b) == 11 and b.startswith("1"):
        b = b[1:]
    return a == b or a.endswith(b) or b.endswith(a)
