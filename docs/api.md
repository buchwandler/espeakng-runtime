# API reference

## Types

```{eval-rst}
.. autodata:: espeakng_runtime.Mode
   :annotation: = Literal['auto', 'native', 'cli']
```

The `Mode` type constrains backend selection. Use `'auto'` to prefer native with CLI fallback, `'native'` to require the ctypes backend, or `'cli'` to force the subprocess backend.

## Runtime

```{eval-rst}
.. autoclass:: espeakng_runtime.EspeakRuntime
   :members:


`EspeakRuntime.resolve_voice(voice, allow_mbrola=False)` returns the concrete `Voice` selected from the active eSpeak inventory. Language-style requests such as `en-gb` are resolved consistently for native and CLI backends. Normal requests exclude MBROLA entries unless `allow_mbrola=True`; explicit `mb/...` and `mb-...` requests are accepted.

`RuntimeInfo.version_tuple` contains the first numeric version sequence from `RuntimeInfo.version`, or `()` when no version is reported.

`EspeakRuntime.native_probes` returns the `LibraryProbe` records from native library selection during construction. For `mode="cli"`, this is an empty tuple. Use `runtime.info` for the selected backend details and `runtime.native_probes` for what was considered during native selection.

.. autofunction:: espeakng_runtime.inspect_espeak
```

## Data models

```{eval-rst}
.. autoclass:: espeakng_runtime.RuntimeInfo
.. autoclass:: espeakng_runtime.Clause
.. autoclass:: espeakng_runtime.EspeakInspection
   :members:
.. autoclass:: espeakng_runtime.LibraryCandidate
.. autoclass:: espeakng_runtime.LibraryProbe
.. autoclass:: espeakng_runtime.Voice
```

## Errors

```{eval-rst}
.. automodule:: espeakng_runtime.errors
   :members:
```
