from __future__ import annotations

from pathlib import Path

import pytest

from espeakng_runtime import discovery
from espeakng_runtime.errors import EspeakUnavailableError


def test_explicit_executable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    executable = tmp_path / "espeak-ng"
    executable.write_text("", encoding="utf-8")
    monkeypatch.setenv(discovery.ENV_EXECUTABLE, str(executable))
    assert discovery.find_executable() == str(executable.resolve())


def test_invalid_explicit_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    monkeypatch.setenv(discovery.ENV_DATA, str(missing))
    with pytest.raises(EspeakUnavailableError, match="data directory"):
        discovery.find_data()


def test_loader_data_is_not_used_for_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(discovery, "_loader_paths", lambda: ("/loader/lib.so", "/loader/data"))
    monkeypatch.setattr(discovery, "_derived_data", lambda executable, library: "/derived/data")
    assert (
        discovery.find_data(executable="/bin/espeak", library="/system/lib.so") == "/derived/data"
    )
    assert discovery.find_data(executable="/bin/espeak", library="/loader/lib.so") == "/loader/data"


def test_explicit_executable_near_library_precedes_system(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(discovery, "_loader_paths", lambda: None)
    monkeypatch.setattr(
        discovery,
        "_near_executable_candidates",
        lambda executable: (Path("/custom/libespeak-ng.so"),),
    )
    monkeypatch.setattr(discovery.ctypes.util, "find_library", lambda name: "/system/lib.so")
    candidates = discovery.iter_library_candidates(executable="/custom/bin/espeak-ng")
    assert candidates[0].library == "/custom/libespeak-ng.so"


def test_unloadable_loader_falls_back_to_near_executable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loader = "/loader/libespeak-ng.so"
    near = Path("/termux/lib/libespeak-ng.so")

    monkeypatch.setattr(discovery, "_loader_paths", lambda: (loader, "/loader/data"))
    monkeypatch.setattr(discovery, "_near_executable_candidates", lambda executable: (near,))
    monkeypatch.setattr(discovery.ctypes.util, "find_library", lambda name: None)

    class LoadableLibrary:
        pass
        espeak_Initialize = object()
        espeak_SetVoiceByName = object()
        espeak_Terminate = object()
        espeak_TextToPhonemes = object()

    def fake_cdll(path: str):
        if path == loader:
            raise OSError("incompatible shared object")
        if path == near.as_posix():
            return LoadableLibrary()
        raise AssertionError(path)

    monkeypatch.setattr(discovery.ctypes, "CDLL", fake_cdll)

    candidate, probes = discovery.select_native(executable="/termux/bin/espeak-ng")

    assert candidate is not None
    assert candidate.library == near.as_posix()
    assert candidate.source == "near-executable"
    assert [probe.loadable for probe in probes] == [False, True]
    assert probes[0].source == "espeakng-loader"
