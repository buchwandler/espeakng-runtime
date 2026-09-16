from __future__ import annotations

import pytest

from espeakng_runtime import runtime
from espeakng_runtime.discovery import LibraryCandidate


class DummyNative:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs


class DummyCli:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs


def test_auto_prefers_native(monkeypatch) -> None:
    monkeypatch.setattr(runtime, "maybe_find_executable", lambda value=None: "/x/espeak-ng")
    monkeypatch.setattr(
        runtime,
        "select_native",
        lambda **kwargs: (LibraryCandidate("/x/libespeak-ng.so", "test", "/x/data"), ()),
    )
    monkeypatch.setattr(runtime, "NativeBackend", DummyNative)
    instance = runtime.EspeakRuntime()
    assert isinstance(instance._backend, DummyNative)


def test_auto_falls_back_after_native_initialization_failure(monkeypatch) -> None:
    monkeypatch.setattr(runtime, "maybe_find_executable", lambda value=None: "/x/espeak-ng")
    monkeypatch.setattr(runtime, "find_executable", lambda value=None: "/x/espeak-ng")
    monkeypatch.setattr(
        runtime,
        "select_native",
        lambda **kwargs: (LibraryCandidate("/x/libespeak-ng.so", "test", "/x/data"), ()),
    )
    monkeypatch.setattr(
        runtime,
        "NativeBackend",
        lambda **kwargs: (_ for _ in ()).throw(runtime.EspeakUnavailableError("bad data path")),
    )
    monkeypatch.setattr(runtime, "CliBackend", DummyCli)

    instance = runtime.EspeakRuntime()

    assert isinstance(instance._backend, DummyCli)
    assert instance._backend.kwargs["fallback_code"] == "native-init-failed"
    assert "bad data path" in instance._backend.kwargs["fallback_reason"]


def test_native_does_not_fall_back_after_initialization_failure(monkeypatch) -> None:
    monkeypatch.setattr(runtime, "maybe_find_executable", lambda value=None: "/x/espeak-ng")
    monkeypatch.setattr(
        runtime,
        "select_native",
        lambda **kwargs: (LibraryCandidate("/x/libespeak-ng.so", "test", "/x/data"), ()),
    )
    error = runtime.EspeakUnavailableError("bad data path")
    monkeypatch.setattr(runtime, "NativeBackend", lambda **kwargs: (_ for _ in ()).throw(error))

    with pytest.raises(runtime.EspeakUnavailableError, match="bad data path"):
        runtime.EspeakRuntime(mode="native")


def test_cli_unavailable_after_native_initialization_failure_is_descriptive(monkeypatch) -> None:
    monkeypatch.setattr(runtime, "maybe_find_executable", lambda value=None: "/x/espeak-ng")
    monkeypatch.setattr(
        runtime,
        "select_native",
        lambda **kwargs: (LibraryCandidate("/x/libespeak-ng.so", "test", "/x/data"), ()),
    )
    monkeypatch.setattr(
        runtime,
        "NativeBackend",
        lambda **kwargs: (_ for _ in ()).throw(runtime.EspeakUnavailableError("bad data path")),
    )
    monkeypatch.setattr(
        runtime,
        "find_executable",
        lambda value=None: (_ for _ in ()).throw(
            runtime.EspeakUnavailableError("missing executable")
        ),
    )

    with pytest.raises(runtime.EspeakUnavailableError, match="bad data path.*missing executable"):
        runtime.EspeakRuntime()


def test_auto_falls_back_to_cli(monkeypatch) -> None:
    monkeypatch.setattr(runtime, "maybe_find_executable", lambda value=None: "/x/espeak-ng")
    monkeypatch.setattr(runtime, "find_executable", lambda value=None: "/x/espeak-ng")
    monkeypatch.setattr(runtime, "select_native", lambda **kwargs: (None, ()))
    monkeypatch.setattr(runtime, "CliBackend", DummyCli)
    instance = runtime.EspeakRuntime(prefer_exact_clauses=True)
    assert isinstance(instance._backend, DummyCli)
    assert "exact clause API" in instance._backend.kwargs["fallback_reason"]


def test_runtime_is_unusable_after_close(monkeypatch) -> None:
    from espeakng_runtime.errors import PhonemizationError

    monkeypatch.setattr(runtime, "find_executable", lambda value=None: "/x/espeak-ng")
    monkeypatch.setattr(runtime, "find_data", lambda *args, **kwargs: None)
    instance = runtime.EspeakRuntime(mode="cli")
    instance.close()
    with pytest.raises(PhonemizationError, match="closed"):
        instance.phonemize("hello", voice="en-us")
