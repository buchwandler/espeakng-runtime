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
