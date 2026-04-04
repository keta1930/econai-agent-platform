"""Simple math CAPTCHA: in-memory store with TTL."""

import random
import time
import uuid

_CAPTCHA_TTL = 300  # 5 minutes
_MAX_ENTRIES = 1000

# {captcha_id: (answer_str, expires_at_timestamp)}
_store: dict[str, tuple[str, float]] = {}


def _cleanup_expired() -> None:
    now = time.monotonic()
    expired = [k for k, (_, exp) in _store.items() if exp < now]
    for k in expired:
        del _store[k]


def generate_captcha() -> tuple[str, str]:
    """Return (captcha_id, question_text). Raises ValueError if store is full."""
    _cleanup_expired()
    if len(_store) >= _MAX_ENTRIES:
        raise ValueError("CAPTCHA store is full")

    a = random.randint(1, 50)
    b = random.randint(1, 50)
    if random.choice([True, False]):
        answer = str(a + b)
        question = f"{a} + {b} = ?"
    else:
        # Ensure non-negative result
        a, b = max(a, b), min(a, b)
        answer = str(a - b)
        question = f"{a} - {b} = ?"

    captcha_id = uuid.uuid4().hex
    _store[captcha_id] = (answer, time.monotonic() + _CAPTCHA_TTL)
    return captcha_id, question


def validate_captcha(captcha_id: str, answer: str) -> bool:
    """Validate and consume a CAPTCHA. Returns False if wrong/expired/missing."""
    entry = _store.pop(captcha_id, None)
    if entry is None:
        return False
    stored_answer, expires_at = entry
    if time.monotonic() > expires_at:
        return False
    return answer.strip() == stored_answer
