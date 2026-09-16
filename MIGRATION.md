# Migration sketch

## KokoroG2P

Keep Kokoro-specific conversion outside this package:

```python
from espeakng_runtime import EspeakRuntime

self._espeak = EspeakRuntime(
    mode="cli" if use_cli else "auto",
    executable=legacy_executable,
    library=legacy_library,
    data=legacy_data,
)

raw = self._espeak.phonemize(
    text,
    voice=language,
    separator=None if use_tie else "_",
    use_tie=use_tie,
)
# existing kokorog2p from_espeak/raw-vocabulary handling follows here
```

`voice=` accepts language-style requests as well as concrete identifiers. The runtime resolves these requests against the active inventory, so a request such as `en-gb` can select the installed native identifier `en`. Normal requests do not select MBROLA implicitly. Call `resolve_voice(request, allow_mbrola=True)` or use an explicit `mb/...` or `mb-...` request when MBROLA is intended. `RuntimeInfo.version_tuple` provides normalized numeric version components.

The runtime owns Python-side backend cleanup. Prefer the context manager or call `close()` explicitly; an unclosed runtime is also protected by garbage-collection finalization. Closing a runtime releases its Python ownership, but the initialized native eSpeak library remains resident for the process lifetime because native state is process-global and older releases may be unsafe to terminate/reinitialize repeatedly. Subsequent compatible runtimes reuse it, and conflicting native library or data paths in the same process are rejected.

## PiperG2P

Keep Piper's clause composition and phone-id mapping outside this package:

```python
from espeakng_runtime import EspeakRuntime

self._espeak = EspeakRuntime(
    mode=mode,
    executable=legacy_executable,
    library=legacy_library,
    data=legacy_data,
    prefer_exact_clauses=(mode != "cli"),
)

clauses = self._espeak.clauses(text, voice=voice)
# existing Piper NFD/terminator/vowel-cluster composition follows here
```

`prefer_exact_clauses=True` asks auto mode to prefer a native library that exposes the exact clause API. If no such library is available, auto mode falls back to the CLI backend and reports the fallback code and detail in `RuntimeInfo`; it does not make CLI clauses exact. A selected native library that fails to initialize is handled the same way in auto mode. Native mode remains strict. Use `clauses(..., exact=True)` when the caller must require exact native terminator metadata. That call raises `CapabilityError` when the selected backend cannot provide it.

PiperG2P should use the runtime's exact `Clause` records and keep its own NFD composition, language-switch and ZWJ cleanup, punctuation policy, sentence grouping, vowel-cluster merging, raw block handling, lexicon overlays, and phoneme-ID mapping. If Piper requires its historical one-punctuation-at-a-time CLI fallback grouping, that splitter also remains in PiperG2P rather than becoming a runtime policy.

Use `inspect_espeak()` for non-initializing capability diagnostics instead of importing discovery internals. The runtime's source labels are diagnostic strings, and its structured fallback codes avoid parsing `fallback_reason`.
For strict reference checks:

```python
clauses = self._espeak.clauses(text, voice=voice, exact=True)
```
