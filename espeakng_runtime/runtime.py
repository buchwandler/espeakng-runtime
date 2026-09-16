"""Public runtime facade."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from .backends.base import EspeakBackend
from .backends.cli import CliBackend
from .backends.native import NativeBackend
from .discovery import find_data, find_executable, maybe_find_executable, select_native
from .errors import EspeakUnavailableError
from .types import Clause, RuntimeInfo, Voice

Mode = Literal["auto", "native", "cli"]


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
        if candidate is not None:
            self._backend = NativeBackend(
                library=candidate.library,
                data=candidate.data,
                executable=found_executable,
                source=candidate.source,
                requested_mode=mode,
            )
            return

        details = "; ".join(
            f"{probe.library}: {probe.error or 'missing exact clause API'}" for probe in probes
        )
        if mode == "native":
            suffix = f" ({details})" if details else ""
            raise EspeakUnavailableError(f"no suitable native eSpeak library found{suffix}")

        reason = "no suitable native eSpeak library found"
        if prefer_exact_clauses:
            reason += " with exact clause API"
        cli_executable = find_executable(executable)
        self._backend = CliBackend(
            executable=cli_executable,
            data=find_data(data, executable=cli_executable),
            timeout=timeout,
            requested_mode=mode,
            fallback_reason=reason,
        )

    @property
    def info(self) -> RuntimeInfo:
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
        return self._backend.phonemize_many(
            texts,
            voice=voice,
            separator=separator,
            use_tie=use_tie,
            tie_char=tie_char,
        )

    def clauses(self, text: str, *, voice: str, exact: bool = False) -> list[Clause]:
        return self._backend.clauses(text, voice=voice, exact=exact)

    def list_voices(self, filter_name: str | None = None) -> list[Voice]:
        return self._backend.list_voices(filter_name)

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._backend.close()

    def __enter__(self) -> EspeakRuntime:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
