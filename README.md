[![PyPI - Version](https://img.shields.io/pypi/v/espeakng-runtime)](https://pypi.org/project/espeakng-runtime/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/espeakng-runtime)
![PyPI - Downloads](https://img.shields.io/pypi/dm/espeakng-runtime)
[![codecov](https://codecov.io/gh/buchwandler/espeakng-runtime/graph/badge.svg?token=spJ8cG3cEK)](https://codecov.io/gh/buchwandler/espeakng-runtime)

# espeakng-runtime

A small Python runtime adapter for **eSpeak NG** phonemization.

The package deliberately does not implement G2P policy for Kokoro, Piper, or any
other model. It centralizes the shared eSpeak plumbing:

- executable, shared-library, and data discovery
- optional `espeakng-loader` integration
- native `ctypes` execution with process-wide locking
- CLI fallback
- voice enumeration
- IPA phonemization and batching
- exact native clause/terminator output when the loaded library exposes
  `espeak_TextToPhonemesWithTerminator`
- explicit runtime diagnostics/capabilities

## Layout

This project intentionally uses a flat package layout (no `src/` directory):

```text
espeakng_runtime/
tests/
pyproject.toml
```

## Versioning

The version is dynamic and comes from Git tags through `setuptools-scm`.
For source archives without Git metadata, the MVP falls back to `0.1.dev0` so
an unpacked zip remains installable.

```bash
git tag v0.1.0
python -m build
```

## Install

Use a system eSpeak/eSpeak NG installation:

```bash
pip install espeakng-runtime
```

Or install the optional binary/data loader:

```bash
pip install "espeakng-runtime[bundled]"
```

## Quick start

```python
from espeakng_runtime import EspeakRuntime

with EspeakRuntime(mode="auto") as espeak:
    print(espeak.info)
    print(espeak.phonemize("Hello world", voice="en-us"))
    print(espeak.phonemize("Hello world", voice="en-us", separator="_"))
    print(espeak.clauses("Hello, world!", voice="en-us"))
```

`mode` is `"auto"`, `"native"`, or `"cli"`. `auto` prefers a working native
library and falls back to the command-line executable.

For Piper-style exact clause handling, request an exact-capable runtime:

```python
from espeakng_runtime import EspeakRuntime

with EspeakRuntime(mode="auto", prefer_exact_clauses=True) as espeak:
    clauses = espeak.clauses("Hello, world!", voice="en-us", exact=True)
```

In `auto` mode, `prefer_exact_clauses=True` chooses an exact-capable native
library when possible and otherwise falls back to CLI best-effort clauses.
Calling `clauses(..., exact=True)` on a non-exact backend raises
`CapabilityError` rather than silently degrading.

## Configuration

Explicit constructor arguments take precedence over environment variables:

- `ESPEAKNG_RUNTIME_EXECUTABLE`
- `ESPEAKNG_RUNTIME_LIBRARY`
- `ESPEAKNG_RUNTIME_DATA`

The library intentionally does not read KokoroG2P/PiperG2P-specific variables;
those projects can map their legacy configuration into constructor arguments
during migration.

## MVP scope

The package returns raw eSpeak output. Model-specific transforms stay in their
consumer projects. In particular this MVP does **not** contain Kokoro phoneme
mapping, Piper NFD/phone composition, vowel-cluster merging, lexicons, or G2P
routing.
