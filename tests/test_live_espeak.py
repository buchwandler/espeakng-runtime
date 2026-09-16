from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest

from espeakng_runtime import EspeakRuntime
from espeakng_runtime.discovery import maybe_find_executable, select_native


@pytest.mark.espeak
def test_cli_smoke() -> None:
    if maybe_find_executable() is None:
        pytest.skip("eSpeak CLI not installed")
    with EspeakRuntime(mode="cli") as runtime:
        value = runtime.phonemize("hello", voice="en-us")
        assert value
        assert runtime.info.implementation == "cli"


@pytest.mark.espeak
def test_native_smoke_if_available() -> None:
    candidate, _ = select_native()
    if candidate is None:
        pytest.skip("eSpeak native library not installed")
    with EspeakRuntime(mode="native") as runtime:
        value = runtime.phonemize("hello", voice="en-us")
        assert value
        assert runtime.info.implementation == "native"


@pytest.mark.espeak
def test_native_repeated_runtime_lifecycle_does_not_hang() -> None:
    candidate, _ = select_native()
    if candidate is None:
        pytest.skip("eSpeak native library not installed")

    code = textwrap.dedent(
        """
        from espeakng_runtime import EspeakRuntime

        for _ in range(10):
            runtime = EspeakRuntime(mode="native")
            assert runtime.phonemize("hello", voice="en-us")
            runtime.close()
        """
    )
    completed = subprocess.run(
        [sys.executable, "-u", "-c", code],
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
