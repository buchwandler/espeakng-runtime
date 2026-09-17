# Backends and discovery

## Automatic selection

`EspeakRuntime(mode="auto")` probes native libraries first, then falls back to the CLI executable. A requested exact capability filters native candidates to libraries exposing `espeak_TextToPhonemesWithTerminator`; if none is available, auto mode uses CLI best-effort behavior and records both `RuntimeInfo.fallback_code` and the detailed `RuntimeInfo.fallback_reason`. If a selected native library cannot initialize, auto mode uses the same fallback; `mode="native"` always raises instead.

Explicit constructor arguments override environment configuration. The discovery variables are `ESPEAKNG_RUNTIME_EXECUTABLE`, `ESPEAKNG_RUNTIME_LIBRARY`, and `ESPEAKNG_RUNTIME_DATA`.

## Inspection and diagnostics

`inspect_espeak(...)` returns an immutable, non-initializing `EspeakInspection` record. It reports CLI availability independently, the selected native library/source/data, and the ordered `LibraryProbe` records. Probes distinguish unloadable libraries, missing mandatory native symbols, and missing exact-clause support. Explicit libraries are authoritative and are the only library probed.

Diagnostic source labels such as `espeakng-loader`, `near-executable`, `system-espeak-ng`, `system-espeak`, `explicit`, and `cli` identify discovery paths. They are diagnostic strings, not an enum contract.

## Native backend

The native backend uses `ctypes`. eSpeak's selected voice and other state are process-global, so native calls share a process-wide lock and native manager. Closing a runtime releases its Python ownership; the initialized native library remains resident for the process lifetime rather than being terminated and reinitialized repeatedly. Compatible runtimes reuse it, and conflicting library or data paths are rejected.

### Voice selector resolution

The native backend resolves voice selectors using a two-step strategy:

1. **Name lookup**: `espeak_SetVoiceByName(selector)` — succeeds for explicit eSpeak voice names and identifiers.
2. **Language property fallback**: when name lookup fails and the native library exposes `espeak_SetVoiceByProperties`, the backend retries using `espeak_SetVoiceByProperties(languages=selector)`.

This is a compatibility strategy, not a BCP-47 implementation in Python. It allows common locale-style selectors such as `de-de`, `en-gb`, `fr-fr`, `sv-se`, and `pt-br` to work natively without consumers maintaining their own alias tables.

```text
CLI:
    eSpeak -v<selector>

Native:
    SetVoiceByName(selector)
    -> if not found:
       SetVoiceByProperties(languages=selector)
```

Older eSpeak libraries that lack `espeak_SetVoiceByProperties` fall back to name-only lookup. Both failures raise `VoiceNotFoundError` with diagnostic codes for each attempt.

`EspeakRuntime` resolves each `voice=` request against the active voice inventory and passes the selected concrete identifier to either backend. Matching prefers exact language, identifier, identifier basename, and then base language, in that order, while preserving inventory order for ties. Identifiers are compared case-insensitively with underscores and Windows separators normalized.

Standard language requests exclude MBROLA entries. Explicit `mb/...` or `mb-...` requests can select MBROLA, and `resolve_voice(..., allow_mbrola=True)` enables it for a normal request when no preferred standard match exists. Voice inventory and resolved requests are cached per runtime instance. If a backend cannot enumerate voices, the requested identifier is passed through for backend-level validation.

## CLI backend

The CLI backend starts eSpeak for each operation. An explicit data directory, the environment data directory, or data derived near the selected executable is used before any optional loader data. When `data` names `espeak-ng-data` or `espeak-data`, the CLI receives its parent directory through `--path`, matching native initialization. Otherwise the executable uses its own default data.

## Clause behavior

Exact native clauses preserve the complete eSpeak NG terminator code. The six common punctuation constants are comma, colon, semicolon, period, question mark, and exclamation mark. The sentence boundary is derived independently from the sentence-type bit.

Other backends use a documented best-effort punctuation splitter. Its output is useful for migration and ordinary processing, but it is not a substitute for exact native metadata.

## Phoneme output semantics

The native backend supports two phoneme output paths:

### Native trace (CLI-equivalent)

When the native library exposes `espeak_SetPhonemeCallback`, `espeak_Synth`, and `espeak_Synchronize`, the backend uses the synthesis trace path. This produces phoneme output identical to the CLI's `-x --ipa` mode, including stress markers on weak words and contractions.

```text
RuntimeInfo.phoneme_output_api = "native-trace"
RuntimeInfo.phoneme_parity = "exact"
```

### Native translation (legacy)

Older libraries or builds without trace symbols use the `espeak_TextToPhonemes` direct translation API. This path may produce different stress semantics than the CLI for some words.

```text
RuntimeInfo.phoneme_output_api = "native-translation"
RuntimeInfo.phoneme_parity = "best-effort"
```

### CLI backend

The CLI backend always uses the eSpeak executable's synthesis phoneme output.

```text
RuntimeInfo.phoneme_output_api = "cli"
RuntimeInfo.phoneme_parity = "exact"
```

### Auto-mode behavior

When `mode="auto"`, the runtime prefers native trace when available. This ensures `mode="auto"` produces CLI-equivalent phoneme output on modern eSpeak NG installations.

The `parity` field on `RuntimeInfo` is preserved for backward compatibility but relates to exact clause API support, not phoneme output semantics. Use `phoneme_output_api` and `phoneme_parity` for phoneme-level diagnostics.
