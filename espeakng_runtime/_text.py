"""Internal text helpers."""

from __future__ import annotations

import re

_CLAUSE_RE = re.compile(r"(.*?)([.!?]+|[,;:]+|$)", re.DOTALL)


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
