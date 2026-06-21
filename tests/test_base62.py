"""Unit tests for base62 encoding."""
import pytest

from app.core import base62


@pytest.mark.parametrize("number", [0, 1, 61, 62, 12345, 9_999_999_999])
def test_roundtrip(number: int) -> None:
    assert base62.decode(base62.encode(number)) == number


def test_zero_is_first_char() -> None:
    assert base62.encode(0) == base62.ALPHABET[0]


def test_random_code_length_and_alphabet() -> None:
    code = base62.random_code(8)
    assert len(code) == 8
    assert all(ch in base62.ALPHABET for ch in code)


def test_negative_raises() -> None:
    with pytest.raises(ValueError):
        base62.encode(-1)


def test_invalid_char_raises() -> None:
    with pytest.raises(ValueError):
        base62.decode("abc!")
