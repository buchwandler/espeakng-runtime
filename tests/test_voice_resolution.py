from __future__ import annotations

from collections.abc import Sequence

import pytest

from espeakng_runtime import EspeakRuntime
from espeakng_runtime._voices import (
    choose_voice,
    is_explicit_mbrola_request,
    is_mbrola_identifier,
    normalize_voice_code,
)
from espeakng_runtime.errors import CapabilityError, VoiceNotFoundError
from espeakng_runtime.types import Clause, RuntimeInfo, Voice

VOICES = (
    Voice("British English", "en-gb", "en"),
    Voice("US English", "en-us", "en-us"),
    Voice("Standard French", "fr-fr", "roa/fr"),
    Voice("French MBROLA", "fr", "mb/mb-fr7"),
    Voice("Custom", "xx", "roa/custom"),
    Voice("Arabic MBROLA", "ar", r"mb\mb-ar1"),
)


def test_voice_normalization_and_classification() -> None:
    assert normalize_voice_code(r"  MB\MB-ar1 ") == "mb/mb-ar1"
    assert is_mbrola_identifier(r"mb\mb-ar1")
    assert is_explicit_mbrola_request("mb-fr7")
    assert is_explicit_mbrola_request("mb/mb-fr7")


@pytest.mark.parametrize(
    ("requested", "identifier"),
    [
        ("en-gb", "en"),
        ("en-us", "en-us"),
        ("fr-fr", "roa/fr"),
        ("custom", "roa/custom"),
        ("en-au", "en"),
    ],
)
def test_choose_voice_ranking(requested: str, identifier: str) -> None:
    assert choose_voice(VOICES, requested).identifier == identifier


def test_generic_french_request_prefers_standard_voice() -> None:
    assert choose_voice(VOICES, "fr").identifier == "roa/fr"


def test_explicit_mbrola_request_is_allowed() -> None:
    assert choose_voice(VOICES, "mb-fr7").identifier == "mb/mb-fr7"
    assert choose_voice(VOICES, r"mb\mb-ar1").identifier == r"mb\mb-ar1"


def test_mbrola_can_be_enabled_for_normal_request() -> None:
    only_mbrola = (Voice("French MBROLA", "fr", "mb/mb-fr7"),)
    with pytest.raises(VoiceNotFoundError):
        choose_voice(only_mbrola, "fr")
    assert choose_voice(only_mbrola, "fr", allow_mbrola=True).identifier == "mb/mb-fr7"


def test_invalid_voice_requests_raise() -> None:
    with pytest.raises(VoiceNotFoundError):
        choose_voice(VOICES, "missing")
    with pytest.raises(VoiceNotFoundError):
        choose_voice(VOICES, "")


class RecordingBackend:
    def __init__(self, voices: Sequence[Voice] = VOICES, *, enumerate_voices: bool = True) -> None:
        self.voices = list(voices)
        self.enumerate_voices = enumerate_voices
        self.list_calls = 0
        self.calls: list[tuple[str, str]] = []

    @property
    def info(self) -> RuntimeInfo:
        return RuntimeInfo(requested_mode="cli", implementation="cli")

    def list_voices(self, filter_name: str | None = None) -> list[Voice]:
        self.list_calls += 1
        if not self.enumerate_voices:
            raise CapabilityError("voice inventory unavailable")
        return self.voices

    def phonemize(
        self,
        text: str,
        *,
        voice: str,
        separator: str | None = None,
        use_tie: bool = False,
        tie_char: str = "͡",
    ) -> str:
        self.calls.append(("phonemize", voice))
        return voice

    def phonemize_many(
        self,
        texts: Sequence[str],
        *,
        voice: str,
        separator: str | None = None,
        use_tie: bool = False,
        tie_char: str = "͡",
    ) -> list[str]:
        self.calls.append(("phonemize_many", voice))
        return [voice for _ in texts]

    def clauses(self, text: str, *, voice: str, exact: bool = False) -> list[Clause]:
        self.calls.append(("clauses", voice))
        return [Clause(phonemes=voice)]

    def close(self) -> None:
        pass


def make_runtime(backend: RecordingBackend) -> EspeakRuntime:
    instance = object.__new__(EspeakRuntime)
    instance._closed = False
    instance._backend = backend
    instance._voice_inventory = None
    instance._resolved_voices = {}
    return instance


def test_runtime_resolves_and_caches_voice_for_all_facade_calls() -> None:
    backend = RecordingBackend()
    runtime = make_runtime(backend)

    assert runtime.resolve_voice("EN_GB").identifier == "en"
    assert runtime.phonemize("hello", voice="en-gb") == "en"
    assert runtime.phonemize_many(["one", "two"], voice="en-gb") == ["en", "en"]
    assert runtime.clauses("hello", voice="en-gb")[0].phonemes == "en"
    assert backend.list_calls == 1
    assert backend.calls == [
        ("phonemize", "en"),
        ("phonemize_many", "en"),
        ("clauses", "en"),
    ]


def test_voice_caches_are_not_shared_between_runtime_instances() -> None:
    first_backend = RecordingBackend()
    second_backend = RecordingBackend()
    first = make_runtime(first_backend)
    second = make_runtime(second_backend)

    first.resolve_voice("en-gb")
    second.resolve_voice("en-gb")

    assert first_backend.list_calls == second_backend.list_calls == 1


def test_missing_inventory_preserves_direct_selection() -> None:
    backend = RecordingBackend(enumerate_voices=False)
    runtime = make_runtime(backend)

    assert runtime.phonemize("hello", voice="en-gb") == "en-gb"
    assert backend.list_calls == 1
