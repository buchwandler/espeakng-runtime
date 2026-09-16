# API reference

## Runtime

```{eval-rst}
.. autoclass:: espeakng_runtime.EspeakRuntime
   :members:


`EspeakRuntime.resolve_voice(voice, allow_mbrola=False)` returns the concrete `Voice` selected from the active eSpeak inventory. Language-style requests such as `en-gb` are resolved consistently for native and CLI backends. Normal requests exclude MBROLA entries unless `allow_mbrola=True`; explicit `mb/...` and `mb-...` requests are accepted.

`RuntimeInfo.version_tuple` contains the first numeric version sequence from `RuntimeInfo.version`, or `()` when no version is reported.
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
