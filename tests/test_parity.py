from __future__ import annotations

import os
from pathlib import Path

import pytest

from espeakng_runtime import EspeakRuntime
from espeakng_runtime.discovery import (
    LibraryCandidate,
    maybe_find_executable,
    probe_library,
    select_native,
)
from espeakng_runtime.errors import VoiceNotFoundError


def _backends_available() -> bool:
    return maybe_find_executable() is not None and select_native()[0] is not None


@pytest.mark.espeak
def test_native_and_cli_share_basic_phonemization() -> None:
    if not _backends_available():
        pytest.skip("both eSpeak CLI and native library are required")
    with EspeakRuntime(mode="native") as native_runtime, EspeakRuntime(mode="cli") as cli_runtime:
        for text in ("Hello world", "Hello, world!", "café"):
            native_value = native_runtime.phonemize(text, voice="en-us")
            cli_value = cli_runtime.phonemize(text, voice="en-us")
            assert native_value == cli_value


@pytest.mark.espeak
def test_language_style_voice_resolution_parity() -> None:
    if not _backends_available():
        pytest.skip("both eSpeak CLI and native library are required")
    with EspeakRuntime(mode="native") as native_runtime, EspeakRuntime(mode="cli") as cli_runtime:
        for requested_voice in ("en-us", "en-gb", "de", "fr"):
            try:
                native_runtime.resolve_voice(requested_voice)
                cli_runtime.resolve_voice(requested_voice)
            except VoiceNotFoundError:
                continue
            assert native_runtime.phonemize(
                "Hello", voice=requested_voice, separator="_"
            ) == cli_runtime.phonemize("Hello", voice=requested_voice, separator="_")


def test_native_and_cli_share_options_and_batches() -> None:
    if not _backends_available():
        pytest.skip("both eSpeak CLI and native library are required")
    values = ["One", "Two", "", "Three"]
    with EspeakRuntime(mode="native") as native_runtime, EspeakRuntime(mode="cli") as cli_runtime:
        for kwargs in ({"separator": "_"}, {"use_tie": True}):
            cli_value = cli_runtime.phonemize("Hello", voice="en-us", **kwargs)
            assert native_runtime.phonemize("Hello", voice="en-us", **kwargs) == cli_value
        native_batch = native_runtime.phonemize_many(values, voice="en-us")
        cli_batch = cli_runtime.phonemize_many(values, voice="en-us")
        assert len(native_batch) == len(cli_batch) == len(values)
        assert native_batch[2] == cli_batch[2] == ""


@pytest.mark.espeak
def test_bundled_loader_smoke() -> None:
    loader = pytest.importorskip("espeakng_loader")
    library = Path(loader.get_library_path())
    data = loader.get_data_path()
    if not library.is_file() or not data or not Path(data).exists():
        pytest.skip("bundled loader paths are unavailable")

    probe = probe_library(
        LibraryCandidate(
            library=str(library),
            source="espeakng-loader",
            data=str(data),
        )
    )
    if not probe.loadable:
        if os.environ.get("ANDROID_ROOT") or os.environ.get("ANDROID_DATA"):
            pytest.skip(
                "espeakng-loader library exists but is not loadable on Android/Termux: "
                f"{probe.error}"
            )
        pytest.fail(f"espeakng-loader library exists but is not loadable: {probe.error}")

    with EspeakRuntime(mode="native") as runtime:
        assert runtime.info.source == "espeakng-loader"
        assert runtime.info.library is not None
        assert Path(runtime.info.library).resolve() == library.resolve()
        assert runtime.phonemize("hello", voice="en-us")
