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
        assert runtime.phonemize("hello", voice="en-us")


# --- Regional locale parity matrix ---

VOICE_PARITY_CASES = (
    ("de-de", "Haus"),
    ("en-us", "hello"),
    ("en-gb", "hello"),
    ("fr-fr", "bonjour"),
    ("sv-se", "hej"),
    ("pt-br", "olá"),
)


@pytest.mark.espeak
@pytest.mark.parametrize(("selector", "text"), VOICE_PARITY_CASES)
def test_regional_locale_parity(selector: str, text: str) -> None:
    """Regional locale selectors produce identical output on native and CLI."""
    if not _backends_available():
        pytest.skip("both eSpeak CLI and native library are required")
    with EspeakRuntime(mode="native") as native_runtime, EspeakRuntime(mode="cli") as cli_runtime:
        try:
            native_value = native_runtime.phonemize(text, voice=selector)
        except VoiceNotFoundError:
            pytest.skip(f"native does not support {selector}")
        try:
            cli_value = cli_runtime.phonemize(text, voice=selector)
        except Exception:
            pytest.skip(f"CLI does not support {selector}")
        assert native_value == cli_value, f"{selector}: native={native_value!r} cli={cli_value!r}"


@pytest.mark.espeak
@pytest.mark.parametrize(("selector", "text"), VOICE_PARITY_CASES)
def test_regional_locale_custom_zwj_tie_parity(selector: str, text: str) -> None:
    """Regional locale selectors with U+200D tie produce identical output."""
    if not _backends_available():
        pytest.skip("both eSpeak CLI and native library are required")
    kwargs = {"use_tie": True, "tie_char": "\u200d"}
    with EspeakRuntime(mode="native") as native_runtime, EspeakRuntime(mode="cli") as cli_runtime:
        try:
            native_value = native_runtime.phonemize(text, voice=selector, **kwargs)
        except VoiceNotFoundError:
            pytest.skip(f"native does not support {selector}")
        try:
            cli_value = cli_runtime.phonemize(text, voice=selector, **kwargs)
        except Exception:
            pytest.skip(f"CLI does not support {selector}")
        msg = f"{selector} zwj: native={native_value!r} cli={cli_value!r}"
        assert native_value == cli_value, msg


@pytest.mark.espeak
def test_batch_parity_with_regional_selector() -> None:
    """Batch phonemization with regional selectors produces identical output."""
    if not _backends_available():
        pytest.skip("both eSpeak CLI and native library are required")
    texts = ["Haus", "Deutsch", "", "hello"]
    with EspeakRuntime(mode="native") as native_runtime, EspeakRuntime(mode="cli") as cli_runtime:
        try:
            native_batch = native_runtime.phonemize_many(texts, voice="de-de")
        except VoiceNotFoundError:
            pytest.skip("native does not support de-de")
        try:
            cli_batch = cli_runtime.phonemize_many(texts, voice="de-de")
        except Exception:
            pytest.skip("CLI does not support de-de")
        assert len(native_batch) == len(cli_batch) == len(texts)
        assert native_batch[2] == cli_batch[2] == ""
        assert native_batch == cli_batch


@pytest.mark.espeak
def test_auto_mode_parity_with_regional_selector() -> None:
    """mode='auto' produces the same result as CLI for regional selectors."""
    if not _backends_available():
        pytest.skip("both eSpeak CLI and native library are required")
    with EspeakRuntime(mode="auto") as auto_runtime, EspeakRuntime(mode="cli") as cli_runtime:
        for selector, text in (("de-de", "Haus"), ("fr-fr", "bonjour")):
            try:
                auto_value = auto_runtime.phonemize(text, voice=selector)
            except VoiceNotFoundError:
                continue
            try:
                cli_value = cli_runtime.phonemize(text, voice=selector)
            except Exception:
                continue
            msg = f"{selector} auto: auto={auto_value!r} cli={cli_value!r}"
            assert auto_value == cli_value, msg


# --- English weak-word parity ---

ENGLISH_WEAK_WORD_PARITY_CASES = (
    "the",
    "and",
    "to",
    "for",
    "of",
    "we",
    "you",
    "they",
    "I'm",
    "we're",
    "you're",
    "they're",
    "we've",
    "you've",
    "we'll",
    "you'll",
    "he's",
    "she's",
    "it's",
)


@pytest.mark.espeak
@pytest.mark.parametrize("text", ENGLISH_WEAK_WORD_PARITY_CASES)
def test_english_weak_word_parity_zwj(text: str) -> None:
    """Weak words and contractions produce identical output on native and CLI with U+200D tie."""
    if not _backends_available():
        pytest.skip("both eSpeak CLI and native library are required")
    kwargs = {"voice": "en-us", "use_tie": True, "tie_char": "\u200d"}
    with EspeakRuntime(mode="native") as native_runtime, EspeakRuntime(mode="cli") as cli_runtime:
        native_value = native_runtime.phonemize(text, **kwargs)
        cli_value = cli_runtime.phonemize(text, **kwargs)
        from tests._phoneme_parity import assert_phoneme_parity

        assert_phoneme_parity(
            text=text,
            native=native_value,
            cli=cli_value,
            voice="en-us",
        )


@pytest.mark.espeak
def test_phrase_context_parity() -> None:
    """Phrase context produces identical output on native and CLI."""
    if not _backends_available():
        pytest.skip("both eSpeak CLI and native library are required")
    kwargs = {"voice": "en-us", "use_tie": True, "tie_char": "\u200d"}
    with EspeakRuntime(mode="native") as native_runtime, EspeakRuntime(mode="cli") as cli_runtime:
        for phrase in ("we're feel play", "I'm going to the store", "you're welcome"):
            native_value = native_runtime.phonemize(phrase, **kwargs)
            cli_value = cli_runtime.phonemize(phrase, **kwargs)
            from tests._phoneme_parity import assert_phoneme_parity

            assert_phoneme_parity(
                text=phrase,
                native=native_value,
                cli=cli_value,
                voice="en-us",
            )


@pytest.mark.espeak
def test_batch_parity_weak_words() -> None:
    """Batch phonemize_many with weak words produces identical output."""
    if not _backends_available():
        pytest.skip("both eSpeak CLI and native library are required")
    values = ["we're", "the", "hello", "", "we've"]
    kwargs = {"voice": "en-us", "use_tie": True, "tie_char": "\u200d"}
    with EspeakRuntime(mode="native") as native_runtime, EspeakRuntime(mode="cli") as cli_runtime:
        native_batch = native_runtime.phonemize_many(values, **kwargs)
        cli_batch = cli_runtime.phonemize_many(values, **kwargs)
        assert len(native_batch) == len(cli_batch) == len(values)
        assert native_batch[3] == cli_batch[3] == ""
        for i, (native_val, cli_val) in enumerate(zip(native_batch, cli_batch, strict=True)):
            if values[i] and values[i].strip():
                from tests._phoneme_parity import assert_phoneme_parity

                assert_phoneme_parity(
                    text=values[i],
                    native=native_val,
                    cli=cli_val,
                    voice="en-us",
                )


@pytest.mark.espeak
def test_auto_mode_weak_word_parity() -> None:
    """mode='auto' matches CLI for weak words when native trace is available."""
    if not _backends_available():
        pytest.skip("both eSpeak CLI and native library are required")
    kwargs = {"voice": "en-us", "use_tie": True, "tie_char": "\u200d"}
    with EspeakRuntime(mode="auto") as auto_runtime, EspeakRuntime(mode="cli") as cli_runtime:
        for text in ("we're", "I'm", "the", "we've"):
            auto_value = auto_runtime.phonemize(text, **kwargs)
            cli_value = cli_runtime.phonemize(text, **kwargs)
            from tests._phoneme_parity import assert_phoneme_parity

            assert_phoneme_parity(
                text=text,
                native=auto_value,
                cli=cli_value,
                voice="en-us",
            )
