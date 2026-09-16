"""Public runtime facade."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from .backends.base import EspeakBackend
from .backends.cli import CliBackend
from .backends.native import NativeBackend
from .discovery import (
    LibraryProbe,
    find_data,
    find_executable,
    maybe_find_executable,
    select_native,
)
from .errors import EspeakUnavailableError, PhonemizationError
from .types import Clause, FallbackCode, RuntimeInfo, Voice

Mode = Literal["auto", "native", "cli"]


def _probe_detail(probe: object) -> str:
    error = getattr(probe, "error", None)
    if error:
        return str(error)
    return "missing exact clause API"


def _selection_failure(
    probes: tuple[LibraryProbe, ...],
    *,
    prefer_exact_clauses: bool,
) -> tuple[FallbackCode, str]:
    if not probes:
        reason = "no suitable native eSpeak library found"
        if prefer_exact_clauses:
            reason += " with exact clause API"
        return "native-unavailable", reason
    details = "; ".join(f"{probe.library}: {_probe_detail(probe)}" for probe in probes)
    if all(not probe.loadable for probe in probes):
        code: FallbackCode = "native-load-error"
    elif prefer_exact_clauses and all(
        not probe.exact_clause_api or bool(probe.missing_symbols) for probe in probes
    ):
        code = "exact-clause-api-unavailable"
    else:
        code = "native-unavailable"
    reason = "no suitable native eSpeak library found"
    if prefer_exact_clauses:
        reason += " with exact clause API"
    return code, f"{reason}: {details}"


class EspeakRuntime:
    """Resolve and own one eSpeak backend.

    Native calls are serialized process-wide because eSpeak's public API uses
    global state, including the currently selected voice.
    """

    def __init__(
        self,
        *,
        mode: Mode = "auto",
        executable: str | None = None,
        library: str | None = None,
        data: str | None = None,
        timeout: float | None = None,
        prefer_exact_clauses: bool = False,
    ) -> None:
        if mode not in {"auto", "native", "cli"}:
            raise ValueError("mode must be 'auto', 'native', or 'cli'")
        self.mode = mode
        self._closed = False
        self._backend: EspeakBackend

        if mode == "cli":
            cli_executable = find_executable(executable)
            self._backend = CliBackend(
                executable=cli_executable,
                data=find_data(data, executable=cli_executable),
                timeout=timeout,
                requested_mode=mode,
            )
            return

        found_executable = maybe_find_executable(executable)
        candidate, probes = select_native(
            library=library,
            executable=found_executable,
            data=data,
            require_exact_clauses=prefer_exact_clauses,
        )
        native_init_error: EspeakUnavailableError | None = None
        if candidate is not None:
            try:
                self._backend = NativeBackend(
                    library=candidate.library,
                    data=candidate.data,
                    executable=found_executable,
                    source=candidate.source,
                    requested_mode=mode,
                )
            except EspeakUnavailableError as exc:
                if mode == "native":
                    raise
                native_init_error = exc
            else:
                return

        if native_init_error is None:
            fallback_code, reason = _selection_failure(
                probes, prefer_exact_clauses=prefer_exact_clauses
            )
        else:
            fallback_code = "native-init-failed"
            reason = f"native eSpeak initialization failed: {native_init_error}"
        if mode == "native":
            raise EspeakUnavailableError(reason)
        try:
            cli_executable = find_executable(executable)
            cli_data = find_data(data, executable=cli_executable)
        except EspeakUnavailableError as cli_error:
            if native_init_error is not None:
                raise EspeakUnavailableError(
                    f"{reason}; CLI fallback unavailable: {cli_error}"
                ) from cli_error
            raise
        self._backend = CliBackend(
            executable=cli_executable,
            data=cli_data,
            timeout=timeout,
            requested_mode=mode,
            fallback_reason=reason,
            fallback_code=fallback_code,
        )

    def _ensure_open(self) -> None:
        if self._closed:
            raise PhonemizationError("eSpeak runtime is closed")

    @property
    def info(self) -> RuntimeInfo:
        self._ensure_open()
        return self._backend.info

    def phonemize(
        self,
        text: str,
        *,
        voice: str,
        separator: str | None = None,
        use_tie: bool = False,
        tie_char: str = "͡",
    ) -> str:
        self._ensure_open()
        return self._backend.phonemize(
            text,
            voice=voice,
            separator=separator,
            use_tie=use_tie,
            tie_char=tie_char,
        )

    def phonemize_many(
        self,
        texts: Sequence[str],
        *,
        voice: str,
        separator: str | None = None,
        use_tie: bool = False,
        tie_char: str = "͡",
    ) -> list[str]:
        self._ensure_open()
        return self._backend.phonemize_many(
            texts,
            voice=voice,
            separator=separator,
            use_tie=use_tie,
            tie_char=tie_char,
        )

    def clauses(self, text: str, *, voice: str, exact: bool = False) -> list[Clause]:
        self._ensure_open()
        return self._backend.clauses(text, voice=voice, exact=exact)

    def list_voices(self, filter_name: str | None = None) -> list[Voice]:
        self._ensure_open()
        return self._backend.list_voices(filter_name)

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._backend.close()

    def __enter__(self) -> EspeakRuntime:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
