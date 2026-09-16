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

`prefer_exact_clauses=True` asks auto mode to prefer a native library that exposes the exact clause API. If no such library is available, auto mode falls back to the CLI backend and reports the fallback in `RuntimeInfo`; it does not make CLI clauses exact. Use `clauses(..., exact=True)` when the caller must require exact native terminator metadata. That call raises `CapabilityError` when the selected backend cannot provide it.

For strict reference checks:

```python
clauses = self._espeak.clauses(text, voice=voice, exact=True)
```
