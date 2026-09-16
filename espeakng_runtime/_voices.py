"""Voice request normalization and deterministic inventory selection."""

from __future__ import annotations

from collections.abc import Sequence

from .errors import VoiceNotFoundError
from .types import Voice


def normalize_voice_code(value: str) -> str:
    """Normalize an eSpeak voice code for comparison."""
    return value.strip().lower().replace("\\", "/").replace("_", "-")


def is_mbrola_identifier(value: str) -> bool:
    """Return whether an inventory identifier denotes an MBROLA voice."""
    return normalize_voice_code(value).startswith("mb/")


def is_explicit_mbrola_request(value: str) -> bool:
    """Return whether a request explicitly asks for an MBROLA voice."""
    code = normalize_voice_code(value)
    return code.startswith(("mb/", "mb-", "mbrola"))


def _standard_rank(requested: str, voice: Voice) -> int | None:
    identifier = normalize_voice_code(voice.identifier)
    language = normalize_voice_code(voice.language)
    identifier_name = identifier.rsplit("/", 1)[-1]
    requested_base = requested.split("-", 1)[0]

    if language == requested:
        return 0
    if identifier == requested:
        return 1
    if identifier_name == requested:
        return 2
    if language.split("-", 1)[0] == requested_base:
        return 3
    return None


def choose_voice(
    voices: Sequence[Voice],
    request: str,
    *,
    allow_mbrola: bool = False,
) -> Voice:
    """Select the best compatible voice from an eSpeak inventory."""
    requested = normalize_voice_code(request)
    if not requested:
        raise VoiceNotFoundError("eSpeak voice request must not be empty")

    explicit_mbrola = is_explicit_mbrola_request(requested)
    ranked: list[tuple[int, int, Voice]] = []
    for index, voice in enumerate(voices):
        identifier = normalize_voice_code(voice.identifier)
        mbrola = is_mbrola_identifier(identifier)
        rank: int | None

        if explicit_mbrola:
            if not mbrola:
                continue
            if identifier == requested:
                rank = 0
            elif identifier.rsplit("/", 1)[-1] == requested:
                rank = 1
            else:
                continue
        else:
            if mbrola:
                if not allow_mbrola:
                    continue
                rank = _standard_rank(requested, voice)
                if rank is None:
                    continue
                rank += 10
            else:
                rank = _standard_rank(requested, voice)
                if rank is None:
                    continue

        if rank is not None:
            ranked.append((rank, index, voice))

    if not ranked:
        raise VoiceNotFoundError(f"eSpeak voice {request!r} was not found")
    return min(ranked, key=lambda item: (item[0], item[1]))[2]
