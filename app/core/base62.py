"""Base62 encoding/decoding utilities.

Base62 keeps short codes compact and URL-safe (no need for percent-encoding).
Used both for deterministic id->code conversion and as the alphabet for random
code generation.
"""

from __future__ import annotations

import secrets

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)
_INDEX = {char: idx for idx, char in enumerate(ALPHABET)}


def encode(number: int) -> str:
    """Encode a non-negative integer into a base62 string."""
    if number < 0:
        raise ValueError("number must be non-negative")
    if number == 0:
        return ALPHABET[0]
    chars: list[str] = []
    while number > 0:
        number, remainder = divmod(number, BASE)
        chars.append(ALPHABET[remainder])
    return "".join(reversed(chars))


def decode(code: str) -> int:
    """Decode a base62 string back into an integer."""
    number = 0
    for char in code:
        try:
            number = number * BASE + _INDEX[char]
        except KeyError as exc:  # pragma: no cover - defensive
            raise ValueError(f"invalid base62 character: {char!r}") from exc
    return number


def random_code(length: int) -> str:
    """Generate a cryptographically-strong random base62 code."""
    if length < 1:
        raise ValueError("length must be positive")
    return "".join(secrets.choice(ALPHABET) for _ in range(length))
