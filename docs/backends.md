# Backends and discovery

## Automatic selection

`EspeakRuntime(mode="auto")` probes native libraries first, then falls back to the CLI executable. A requested exact capability filters native candidates to libraries exposing `espeak_TextToPhonemesWithTerminator`; if none is available, auto mode uses CLI best-effort behavior and records both `RuntimeInfo.fallback_code` and the detailed `RuntimeInfo.fallback_reason`. If a selected native library cannot initialize, auto mode uses the same fallback; `mode="native"` always raises instead.

Explicit constructor arguments override environment configuration. The discovery variables are `ESPEAKNG_RUNTIME_EXECUTABLE`, `ESPEAKNG_RUNTIME_LIBRARY`, and `ESPEAKNG_RUNTIME_DATA`.

## Inspection and diagnostics

`inspect_espeak(...)` returns an immutable, non-initializing `EspeakInspection` record. It reports CLI availability independently, the selected native library/source/data, and the ordered `LibraryProbe` records. Probes distinguish unloadable libraries, missing mandatory native symbols, and missing exact-clause support. Explicit libraries are authoritative and are the only library probed.

Diagnostic source labels such as `espeakng-loader`, `near-executable`, `system-espeak-ng`, `system-espeak`, `explicit`, and `cli` identify discovery paths. They are diagnostic strings, not an enum contract.

## Native backend

The native backend uses `ctypes`. eSpeak's selected voice and other state are process-global, so native calls share a process-wide lock and native manager. Only the final runtime using a library calls `espeak_Terminate`. Conflicting active library or data paths are rejected.

## CLI backend

The CLI backend starts eSpeak for each operation. An explicit data directory, the environment data directory, or data derived near the selected executable is used before any optional loader data. When `data` names `espeak-ng-data` or `espeak-data`, the CLI receives its parent directory through `--path`, matching native initialization. Otherwise the executable uses its own default data.

## Clause behavior

Exact native clauses preserve the complete eSpeak NG terminator code. The six common punctuation constants are comma, colon, semicolon, period, question mark, and exclamation mark. The sentence boundary is derived independently from the sentence-type bit.

Other backends use a documented best-effort punctuation splitter. Its output is useful for migration and ordinary processing, but it is not a substitute for exact native metadata.
