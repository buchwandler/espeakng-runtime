"""Small public data models."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

FallbackCode = Literal[
    "native-unavailable",
    "native-load-error",
    "exact-clause-api-unavailable",
    "native-init-failed",
]


@dataclass(frozen=True, slots=True)
class Voice:
    """An eSpeak voice entry."""

    name: str
    language: str
    identifier: str
    gender: int = 0
    age: int = 0


@dataclass(frozen=True, slots=True)
class Clause:
    """A phonemized clause plus its source terminator."""

    phonemes: str
    terminator: str | None = None
    terminator_code: int | None = None
    sentence_end: bool = False


@dataclass(frozen=True, slots=True)
class RuntimeInfo:
    """Resolved backend and capability information."""

    requested_mode: Literal["auto", "native", "cli"]
    implementation: Literal["native", "cli"]
    executable: str | None = None
    library: str | None = None
    data: str | None = None
    source: str | None = None
    version: str | None = None
    exact_clause_api: bool = False
    phoneme_output_api: Literal["cli", "native-trace", "native-translation"] | None = None
    phoneme_parity: Literal["exact", "best-effort"] | None = None
    parity: Literal["exact", "best-effort"] = "best-effort"
    fallback_reason: str | None = None
    fallback_code: FallbackCode | None = None

    @property
    def version_tuple(self) -> tuple[int, ...]:
        """Return the numeric components of the reported version."""
        if not self.version:
            return ()
        match = re.search(r"\d+(?:\.\d+)*", self.version)
        return tuple(int(part) for part in match.group(0).split(".")) if match else ()
