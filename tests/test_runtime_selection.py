from __future__ import annotations

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


def test_auto_falls_back_to_cli(monkeypatch) -> None:
    monkeypatch.setattr(runtime, "maybe_find_executable", lambda value=None: "/x/espeak-ng")
    monkeypatch.setattr(runtime, "find_executable", lambda value=None: "/x/espeak-ng")
    monkeypatch.setattr(runtime, "select_native", lambda **kwargs: (None, ()))
    monkeypatch.setattr(runtime, "CliBackend", DummyCli)
    instance = runtime.EspeakRuntime(prefer_exact_clauses=True)
    assert isinstance(instance._backend, DummyCli)
    assert "exact clause API" in instance._backend.kwargs["fallback_reason"]
