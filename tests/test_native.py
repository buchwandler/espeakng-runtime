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
        trace: bool = True,
        init_result: int = 0,
        voice_result: int = 0,
        voice_by_properties_result: int | None = 0,
        no_progress: bool = False,
        synth_result: int = 0,
    ) -> None:
        self.init_result = init_result
        self.voice_result = voice_result
        self.voice_by_properties_result = voice_by_properties_result
        self.no_progress = no_progress
        self.synth_result = synth_result
        self.terminate_calls = 0
        self.initialize_calls = 0
        self.voices_calls = 0
        self.last_voice: bytes | None = None
        self.last_voice_properties_language: bytes | None = None
        self.set_voice_by_name_calls = 0
        self.set_voice_by_properties_calls = 0
        self._clause_index = 0

        # Trace-specific state
        self.last_phoneme_mode: int | None = None
        self.last_callback: object | None = None
        self.set_phoneme_callback_calls = 0
        self.last_synth_text: bytes | None = None
        self.synth_calls = 0
        self.synchronize_calls = 0
        self.last_trace_mode: int | None = None
        self.last_trace_stream: object | None = None
        self.set_phoneme_trace_calls = 0

        self.espeak_Initialize = FakeFunction(self._initialize)
        self.espeak_SetVoiceByName = FakeFunction(self._set_voice)
        self.espeak_Terminate = FakeFunction(self._terminate)
        self.espeak_Info = FakeFunction(self._info)
        self.espeak_TextToPhonemes = FakeFunction(self._phonemes)
        self.espeak_ListVoices = FakeFunction(self._list_voices)
        if voice_by_properties_result is not None:
            self.espeak_SetVoiceByProperties = FakeFunction(self._set_voice_by_properties)
        if exact:
            self.espeak_TextToPhonemesWithTerminator = FakeFunction(self._exact_clauses)
        if trace:
            self.espeak_SetPhonemeTrace = FakeFunction(self._set_phoneme_trace)
            self.espeak_SetPhonemeCallback = FakeFunction(self._set_phoneme_callback)
            self.espeak_Synth = FakeFunction(self._synth)
            self.espeak_Synchronize = FakeFunction(self._synchronize)

    def _initialize(self, *_args: object) -> int:
        self.initialize_calls += 1
        return self.init_result

    def _set_voice(self, voice: bytes) -> int:
        self.last_voice = voice
        self.set_voice_by_name_calls += 1
        return self.voice_result

    def _set_voice_by_properties(self, spec_ptr: ctypes.c_void_p) -> int:
        spec = ctypes.cast(spec_ptr, ctypes.POINTER(native._VoiceStruct)).contents
        self.last_voice_properties_language = spec.languages
        self.set_voice_by_properties_calls += 1
        return self.voice_by_properties_result

    def _terminate(self) -> int:
        self.terminate_calls += 1
        return 0

    def _info(self, reported: ctypes.c_void_p) -> bytes:
        ctypes.cast(reported, ctypes.POINTER(ctypes.c_char_p)).contents.value = b"/fake/data"
        return b"1.0"

    def _phonemes(self, pointer: ctypes.c_void_p, _input_type: int, mode: int) -> bytes:
        self.last_phoneme_mode = mode
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

    def _set_phoneme_trace(self, mode: int, stream: object) -> None:
        self.last_trace_mode = mode
        self.last_trace_stream = stream
        self.set_phoneme_trace_calls += 1

    def _set_phoneme_callback(self, callback: object) -> object:
        self.last_callback = callback
        self.set_phoneme_callback_calls += 1
        return callback  # Return the callback as previous

    def _synth(
        self,
        text: bytes,
        size: int,
        position: int,
        position_type: int,
        end_position: int,
        flags: int,
        synth_id_ptr: ctypes.c_void_p,
        user_data: object,
    ) -> int:
        self.last_synth_text = text
        self.synth_calls += 1
        # Simulate callback invocation if registered
        if self.last_callback is not None:
            # Call the callback with fake phoneme output
            try:
                self.last_callback("həloʊ".encode())
            except Exception:
                pass
        return self.synth_result

    def _synchronize(self) -> None:
        self.synchronize_calls += 1
    def _initialize(self, *_args: object) -> int:
        self.initialize_calls += 1
        return self.init_result

    def _set_voice(self, voice: bytes) -> int:
        self.last_voice = voice
        self.set_voice_by_name_calls += 1
        return self.voice_result

    def _set_voice_by_properties(self, spec_ptr: ctypes.c_void_p) -> int:
        spec = ctypes.cast(spec_ptr, ctypes.POINTER(native._VoiceStruct)).contents
        self.last_voice_properties_language = spec.languages
        self.set_voice_by_properties_calls += 1
        return self.voice_by_properties_result

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
    library = FakeNativeLibrary(voice_result=1, voice_by_properties_result=None)
    backend = make_backend(monkeypatch, library)
    with pytest.raises(VoiceNotFoundError):
        backend.phonemize("hello", voice="missing")
    backend.close()


def test_no_progress_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = make_backend(monkeypatch, FakeNativeLibrary(no_progress=True, trace=False))
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
        make_backend(monkeypatch, FakeNativeLibrary(), "/fake/two.so")


def test_explicit_name_succeeds_skips_properties(monkeypatch: pytest.MonkeyPatch) -> None:
    """SetVoiceByName succeeds -> SetVoiceByProperties must not be called."""
    library = FakeNativeLibrary(voice_result=0)
    backend = make_backend(monkeypatch, library)
    backend.phonemize("hello", voice="en-us")
    assert library.set_voice_by_name_calls == 1
    assert library.set_voice_by_properties_calls == 0
    backend.close()


def test_name_fails_property_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """SetVoiceByName fails -> SetVoiceByProperties(languages=selector) succeeds."""
    library = FakeNativeLibrary(voice_result=1, voice_by_properties_result=0)
    backend = make_backend(monkeypatch, library)
    result = backend.phonemize("hello", voice="de-de")
    assert result  # phonemization succeeded
    assert library.set_voice_by_name_calls == 1
    assert library.set_voice_by_properties_calls == 1
    assert library.last_voice_properties_language == b"de-de"
    backend.close()


def test_both_name_and_property_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both lookups fail -> VoiceNotFoundError with selector in diagnostic."""
    library = FakeNativeLibrary(voice_result=1, voice_by_properties_result=1)
    backend = make_backend(monkeypatch, library)
    with pytest.raises(VoiceNotFoundError, match="xx-yy") as exc_info:
        backend.phonemize("hello", voice="xx-yy")
    assert "name lookup code 1" in str(exc_info.value)
    assert "language lookup code 1" in str(exc_info.value)
    backend.close()


def test_properties_api_absent_name_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Older library without SetVoiceByProperties: failed name raises VoiceNotFoundError."""
    library = FakeNativeLibrary(voice_result=1, voice_by_properties_result=None)
    backend = make_backend(monkeypatch, library)
    with pytest.raises(VoiceNotFoundError, match="xx-yy") as exc_info:
        backend.phonemize("hello", voice="xx-yy")
    assert "language-property lookup unavailable" in str(exc_info.value)
    backend.close()


def test_properties_api_absent_name_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Older library without SetVoiceByProperties: successful name still works."""
    library = FakeNativeLibrary(voice_result=0, voice_by_properties_result=None)
    backend = make_backend(monkeypatch, library)
    result = backend.phonemize("hello", voice="en-us")
    assert result
    assert library.set_voice_by_name_calls == 1
    backend.close()


def test_voice_selection_stays_inside_manager_lock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Repeated phonemize calls verify voice selection is inside the lock."""
    library = FakeNativeLibrary(voice_result=0)
    backend = make_backend(monkeypatch, library)
    for _ in range(5):
        backend.phonemize("hello", voice="en-us")
    assert library.set_voice_by_name_calls == 5
    backend.close()


# --- Trace capability tests ---


def test_native_trace_capability_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    """Backend reports phoneme_trace_api when trace symbols are present."""
    backend = make_backend(monkeypatch, FakeNativeLibrary(trace=True))
    assert backend.phoneme_trace_api
    assert backend.info.phoneme_output_api == "native-trace"
    assert backend.info.phoneme_parity == "exact"
    backend.close()


def test_native_trace_capability_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Backend reports native-translation when trace symbols are absent."""
    backend = make_backend(monkeypatch, FakeNativeLibrary(trace=False))
    assert not backend.phoneme_trace_api
    assert backend.info.phoneme_output_api == "native-translation"
    assert backend.info.phoneme_parity == "best-effort"
    backend.close()


def test_trace_path_is_preferred_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """Trace path is used when trace symbols are available."""
    library = FakeNativeLibrary(trace=True)
    backend = make_backend(monkeypatch, library)
    backend.phonemize("hello", voice="en-us")
    assert library.synth_calls == 1
    assert library.synchronize_calls == 1
    backend.close()


def test_translation_path_used_without_trace(monkeypatch: pytest.MonkeyPatch) -> None:
    """Legacy translation path used when trace symbols are absent."""
    library = FakeNativeLibrary(trace=False)
    backend = make_backend(monkeypatch, library)
    result = backend.phonemize("hello", voice="en-us")
    assert result == "həloʊ"
    assert library.synth_calls == 0
    backend.close()


def test_tie_mode_forwarded_to_trace(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tie mode is forwarded to trace API."""
    library = FakeNativeLibrary(trace=True)
    backend = make_backend(monkeypatch, library)
    backend.phonemize("hello", voice="en-us", use_tie=True, tie_char="\u200d")
    # Check that SetPhonemeTrace was called with the correct mode
    # PHONEMES_IPA | PHONEMES_TIE | (ord('\u200d') << 8)
    expected_mode = 0x02 | 0x80 | (ord('\u200d') << 8)
    assert library.last_trace_mode == expected_mode
    backend.close()


def test_separator_mode_forwarded_to_trace(monkeypatch: pytest.MonkeyPatch) -> None:
    """Separator mode is forwarded to trace API."""
    library = FakeNativeLibrary(trace=True)
    backend = make_backend(monkeypatch, library)
    backend.phonemize("hello", voice="en-us", separator="_")
    # PHONEMES_IPA | (ord('_') << 8)
    expected_mode = 0x02 | (ord('_') << 8)
    assert library.last_trace_mode == expected_mode
    backend.close()


def test_callback_is_retained(monkeypatch: pytest.MonkeyPatch) -> None:
    """Callback object is retained to prevent GC during synthesis."""
    library = FakeNativeLibrary(trace=True)
    backend = make_backend(monkeypatch, library)
    backend.phonemize("hello", voice="en-us")
    assert library.set_phoneme_callback_calls == 2  # set + restore
    assert backend._phoneme_callback_obj is None  # cleared after synthesis
    backend.close()


def test_synthesis_failure_maps_to_phonemization_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """espeak_Synth failure raises PhonemizationError."""
    library = FakeNativeLibrary(trace=True, synth_result=1)  # non-zero = error
    backend = make_backend(monkeypatch, library)
    with pytest.raises(PhonemizationError, match="espeak_Synth failed"):
        backend.phonemize("hello", voice="en-us")
    backend.close()


def test_trace_phonemize_returns_correct_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """Trace path returns normalized phoneme output."""
    library = FakeNativeLibrary(trace=True)
    backend = make_backend(monkeypatch, library)
    result = backend.phonemize("hello", voice="en-us")
    assert result == "həloʊ"
    backend.close()
