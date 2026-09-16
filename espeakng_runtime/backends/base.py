"""Backend protocol."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from ..types import Clause, RuntimeInfo, Voice


class EspeakBackend(Protocol):
    @property
    def info(self) -> RuntimeInfo: ...

    def phonemize(
        self,
        text: str,
        *,
        voice: str,
        separator: str | None = None,
        use_tie: bool = False,
        tie_char: str = "͡",
    ) -> str: ...

    def phonemize_many(
        self,
        texts: Sequence[str],
        *,
        voice: str,
        separator: str | None = None,
        use_tie: bool = False,
        tie_char: str = "͡",
    ) -> list[str]: ...

    def clauses(self, text: str, *, voice: str, exact: bool = False) -> list[Clause]: ...

    def list_voices(self, filter_name: str | None = None) -> list[Voice]: ...

    def close(self) -> None: ...
