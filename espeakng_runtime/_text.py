"""Internal text helpers."""

from __future__ import annotations

import re
from collections.abc import Sequence

_CLAUSE_RE = re.compile(r"(.*?)([.!?]+|[,;:]+|$)", re.DOTALL)


def normalize_phoneme_output(value: str) -> str:
    """Normalize whitespace in backend phoneme output.

    Strips leading/trailing whitespace and collapses internal runs of
    whitespace into single spaces.  IPA symbols, Unicode combining marks,
    tie characters, stress markers, and punctuation are left untouched.
    """
    return re.sub(r"\s+", " ", value.strip())


def _validate_batch_texts(texts: Sequence[str]) -> list[str]:
    """Return batch inputs as a concrete list.

    Embedded line breaks are valid text. Backends must preserve the
    ``phonemize_many`` per-item contract even when an optimized batch
    transport cannot frame multiline items directly.
    """
    return list(texts)


def split_best_effort_clauses(text: str) -> list[tuple[str, str | None, bool]]:
    """Split punctuation for CLI/non-exact fallback.

    This is intentionally labeled best-effort: it is not a replacement for
    eSpeak NG's native terminator API.
    """
    result: list[tuple[str, str | None, bool]] = []
    position = 0
    for match in _CLAUSE_RE.finditer(text):
        if match.start() != position:
            continue
        body, terminator = match.groups()
        if not body and not terminator:
            break
        token = terminator or None
        result.append((body, token, bool(token and set(token) & {".", "!", "?"})))
        position = match.end()
        if position >= len(text):
            break
    return result
