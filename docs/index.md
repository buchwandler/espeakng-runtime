# espeakng-runtime

`espeakng-runtime` is a small Python adapter around eSpeak and eSpeak NG for applications that need phonemization without embedding model-specific G2P policy.

It provides:

- native `ctypes` and command-line backends
- automatic executable, library, and data discovery
- optional `espeakng-loader` integration
- IPA phonemization and batching
- voice enumeration
- exact native clause terminator codes when supported
- runtime diagnostics and capability reporting

```{toctree}
:maxdepth: 2

installation
usage
backends
api
migration
changelog
```
