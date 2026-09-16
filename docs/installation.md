# Installation

## Requirements

Python 3.10 or newer is supported. Install eSpeak NG from your operating system package manager when using the native or CLI backends.

```console
python -m pip install espeakng-runtime
```

The optional `bundled` extra installs `espeakng-loader`, which supplies a native library and its data files when that package supports the current platform:

```console
python -m pip install "espeakng-runtime[bundled]"
```

The bundled extra does not change the package's public API and does not provide model-specific G2P conversion.

### Termux / Android

On Termux, prefer the native Termux eSpeak NG package rather than the
`bundled` extra. `espeakng-loader` publishes desktop/server Linux
manylinux builds, not Android/Bionic builds.

```console
pkg install espeak
python -m pip install espeakng-runtime
```

`EspeakRuntime(mode="auto")` or `mode="native"` can then discover the
Termux-provided shared library. Use `runtime.info` to confirm the selected
library and source.

## Development and documentation

```console
python -m pip install -e ".[dev,docs]"
```

Build the site with:

```console
python docs/make.py html
```

## Configuration

Constructor arguments take precedence over environment variables:

- `ESPEAKNG_RUNTIME_EXECUTABLE`
- `ESPEAKNG_RUNTIME_LIBRARY`
- `ESPEAKNG_RUNTIME_DATA`

Use `runtime.info` to inspect the selected implementation and resolved paths.
