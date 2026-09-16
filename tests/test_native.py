from __future__ import annotations

import ctypes
from collections.abc import Iterator

import pytest

from espeakng_runtime.backends import native
from espeakng_runtime.errors import (
    CapabilityError,
    EspeakConflictError,
    EspeakUnavailableError,
    PhonemizationError,
    VoiceNotFoundError,
)


class FakeFunction:
    def __init__(self, function):
        self.function = function

    def __call__(self, *args):
        return self.function(*args)


class FakeNativeLibrary:
    def __init__(
        self,
        *,
        exact: bool = True,
        init_result: int = 0,
        voice_result: int = 0,
        no_progress: bool = False,
    ) -> None:
        self.init_result = init_result
        self.voice_result = voice_result
        self.no_progress = no_progress
        self.terminate_calls = 0
        self.initialize_calls = 0
        self.voices_calls = 0
        self.last_voice: bytes | None = None
        self._clause_index = 0

        self.espeak_Initialize = FakeFunction(self._initialize)
        self.espeak_SetVoiceByName = FakeFunction(self._set_voice)
        self.espeak_Terminate = FakeFunction(self._terminate)
        self.espeak_Info = FakeFunction(self._info)
        self.espeak_TextToPhonemes = FakeFunction(self._phonemes)
        self.espeak_ListVoices = FakeFunction(self._list_voices)
        if exact:
            self.espeak_TextToPhonemesWithTerminator = FakeFunction(self._exact_clauses)

    def _initialize(self, *_args: object) -> int:
        self.initialize_calls += 1
        return self.init_result

    def _set_voice(self, voice: bytes) -> int:
        self.last_voice = voice
        return self.voice_result

    def _terminate(self) -> int:
        self.terminate_calls += 1
        return 0

    def _info(self, reported: ctypes.c_void_p) -> bytes:
        ctypes.cast(reported, ctypes.POINTER(ctypes.c_char_p)).contents.value = b"/fake/data"
        return b"1.0"

    def _phonemes(self, pointer: ctypes.c_void_p, _input_type: int, _mode: int) -> bytes:
        value = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_void_p)).contents
        if not self.no_progress:
            value.value = 0
        return "həloʊ".encode()

    def _exact_clauses(
        self,
        pointer: ctypes.c_void_p,
        _input_type: int,
        _mode: int,
        terminator: ctypes.c_void_p,
    ) -> bytes:
        value = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_void_p)).contents
        code = [0x41014, 0x4001E, 0x4101E, 0x80028, 0x82028, 0x8302D][self._clause_index]
        self._clause_index += 1
        ctypes.cast(terminator, ctypes.POINTER(ctypes.c_int)).contents.value = code
        value.value = 0 if self._clause_index == 6 else self._clause_index
        return f"clause-{self._clause_index}".encode()

    def _list_voices(self, _spec: object):
        self.voices_calls += 1
        item = native._VoiceStruct(
            name=b"Alice",
            languages=b"\x05en-us",
            identifier=b"en-us",
            gender=2,
            age=30,
            variant=0,
            xx1=0,
            score=0,
            spare=None,
        )
        array_type = ctypes.POINTER(native._VoiceStruct) * 2
        return array_type(ctypes.pointer(item), None)


@pytest.fixture(autouse=True)
def reset_manager() -> Iterator[None]:
    manager = native._MANAGER
    with manager.lock:
        manager.library = None
        manager.library_path = None
        manager.data_path = None
        manager.version = None
        manager.users = 0
    yield
    with manager.lock:
        if manager.library is not None:
            manager.library.espeak_Terminate()
        manager.library = None
        manager.library_path = None
        manager.data_path = None
        manager.version = None
        manager.users = 0


def make_backend(
    monkeypatch: pytest.MonkeyPatch,
    library: FakeNativeLibrary,
    path: str = "/fake/lib.so",
    data: str | None = "/fake/data",
):
    monkeypatch.setattr(native.ctypes, "CDLL", lambda _path: library)
    return native.NativeBackend(
        library=path,
        data=data,
        executable=None,
        source="test",
        requested_mode="native",
    )


@pytest.mark.parametrize(
    ("code", "token", "sentence_end"),
    [
        (0x80028, ".", True),
        (0x82028, "?", True),
        (0x8302D, "!", True),
        (0x41014, ",", False),
        (0x4001E, ":", False),
        (0x4101E, ";", False),
    ],
)
def test_decode_exact_terminator(code: int, token: str, sentence_end: bool) -> None:
    assert native._decode_terminator(code) == (token, sentence_end)


def test_decode_unknown_preserves_sentence_bit() -> None:
    assert native._decode_terminator(0x80099) == (None, True)
    assert native._decode_terminator(0) == (None, False)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ("/x/espeak-ng-data", b"/x"),
        ("/x/espeak-data", b"/x"),
        ("/x", b"/x"),
        (None, None),
    ],
)
def test_native_data_path_normalization(data: str | None, expected: bytes | None) -> None:
    assert native._init_data_path(data) == expected


def test_exact_clause_conversion_preserves_codes(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = make_backend(monkeypatch, FakeNativeLibrary())
    clauses = backend.clauses("ignored", voice="en-us", exact=True)
    assert [clause.terminator for clause in clauses] == [",", ":", ";", ".", "?", "!"]
    assert [clause.sentence_end for clause in clauses] == [False, False, False, True, True, True]
    assert [clause.terminator_code for clause in clauses] == [
        0x41014,
        0x4001E,
        0x4101E,
        0x80028,
        0x82028,
        0x8302D,
    ]
    backend.close()


def test_native_initialization_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(EspeakUnavailableError, match="initialization failed"):
        make_backend(monkeypatch, FakeNativeLibrary(init_result=-1))
    assert native._MANAGER.library is None


def test_voice_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = make_backend(monkeypatch, FakeNativeLibrary(voice_result=1))
    with pytest.raises(VoiceNotFoundError):
        backend.phonemize("hello", voice="missing")
    backend.close()


def test_no_progress_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = make_backend(monkeypatch, FakeNativeLibrary(no_progress=True))
    with pytest.raises(PhonemizationError, match="no progress"):
        backend.phonemize("hello", voice="en-us")
    backend.close()


def test_exact_capability_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = make_backend(monkeypatch, FakeNativeLibrary(exact=False))
    assert not backend.info.exact_clause_api
    with pytest.raises(CapabilityError):
        backend.clauses("hello", voice="en-us", exact=True)
    backend.close()


def test_list_voices(monkeypatch: pytest.MonkeyPatch) -> None:
    library = FakeNativeLibrary()
    backend = make_backend(monkeypatch, library)
    assert [voice.name for voice in backend.list_voices()] == ["Alice"]
    assert library.voices_calls == 1
    backend.close()


def test_manager_reuses_library_without_terminating_final_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    library = FakeNativeLibrary()
    first = make_backend(monkeypatch, library)
    second = make_backend(monkeypatch, library)
    assert first._library is second._library
    assert native._MANAGER.users == 2
    first.close()
    assert library.terminate_calls == 0
    assert native._MANAGER.users == 1
    second.close()
    assert library.terminate_calls == 0
    assert native._MANAGER.users == 0
    assert native._MANAGER.library is library


def test_manager_reuses_initialized_library_after_all_users_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    library = FakeNativeLibrary()
    first = make_backend(monkeypatch, library)
    first.close()

    assert native._MANAGER.users == 0
    assert library.initialize_calls == 1
    assert library.terminate_calls == 0

    second = make_backend(monkeypatch, library)

    assert native._MANAGER.users == 1
    assert library.initialize_calls == 1
    assert library.terminate_calls == 0

    second.close()


def test_manager_rejects_conflicting_library_and_data(monkeypatch: pytest.MonkeyPatch) -> None:
    first = make_backend(monkeypatch, FakeNativeLibrary(), "/fake/one.so")
    with pytest.raises(EspeakConflictError, match="shared library"):
        make_backend(monkeypatch, FakeNativeLibrary(), "/fake/two.so")
    with pytest.raises(EspeakConflictError, match="data directory"):
        make_backend(monkeypatch, FakeNativeLibrary(), "/fake/one.so", "/fake/other-data")
    first.close()

    with pytest.raises(EspeakConflictError, match="shared library"):
        make_backend(monkeypatch, FakeNativeLibrary(), "/fake/two.so")
