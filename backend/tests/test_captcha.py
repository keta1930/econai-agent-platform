"""Tests for CAPTCHA service (6 cases)."""

import time
from unittest.mock import patch

from services.captcha_service import (
    generate_captcha,
    validate_captcha,
    _store,
    _CAPTCHA_TTL,
    _MAX_ENTRIES,
)


def setup_function():
    """Clear CAPTCHA store before each test."""
    _store.clear()


def test_generate_captcha():
    """CAPTCHA returns an id and a math question."""
    captcha_id, question = generate_captcha()
    assert isinstance(captcha_id, str) and len(captcha_id) > 0
    assert "= ?" in question
    assert ("+" in question) or ("-" in question)


def test_validate_captcha_correct():
    """Correct answer passes validation."""
    captcha_id, question = generate_captcha()
    # Parse the expected answer from the store
    answer = _store[captcha_id][0]
    assert validate_captcha(captcha_id, answer) is True


def test_validate_captcha_wrong():
    """Wrong answer fails validation."""
    captcha_id, _ = generate_captcha()
    assert validate_captcha(captcha_id, "99999") is False


def test_validate_captcha_expired():
    """Expired CAPTCHA fails validation."""
    captcha_id, _ = generate_captcha()
    answer = _store[captcha_id][0]
    # Manually expire the entry
    _store[captcha_id] = (answer, time.monotonic() - 1)
    assert validate_captcha(captcha_id, answer) is False


def test_validate_captcha_single_use():
    """CAPTCHA is consumed after first validation — second attempt fails."""
    captcha_id, _ = generate_captcha()
    answer = _store[captcha_id][0]
    assert validate_captcha(captcha_id, answer) is True
    assert validate_captcha(captcha_id, answer) is False


def test_captcha_limit():
    """Store rejects generation when at capacity."""
    for _ in range(_MAX_ENTRIES):
        generate_captcha()
    try:
        generate_captcha()
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "full" in str(e).lower()
