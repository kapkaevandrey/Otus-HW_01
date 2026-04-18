class RetriesExceededError(Exception):
    """Exception means that number of attempts to process message exceeded max
    times."""


class ImproperlyConfiguredError(ValueError):
    """Exception means that there is incorrect parameters passed to extractor
    or consumer."""
