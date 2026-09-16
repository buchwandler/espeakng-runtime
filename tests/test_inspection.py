from __future__ import annotations

import pytest

from espeakng_runtime import discovery, inspect_espeak


class FakeLibrary:
    def __init__(self, *, exact: bool = False, missing: tuple[str, ...] = ()) -> None:
        required = {
            "espeak_Initialize",
            "espeak_SetVoiceByName",
            "espeak_Terminate",
            "espeak_TextToPhonemes",
        }
        for name in required.difference(missing):
            setattr(self, name, object())
        if exact:
            self.espeak_TextToPhonemesWithTerminator = object()


def test_inspection_selects_later_exact_candidate_without_initializing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidates = ("/near/first.so", "/near/second.so")
    initialize_calls = 0

    monkeypatch.setattr(discovery, "_loader_paths", lambda: None)
    monkeypatch.setattr(
        discovery,
        "_near_executable_candidates",
        lambda executable: tuple(discovery.Path(path) for path in candidates),
    )
    monkeypatch.setattr(discovery.ctypes.util, "find_library", lambda name: None)

    def fake_cdll(path: str) -> FakeLibrary:
        nonlocal initialize_calls
        library = FakeLibrary(exact=path == candidates[1])

        def initialize(*_args: object) -> int:
            nonlocal initialize_calls
            initialize_calls += 1
            return 0

        library.espeak_Initialize = initialize
        return library

    monkeypatch.setattr(discovery.ctypes, "CDLL", fake_cdll)
    monkeypatch.setattr(discovery, "maybe_find_executable", lambda explicit=None: "/bin/espeak-ng")

    result = inspect_espeak(require_exact_clauses=True)

    assert result.cli_available
    assert result.native_available
    assert result.exact_native_available
    assert result.selected_library == candidates[1]
    assert [probe.library for probe in result.candidates] == list(candidates)
    assert initialize_calls == 0


def test_inspection_explicit_library_is_authoritative(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    explicit = "/explicit/lib.so"

    monkeypatch.setattr(discovery, "_loader_paths", lambda: None)
    monkeypatch.setattr(
        discovery,
        "_near_executable_candidates",
        lambda executable: (discovery.Path("/near/lib.so"),),
    )
    monkeypatch.setattr(discovery.ctypes.util, "find_library", lambda name: "/system/lib.so")

    def fake_cdll(path: str) -> FakeLibrary:
        calls.append(path)
        return FakeLibrary(exact=True)

    monkeypatch.setattr(discovery.ctypes, "CDLL", fake_cdll)

    result = inspect_espeak(library=explicit, require_exact_clauses=True)

    assert result.selected_library == explicit
    assert calls == [explicit]
    assert len(result.candidates) == 1


def test_probe_records_missing_mandatory_symbols(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        discovery.ctypes,
        "CDLL",
        lambda path: FakeLibrary(missing=("espeak_Terminate",)),
    )

    probe = discovery.probe_library(discovery.LibraryCandidate("/broken.so", "test"))

    assert probe.loadable
    assert probe.missing_symbols == ("espeak_Terminate",)
    assert probe.error == "missing mandatory symbols: espeak_Terminate"
