# Backends and discovery

## Automatic selection

`EspeakRuntime(mode="auto")` probes native libraries first, then falls back to the CLI executable. A requested exact capability filters native candidates to libraries exposing `espeak_TextToPhonemesWithTerminator`; if none is available, auto mode uses CLI best-effort behavior and records the reason in `RuntimeInfo.fallback_reason`.

Explicit constructor arguments override environment configuration. The discovery variables are `ESPEAKNG_RUNTIME_EXECUTABLE`, `ESPEAKNG_RUNTIME_LIBRARY`, and `ESPEAKNG_RUNTIME_DATA`.

## Native backend

The native backend uses `ctypes`. eSpeak's selected voice and other state are process-global, so native calls share a process-wide lock and native manager. Only the final runtime using a library calls `espeak_Terminate`. Conflicting active library or data paths are rejected.

## CLI backend

The CLI backend starts eSpeak for each operation. An explicit data directory, the environment data directory, or data derived near the selected executable is used before any optional loader data. Otherwise the executable uses its own default data.

## Clause behavior

Exact native clauses preserve the complete eSpeak NG terminator code. The six common punctuation constants are comma, colon, semicolon, period, question mark, and exclamation mark. The sentence boundary is derived independently from the sentence-type bit.

Other backends use a documented best-effort punctuation splitter. Its output is useful for migration and ordinary processing, but it is not a substitute for exact native metadata.
