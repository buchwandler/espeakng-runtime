"""Reliable native/CLI access to eSpeak NG phonemization."""

from __future__ import annotations

from .errors import (
    CapabilityError,
    EspeakConflictError,
    EspeakError,
    EspeakUnavailableError,
    PhonemizationError,
    VoiceNotFoundError,
)
from .runtime import EspeakRuntime
from .types import Clause, RuntimeInfo, Voice

try:
    from ._version import __version__
except ImportError:  # pragma: no cover - editable tree before build hook runs
    __version__ = "0.1.dev0"

__all__ = [
    "CapabilityError",
    "Clause",
    "EspeakConflictError",
    "EspeakError",
    "EspeakRuntime",
    "EspeakUnavailableError",
    "PhonemizationError",
    "RuntimeInfo",
    "Voice",
    "VoiceNotFoundError",
    "__version__",
]
