"""Explainable phoneme parity assertion helper for native/CLI backend comparison.

Uses Phonodist for structural mismatch diagnosis when raw outputs differ.
"""

from __future__ import annotations

import pytest

try:
    from phonodist import PhonodistError, compare_pronunciations
except ImportError:  # pragma: no cover
    compare_pronunciations = None  # type: ignore[assignment]
    PhonodistError = Exception  # type: ignore[assignment,misc]


def assert_phoneme_parity(
    *,
    text: str,
    native: str,
    cli: str,
    voice: str,
) -> None:
    """Assert native and CLI phoneme outputs are identical.

    On mismatch, uses Phonodist to classify the difference and emits a
    detailed diagnostic. Raw equality remains the actual parity assertion;
    Phonodist only improves failure messages.
    """
    if native == cli:
        return

    # Try Phonodist classification for better diagnostics
    classification = None
    segment_relation = None
    stress_info = None

    if compare_pronunciations is not None:
        try:
            comparison = compare_pronunciations(native, cli)
            classification = comparison.classification
            segment_relation = comparison.segment_relation
            stress_ops = comparison.stress_operations
            if stress_ops:
                stress_info = str(stress_ops)
        except (PhonodistError, Exception):
            pass

    lines = [
        f'text: "{text}"',
        f"voice: {voice}",
        f"native: {native!r}",
        f"cli:    {cli!r}",
    ]
    if classification:
        lines.append(f"classification: {classification}")
    if segment_relation:
        lines.append(f"segment_relation: {segment_relation}")
    if stress_info:
        lines.append(f"stress_operations: {stress_info}")

    pytest.fail("\n".join(lines))
