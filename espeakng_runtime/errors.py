"""Public exceptions for espeakng-runtime."""


class EspeakError(RuntimeError):
    """Base class for runtime errors."""


class EspeakUnavailableError(EspeakError):
    """Raised when no requested eSpeak backend can be initialized."""


class EspeakConflictError(EspeakError):
    """Raised when incompatible native eSpeak configurations share a process."""


class PhonemizationError(EspeakError):
    """Raised when eSpeak fails while phonemizing text."""


class VoiceNotFoundError(PhonemizationError):
    """Raised when eSpeak cannot select a requested voice."""


class CapabilityError(EspeakError):
    """Raised when the active backend lacks a requested capability."""
