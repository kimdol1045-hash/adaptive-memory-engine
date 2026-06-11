class AmeError(Exception):
    """Base error for Adaptive Memory Engine."""


class CorpusNotFoundError(AmeError):
    pass


class UnsupportedHardwareError(AmeError):
    pass


class LlmClientError(AmeError):
    pass


class LightRagBackendError(AmeError):
    pass
