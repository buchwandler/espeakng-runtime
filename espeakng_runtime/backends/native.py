"""Native ctypes backend for eSpeak/eSpeak NG."""

from __future__ import annotations

import ctypes
import threading
from collections.abc import Sequence
from pathlib import Path

from .._text import split_best_effort_clauses
from ..errors import (
    CapabilityError,
    EspeakConflictError,
    EspeakUnavailableError,
    PhonemizationError,
    VoiceNotFoundError,
)
from ..types import Clause, RuntimeInfo, Voice

AUDIO_OUTPUT_SYNCHRONOUS = 2
CHARS_UTF8 = 1
PHONEMES_IPA = 0x02
PHONEMES_TIE = 0x80

_TERMINATORS: dict[int, tuple[str, bool]] = {
    0x41000: (",", False),
    0x42000: (":", False),
    0x43000: (";", False),
    0x48000: (".", True),
    0x82000: ("?", True),
    0x83000: ("!", True),
}


class _VoiceStruct(ctypes.Structure):
    _fields_ = [
        ("name", ctypes.c_char_p),
        ("languages", ctypes.c_char_p),
        ("identifier", ctypes.c_char_p),
        ("gender", ctypes.c_ubyte),
        ("age", ctypes.c_ubyte),
        ("variant", ctypes.c_ubyte),
        ("xx1", ctypes.c_ubyte),
        ("score", ctypes.c_int),
        ("spare", ctypes.c_void_p),
    ]


def _decode(value: bytes | None) -> str:
    return value.decode("utf-8", errors="replace") if value else ""


def _voice_language(value: bytes | None) -> str:
    if not value:
        return ""
    # eSpeak language records are priority-byte + language strings. For the
    # common one-language case, skipping the first priority byte is sufficient.
    payload = value[1:] if len(value) > 1 else b""
    return payload.split(b"\0", 1)[0].decode("utf-8", errors="replace")


def _path_identity(value: str | None) -> str | None:
    if value is None:
        return None
    path = Path(value)
    if path.is_absolute() or path.exists():
        try:
            return str(path.resolve())
        except OSError:
            pass
    return value


def _init_data_path(data: str | None) -> bytes | None:
    if not data:
        return None
    path = Path(data)
    # espeak_Initialize accepts a path whose child is espeak-ng-data. Loader
    # packages generally return the espeak-ng-data directory itself.
    value = path.parent if path.name in {"espeak-ng-data", "espeak-data"} else path
    return str(value).encode("utf-8")


class _NativeManager:
    """One process-wide native runtime; eSpeak itself uses global state."""

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.library: ctypes.CDLL | None = None
        self.library_path: str | None = None
        self.data_path: str | None = None
        self.version: str | None = None
        self.users = 0

    def acquire(self, library_path: str, data_path: str | None) -> ctypes.CDLL:
        with self.lock:
            requested_library = _path_identity(library_path)
            requested_data = _path_identity(data_path)
            if self.library is not None:
                if _path_identity(self.library_path) != requested_library:
                    raise EspeakConflictError(
                        "a different eSpeak shared library is already active in this process"
                    )
                if requested_data and _path_identity(self.data_path) not in {None, requested_data}:
                    raise EspeakConflictError(
                        "a different eSpeak data directory is already active in this process"
                    )
                self.users += 1
                return self.library

            try:
                loaded = ctypes.CDLL(library_path)
            except OSError as exc:
                raise EspeakUnavailableError(
                    f"could not load eSpeak library {library_path!r}: {exc}"
                ) from exc
            self._configure(loaded)
            result = loaded.espeak_Initialize(
                AUDIO_OUTPUT_SYNCHRONOUS,
                0,
                _init_data_path(data_path),
                0,
            )
            if result < 0:
                raise EspeakUnavailableError(f"eSpeak initialization failed with code {result}")

            self.library = loaded
            self.library_path = library_path
            self.data_path = data_path
            if hasattr(loaded, "espeak_Info"):
                reported = ctypes.c_char_p()
                version = loaded.espeak_Info(ctypes.byref(reported))
                self.version = _decode(version)
                if reported.value:
                    self.data_path = _decode(reported.value)
            self.users = 1
            return loaded

    @staticmethod
    def _configure(library: ctypes.CDLL) -> None:
        library.espeak_Initialize.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
        ]
        library.espeak_Initialize.restype = ctypes.c_int
        library.espeak_SetVoiceByName.argtypes = [ctypes.c_char_p]
        library.espeak_SetVoiceByName.restype = ctypes.c_int
        library.espeak_Terminate.argtypes = []
        library.espeak_Terminate.restype = ctypes.c_int
        library.espeak_TextToPhonemes.argtypes = [
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_int,
            ctypes.c_int,
        ]
        library.espeak_TextToPhonemes.restype = ctypes.c_char_p
        if hasattr(library, "espeak_TextToPhonemesWithTerminator"):
            func = library.espeak_TextToPhonemesWithTerminator
            func.argtypes = [
                ctypes.POINTER(ctypes.c_void_p),
                ctypes.c_int,
                ctypes.c_int,
                ctypes.POINTER(ctypes.c_int),
            ]
            func.restype = ctypes.c_char_p
        if hasattr(library, "espeak_Info"):
            library.espeak_Info.argtypes = [ctypes.POINTER(ctypes.c_char_p)]
            library.espeak_Info.restype = ctypes.c_char_p
        if hasattr(library, "espeak_ListVoices"):
            library.espeak_ListVoices.argtypes = [ctypes.POINTER(_VoiceStruct)]
            library.espeak_ListVoices.restype = ctypes.POINTER(ctypes.POINTER(_VoiceStruct))

    def release(self) -> None:
        with self.lock:
            self.users = max(0, self.users - 1)
            if self.users == 0 and self.library is not None:
                try:
                    self.library.espeak_Terminate()
                finally:
                    self.library = None
                    self.library_path = None
                    self.data_path = None
                    self.version = None


_MANAGER = _NativeManager()


class NativeBackend:
    def __init__(
        self,
        *,
        library: str,
        data: str | None,
        executable: str | None,
        source: str,
        requested_mode: str,
        fallback_reason: str | None = None,
    ) -> None:
        self._closed = False
        self._library = _MANAGER.acquire(library, data)
        self._library_arg = library
        self._data_arg = data
        self._executable = executable
        self._source = source
        self._requested_mode = requested_mode
        self._fallback_reason = fallback_reason
        self.exact_clause_api = hasattr(self._library, "espeak_TextToPhonemesWithTerminator")

    @property
    def info(self) -> RuntimeInfo:
        return RuntimeInfo(
            requested_mode=self._requested_mode,  # type: ignore[arg-type]
            implementation="native",
            executable=self._executable,
            library=_MANAGER.library_path or self._library_arg,
            data=_MANAGER.data_path or self._data_arg,
            source=self._source,
            version=_MANAGER.version,
            exact_clause_api=self.exact_clause_api,
            parity="exact" if self.exact_clause_api else "best-effort",
            fallback_reason=self._fallback_reason,
        )

    def _ensure_open(self) -> None:
        if self._closed:
            raise PhonemizationError("native eSpeak backend is closed")

    def _set_voice(self, voice: str) -> None:
        result = self._library.espeak_SetVoiceByName(voice.encode("utf-8"))
        if result != 0:
            raise VoiceNotFoundError(f"eSpeak voice {voice!r} was not found (code {result})")

    @staticmethod
    def _phoneme_mode(
        separator: str | None,
        use_tie: bool,
        tie_char: str,
    ) -> int:
        mode = PHONEMES_IPA
        if use_tie:
            if not tie_char:
                raise ValueError("tie_char must not be empty")
            mode |= PHONEMES_TIE
            mode |= ord(tie_char[0]) << 8
        elif separator:
            mode |= ord(separator[0]) << 8
        return mode

    def _phonemize_locked(
        self,
        text: str,
        *,
        voice: str,
        separator: str | None,
        use_tie: bool,
        tie_char: str,
    ) -> str:
        if not text or not text.strip():
            return ""
        self._set_voice(voice)
        buffer = ctypes.create_string_buffer(text.encode("utf-8") + b"\0")
        pointer = ctypes.c_void_p(ctypes.addressof(buffer))
        mode = self._phoneme_mode(separator, use_tie, tie_char)
        chunks: list[str] = []
        while pointer.value:
            previous = pointer.value
            value = self._library.espeak_TextToPhonemes(ctypes.byref(pointer), CHARS_UTF8, mode)
            if pointer.value == previous:
                raise PhonemizationError("espeak_TextToPhonemes made no progress")
            if value:
                chunks.append(_decode(value))
        return " ".join(chunk.strip() for chunk in chunks if chunk.strip()).strip()

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
        with _MANAGER.lock:
            return self._phonemize_locked(
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
        with _MANAGER.lock:
            return [
                self._phonemize_locked(
                    text,
                    voice=voice,
                    separator=separator,
                    use_tie=use_tie,
                    tie_char=tie_char,
                )
                for text in texts
            ]

    def _exact_clauses_locked(self, text: str, voice: str) -> list[Clause]:
        self._set_voice(voice)
        buffer = ctypes.create_string_buffer(text.encode("utf-8") + b"\0")
        pointer = ctypes.c_void_p(ctypes.addressof(buffer))
        clauses: list[Clause] = []
        while pointer.value:
            previous = pointer.value
            terminator = ctypes.c_int(0)
            value = self._library.espeak_TextToPhonemesWithTerminator(
                ctypes.byref(pointer),
                CHARS_UTF8,
                PHONEMES_IPA,
                ctypes.byref(terminator),
            )
            if pointer.value == previous:
                raise PhonemizationError("espeak_TextToPhonemesWithTerminator made no progress")
            token, sentence_end = _TERMINATORS.get(terminator.value & 0xFFF000, (None, False))
            clauses.append(
                Clause(
                    phonemes=_decode(value),
                    terminator=token,
                    terminator_code=terminator.value,
                    sentence_end=sentence_end,
                )
            )
        return clauses

    def clauses(self, text: str, *, voice: str, exact: bool = False) -> list[Clause]:
        self._ensure_open()
        if not text:
            return []
        with _MANAGER.lock:
            if self.exact_clause_api:
                return self._exact_clauses_locked(text, voice)
            if exact:
                raise CapabilityError(
                    "loaded eSpeak library lacks espeak_TextToPhonemesWithTerminator"
                )
            return [
                Clause(
                    self._phonemize_locked(
                        body,
                        voice=voice,
                        separator=None,
                        use_tie=False,
                        tie_char="͡",
                    ),
                    terminator,
                    None,
                    sentence_end,
                )
                for body, terminator, sentence_end in split_best_effort_clauses(text)
            ]

    def list_voices(self, filter_name: str | None = None) -> list[Voice]:
        self._ensure_open()
        if not hasattr(self._library, "espeak_ListVoices"):
            raise CapabilityError("loaded eSpeak library does not expose espeak_ListVoices")
        spec: _VoiceStruct | None = None
        if filter_name:
            spec = _VoiceStruct()
            spec.languages = filter_name.encode("utf-8")
        with _MANAGER.lock:
            values = self._library.espeak_ListVoices(
                ctypes.byref(spec) if spec is not None else None
            )
            voices: list[Voice] = []
            index = 0
            while values and values[index]:
                item = values[index].contents
                voices.append(
                    Voice(
                        name=_decode(item.name).replace("_", " "),
                        language=_voice_language(item.languages),
                        identifier=_decode(item.identifier).replace("\\", "/"),
                        gender=int(item.gender),
                        age=int(item.age),
                    )
                )
                index += 1
            return voices

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            _MANAGER.release()
