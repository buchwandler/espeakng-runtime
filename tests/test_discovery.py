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
