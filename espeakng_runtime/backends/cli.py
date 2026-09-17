"""Command-line eSpeak backend."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Sequence

from .._text import normalize_phoneme_output, split_best_effort_clauses
from ..discovery import data_parent_for_espeak
from ..errors import CapabilityError, PhonemizationError
from ..types import Clause, FallbackCode, RuntimeInfo, Voice

_VERSION_RE = re.compile(r"(?:eSpeak NG|eSpeak)[^0-9]*([0-9]+(?:\.[0-9]+)+)", re.I)


class CliBackend:
    def __init__(
        self,
        *,
        executable: str,
        data: str | None,
        timeout: float | None,
        requested_mode: str,
        fallback_reason: str | None = None,
        fallback_code: FallbackCode | None = None,
    ) -> None:
        self.executable = executable
        self.data = data
        self.timeout = timeout
        self.requested_mode = requested_mode
        self.fallback_reason = fallback_reason
        self.fallback_code = fallback_code
        self._version: str | None = None

    def _run(
        self,
        args: list[str],
        *,
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [self.executable, *args]
        if self.data:
            command.append(f"--path={data_parent_for_espeak(self.data)}")
        try:
            process = subprocess.run(
                command,
                input=input_text,
                text=True,
                encoding="utf-8",
                errors="strict",
                capture_output=True,
                check=False,
                timeout=self.timeout,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise PhonemizationError(f"eSpeak CLI invocation failed: {exc}") from exc
        if process.returncode:
            raise PhonemizationError(
                f"eSpeak failed ({process.returncode}): {process.stderr.strip()}"
            )
        return process

    @property
    def version(self) -> str | None:
        if self._version is None:
            process = self._run(["--version"])
            output = f"{process.stdout}\n{process.stderr}"
            match = _VERSION_RE.search(output)
            self._version = match.group(1) if match else output.strip().splitlines()[0]
        return self._version

    @property
    def info(self) -> RuntimeInfo:
        return RuntimeInfo(
            requested_mode=self.requested_mode,  # type: ignore[arg-type]
            implementation="cli",
            executable=self.executable,
            data=self.data,
            source="cli",
            version=self.version,
            exact_clause_api=False,
            parity="best-effort",
            fallback_reason=self.fallback_reason,
            fallback_code=self.fallback_code,
        )

    @staticmethod
    def _phoneme_args(
        *,
        voice: str,
        separator: str | None,
        use_tie: bool,
        tie_char: str,
    ) -> list[str]:
        args = ["-q", "-x", "--ipa", f"-v{voice}"]
        if use_tie:
            if not tie_char:
                raise ValueError("tie_char must not be empty")
            args.append(f"--tie={tie_char[0]}")
        elif separator:
            args.append(f"--sep={separator[0]}")
        return args

    def phonemize(
        self,
        text: str,
        *,
        voice: str,
        separator: str | None = None,
        use_tie: bool = False,
        tie_char: str = "͡",
    ) -> str:
        if not text or not text.strip():
            return ""
        process = self._run(
            self._phoneme_args(
                voice=voice,
                separator=separator,
                use_tie=use_tie,
                tie_char=tie_char,
            ),
            input_text=text if text.endswith("\n") else f"{text}\n",
        )
        return normalize_phoneme_output(process.stdout)

    def phonemize_many(
        self,
        texts: Sequence[str],
        *,
        voice: str,
        separator: str | None = None,
        use_tie: bool = False,
        tie_char: str = "͡",
    ) -> list[str]:
        values = list(texts)
        nonempty = [text for text in values if text and text.strip()]
        if not nonempty:
            return [""] * len(values)
        process = self._run(
            self._phoneme_args(
                voice=voice,
                separator=separator,
                use_tie=use_tie,
                tie_char=tie_char,
            ),
            input_text="\n".join(nonempty) + "\n",
        )
        lines = process.stdout.splitlines()
        if len(lines) != len(nonempty):
            raise PhonemizationError(
                f"eSpeak returned {len(lines)} lines for {len(nonempty)} inputs"
            )
        iterator = iter(lines)
        result: list[str] = []
        for text in values:
            if not text or not text.strip():
                result.append("")
            else:
                result.append(normalize_phoneme_output(next(iterator)))
        return result

    def clauses(self, text: str, *, voice: str, exact: bool = False) -> list[Clause]:
        if exact:
            raise CapabilityError("CLI eSpeak does not expose exact clause terminator codes")
        parts = list(split_best_effort_clauses(text))
        if not parts:
            return []
        phonemes = self.phonemize_many(
            [body for body, _, _ in parts],
            voice=voice,
        )
        return [
            Clause(value, terminator, None, sentence_end)
            for value, (_, terminator, sentence_end) in zip(phonemes, parts, strict=True)
        ]

    def list_voices(self, filter_name: str | None = None) -> list[Voice]:
        args = [f"--voices={filter_name}"] if filter_name else ["--voices"]
        process = self._run(args)
        voices: list[Voice] = []
        for line in process.stdout.splitlines():
            line = line.strip()
            if not line or line.lower().startswith("pty"):
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            voices.append(
                Voice(
                    name=parts[3].replace("_", " "),
                    language=parts[1],
                    identifier=parts[4].replace("\\", "/"),
                )
            )
        return voices

    def close(self) -> None:
        return None
