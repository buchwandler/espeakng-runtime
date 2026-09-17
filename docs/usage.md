# Usage

## Basic phonemization

```python
from espeakng_runtime import EspeakRuntime

with EspeakRuntime() as runtime:
    print(runtime.phonemize("Hello world", voice="en-us"))
```

The default `auto` mode prefers a usable native library and falls back to the CLI executable. Select a backend explicitly with `mode="native"` or `mode="cli"`.

## Regional locale selectors

Common locale-style selectors work across both backends:

```python
with EspeakRuntime(mode="auto") as runtime:
    runtime.phonemize("Haus", voice="de-de")
    runtime.phonemize("bonjour", voice="fr-fr")
    runtime.phonemize("hej", voice="sv-se")
```
## Options and batches

```python
with EspeakRuntime(mode="auto") as runtime:
    runtime.phonemize("Hello", voice="en-us", separator="_")
    runtime.phonemize("joined", voice="en-us", use_tie=True)
    runtime.phonemize_many(["One", "Two"], voice="en-us")
    runtime.phonemize(
        "Haus",
        voice="de-de",
        use_tie=True,
        tie_char="\u200d",
    )
```

`list_voices()` returns available `Voice` records. `runtime.info` returns a `RuntimeInfo` record describing discovery, implementation, version, parity, and capabilities.

Use `inspect_espeak(require_exact_clauses=True)` when a consumer needs to choose behavior before creating a runtime. Inspection probes libraries without calling `espeak_Initialize`; `LibraryProbe.missing_symbols` and `RuntimeInfo.fallback_code` are intended for diagnostics without parsing human-readable messages.

## Clauses

All backends support best-effort clause splitting. Native eSpeak NG libraries that expose `espeak_TextToPhonemesWithTerminator` also support exact clause metadata:

```python
with EspeakRuntime(prefer_exact_clauses=True) as runtime:
    clauses = runtime.clauses("One, two: three; four. Five? Six!", voice="en-us", exact=True)
```

Each `Clause` contains phonemes, a punctuation token, the raw `terminator_code`, and `sentence_end`. Calling `exact=True` on a backend without the native capability raises `CapabilityError`.

## Closing runtimes

Use the context manager for deterministic cleanup. After `close()`, a runtime is unusable and raises the backend's runtime error if an operation is attempted.
