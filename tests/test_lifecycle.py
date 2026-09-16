from __future__ import annotations

import gc

from espeakng_runtime import EspeakRuntime


class CloseCountingBackend:
    def __init__(self) -> None:
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1


def make_runtime(backend: CloseCountingBackend) -> EspeakRuntime:
    runtime = object.__new__(EspeakRuntime)
    runtime._closed = False
    runtime._backend = backend
    runtime._voice_inventory = None
    runtime._resolved_voices = {}
    runtime._register_finalizer()
    return runtime


def test_explicit_close_is_idempotent() -> None:
    backend = CloseCountingBackend()
    runtime = make_runtime(backend)

    runtime.close()
    runtime.close()

    assert backend.close_calls == 1


def test_context_manager_closes_once() -> None:
    backend = CloseCountingBackend()
    runtime = make_runtime(backend)

    with runtime:
        pass

    assert backend.close_calls == 1


def test_unclosed_runtime_is_closed_by_garbage_collection() -> None:
    backend = CloseCountingBackend()
    runtime = make_runtime(backend)

    del runtime
    gc.collect()

    assert backend.close_calls == 1


def test_cli_style_backend_is_harmless_under_finalization() -> None:
    backend = CloseCountingBackend()
    runtime = make_runtime(backend)

    del runtime
    gc.collect()

    assert backend.close_calls == 1
