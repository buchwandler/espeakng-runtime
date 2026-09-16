# Migration

`espeakng-runtime` centralizes eSpeak discovery and phonemization while leaving model-specific mapping to the consumer.

## KokoroG2P and PiperG2P

Pass legacy executable, library, and data settings to the public constructor. The valid exact-clause preference argument is `prefer_exact_clauses`, not `require_exact_clauses`.

```python
from espeakng_runtime import EspeakRuntime

runtime = EspeakRuntime(
    mode="auto",
    executable=legacy_executable,
    library=legacy_library,
    data=legacy_data,
    prefer_exact_clauses=True,
)
```

Use `runtime.phonemize()` for raw IPA output. Keep Piper clause composition, terminator handling, phone IDs, and NFD mapping in PiperG2P. Keep Kokoro vocabulary conversion in KokoroG2P.

`prefer_exact_clauses=True` prefers an exact native backend in auto mode, but may fall back to CLI. Require exact behavior at the call site with `runtime.clauses(text, voice=voice, exact=True)`, which raises `CapabilityError` when exact native metadata is unavailable.
See the [migration sketch](https://github.com/buchwandler/espeakng-runtime/blob/main/MIGRATION.md) for complete consumer-oriented examples.
