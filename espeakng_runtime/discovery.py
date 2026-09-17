"""Cross-platform eSpeak executable/library/data discovery."""

from __future__ import annotations

import ctypes
import ctypes.util
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from .errors import EspeakUnavailableError

ENV_EXECUTABLE = "ESPEAKNG_RUNTIME_EXECUTABLE"
ENV_LIBRARY = "ESPEAKNG_RUNTIME_LIBRARY"
ENV_DATA = "ESPEAKNG_RUNTIME_DATA"


@dataclass(frozen=True, slots=True)
class EspeakPaths:
    executable: str | None = None
    library: str | None = None
    data: str | None = None
    source: str = "unknown"


@dataclass(frozen=True, slots=True)
class LibraryCandidate:
    library: str
    source: str
    data: str | None = None
    explicit: bool = False


@dataclass(frozen=True, slots=True)
class LibraryProbe:
    library: str
    source: str
    data: str | None
    loadable: bool
    exact_clause_api: bool
    phoneme_trace_api: bool = False
    error: str | None = None

    missing_symbols: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class EspeakInspection:
    """Non-initializing eSpeak capability and candidate inspection."""

    executable: str | None
    cli_available: bool
    require_exact_clauses: bool
    selected_library: str | None
    selected_source: str | None
    selected_data: str | None
    candidates: tuple[LibraryProbe, ...] = ()

    @property
    def native_available(self) -> bool:
        return self.selected_library is not None

    @property
    def exact_native_available(self) -> bool:
        return bool(
            self.selected_library
            and any(
                probe.library == self.selected_library and probe.exact_clause_api
                for probe in self.candidates
            )
        )

    @property
    def trace_native_available(self) -> bool:
        """True when the selected native library exposes the phoneme trace API."""
        return bool(
            self.selected_library
            and any(
                probe.library == self.selected_library and probe.phoneme_trace_api
                for probe in self.candidates
            )
        )

_REQUIRED_NATIVE_SYMBOLS = (
    "espeak_Initialize",
    "espeak_SetVoiceByName",
    "espeak_Terminate",
    "espeak_TextToPhonemes",
)
_EXACT_CLAUSE_SYMBOL = "espeak_TextToPhonemesWithTerminator"
_TRACE_SYMBOLS = (
    "espeak_SetPhonemeTrace",
    "espeak_SetPhonemeCallback",
    "espeak_Synth",
    "espeak_Synchronize",
)


def _loader_paths() -> tuple[str, str | None] | None:
    try:
        import espeakng_loader  # type: ignore[import-not-found,import-untyped]
    except ImportError:
        return None

    library = espeakng_loader.get_library_path()
    data = espeakng_loader.get_data_path()
    if library and Path(library).is_file():
        return str(Path(library)), str(data) if data else None
    return None


def _as_executable(value: str) -> str | None:
    path = Path(value).expanduser()
    if path.is_file():
        return str(path.resolve())
    found = shutil.which(value)
    return str(Path(found).resolve()) if found else None


def maybe_find_executable(explicit: str | None = None) -> str | None:
    configured = explicit or os.environ.get(ENV_EXECUTABLE)
    if configured:
        return _as_executable(configured)
    found = shutil.which("espeak-ng") or shutil.which("espeak")
    return str(Path(found).resolve()) if found else None


def find_executable(explicit: str | None = None) -> str:
    configured = explicit or os.environ.get(ENV_EXECUTABLE)
    found = maybe_find_executable(explicit)
    if found:
        return found
    if configured:
        raise EspeakUnavailableError(f"configured eSpeak executable does not exist: {configured}")
    raise EspeakUnavailableError(
        f"eSpeak executable was not found; install eSpeak NG or set {ENV_EXECUTABLE}"
    )


def _near_executable_candidates(executable: str | None) -> tuple[Path, ...]:
    if not executable:
        return ()
    path = Path(executable)
    try:
        path = path.resolve()
    except OSError:
        pass
    roots = (path.parent, path.parent.parent)
    patterns = (
        "libespeak-ng.so*",
        "libespeak.so*",
        "libespeak-ng.dylib",
        "libespeak.dylib",
        "libespeak-ng.dll",
        "espeak-ng.dll",
        "libespeak.dll",
        "espeak.dll",
    )
    values: list[Path] = []
    for root in roots:
        for directory in (root, root / "lib", root / "lib64", root / "bin"):
            for pattern in patterns:
                values.extend(path for path in directory.glob(pattern) if path.is_file())
    result: list[Path] = []
    for value in values:
        try:
            value = value.resolve()
        except OSError:
            pass
        if value not in result:
            result.append(value)
    return tuple(result)


def _derived_data(executable: str | None, library: str | None) -> str | None:
    candidates: list[Path] = []
    for value in (executable, library):
        if not value or ("/" not in value and "\\" not in value):
            continue
        path = Path(value)
        try:
            path = path.resolve()
        except OSError:
            pass
        roots = (path.parent, path.parent.parent)
        for root in roots:
            candidates.extend(
                (
                    root / "espeak-ng-data",
                    root / "share" / "espeak-ng-data",
                    root / "share" / "espeak-data",
                    root / "espeak-data",
                )
            )
    for candidate in candidates:
        if candidate.is_dir():
            return str(candidate)
    return None


def find_data(
    explicit: str | None = None,
    *,
    executable: str | None = None,
    library: str | None = None,
) -> str | None:
    configured = explicit or os.environ.get(ENV_DATA)
    if configured:
        path = Path(configured).expanduser()
        if path.is_dir():
            return str(path.resolve())
        raise EspeakUnavailableError(
            f"configured eSpeak data directory does not exist: {configured}"
        )
    loader = _loader_paths()
    if loader is not None and loader[1] and library is not None:
        if _identity(library) == _identity(loader[0]):
            return loader[1]
    return _derived_data(executable, library)


def data_parent_for_espeak(data: str | None) -> str | None:
    """Return the directory eSpeak expects for a public data path."""
    if not data:
        return None
    path = Path(data)
    return path.parent.as_posix() if path.name in {"espeak-ng-data", "espeak-data"} else data


def _identity(value: str) -> str:
    path = Path(value)
    if path.is_absolute() or path.exists():
        try:
            return str(path.resolve())
        except OSError:
            pass
    return value


def iter_library_candidates(
    explicit: str | None = None,
    *,
    executable: str | None = None,
    data: str | None = None,
) -> tuple[LibraryCandidate, ...]:
    configured = explicit or os.environ.get(ENV_LIBRARY)
    if configured:
        path = Path(configured).expanduser()
        value = str(path.resolve()) if path.is_file() else configured
        configured_data = data or os.environ.get(ENV_DATA)
        candidate_data: str | None
        if configured_data:
            data_path = Path(configured_data).expanduser()
            if not data_path.is_dir():
                raise EspeakUnavailableError(
                    f"configured eSpeak data directory does not exist: {configured_data}"
                )
            candidate_data = str(data_path.resolve())
        else:
            candidate_data = _derived_data(executable, value)
        return (LibraryCandidate(value, "explicit", candidate_data, True),)

    values: list[LibraryCandidate] = []
    loader = _loader_paths()
    if loader is not None:
        values.append(LibraryCandidate(loader[0], "espeakng-loader", loader[1]))

    found_executable = executable or maybe_find_executable()
    values.extend(
        LibraryCandidate(path.as_posix(), "near-executable")
        for path in _near_executable_candidates(found_executable)
    )

    for name, source in (("espeak-ng", "system-espeak-ng"), ("espeak", "system-espeak")):
        found = ctypes.util.find_library(name)
        if found:
            values.append(LibraryCandidate(found, source))

    result: list[LibraryCandidate] = []
    seen: set[str] = set()
    for candidate in values:
        identity = _identity(candidate.library)
        if identity in seen:
            continue
        seen.add(identity)
        candidate_data = (
            data or candidate.data or _derived_data(found_executable, candidate.library)
        )
        result.append(
            LibraryCandidate(
                library=candidate.library,
                source=candidate.source,
                data=candidate_data,
                explicit=candidate.explicit,
            )
        )
    return tuple(result)


def probe_library(candidate: LibraryCandidate) -> LibraryProbe:
    try:
        library = ctypes.CDLL(candidate.library)
    except OSError as exc:
        return LibraryProbe(
            candidate.library,
            candidate.source,
            candidate.data,
            False,
            False,
            str(exc),
        )
    missing_symbols = tuple(name for name in _REQUIRED_NATIVE_SYMBOLS if not hasattr(library, name))
    error = f"missing mandatory symbols: {', '.join(missing_symbols)}" if missing_symbols else None
    has_trace = all(hasattr(library, name) for name in _TRACE_SYMBOLS)
    return LibraryProbe(
        candidate.library,
        candidate.source,
        candidate.data,
        True,
        hasattr(library, _EXACT_CLAUSE_SYMBOL),
        has_trace,
        error,
        missing_symbols,
    )


def select_native(
    *,
    library: str | None = None,
    executable: str | None = None,
    data: str | None = None,
    require_exact_clauses: bool = False,
) -> tuple[LibraryCandidate | None, tuple[LibraryProbe, ...]]:
    probes: list[LibraryProbe] = []
    for candidate in iter_library_candidates(library, executable=executable, data=data):
        probe = probe_library(candidate)
        probes.append(probe)
        if (
            probe.loadable
            and not probe.missing_symbols
            and (probe.exact_clause_api or not require_exact_clauses)
        ):
            return candidate, tuple(probes)
    return None, tuple(probes)


def inspect_espeak(
    *,
    executable: str | None = None,
    library: str | None = None,
    data: str | None = None,
    require_exact_clauses: bool = False,
) -> EspeakInspection:
    """Inspect eSpeak candidates without initializing the native library."""
    resolved_executable = maybe_find_executable(executable)
    selected, probes = select_native(
        library=library,
        executable=resolved_executable,
        data=data,
        require_exact_clauses=require_exact_clauses,
    )
    return EspeakInspection(
        executable=resolved_executable,
        cli_available=resolved_executable is not None,
        require_exact_clauses=require_exact_clauses,
        selected_library=selected.library if selected else None,
        selected_source=selected.source if selected else None,
        selected_data=selected.data if selected else None,
        candidates=probes,
    )


def discover(
    *,
    executable: str | None = None,
    library: str | None = None,
    data: str | None = None,
    require_executable: bool = False,
) -> EspeakPaths:
    exe = find_executable(executable) if require_executable else maybe_find_executable(executable)
    candidate, _ = select_native(
        library=library,
        executable=exe,
        data=data,
        require_exact_clauses=False,
    )
    selected_library = candidate.library if candidate else None
    selected_data = find_data(
        data,
        executable=exe,
        library=selected_library,
    )
    source = candidate.source if candidate else ("cli" if exe else "unknown")
    return EspeakPaths(exe, selected_library, selected_data, source)
