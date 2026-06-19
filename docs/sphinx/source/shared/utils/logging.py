"""
Structured logging configuration for all AURA services.

Configures a consistent log format that includes the service name,
making it easy to filter logs when running the full stack.
"""
import logging
import sys


def configure_logging(service: str, level: str = "INFO") -> None:
    """Configure stdout logging for a service.

    Sets up a :class:`logging.StreamHandler` writing to stdout with a
    format that includes the service name and log level.

    Args:
        service: Human-readable service name used as a prefix in every
                 log line, e.g. ``"api-gateway"`` or ``"device-service"``.
        level:   Log level string: ``"DEBUG"``, ``"INFO"``, ``"WARNING"``
                 or ``"ERROR"``. Defaults to ``"INFO"``.

    Example:
        >>> configure_logging("my-service", "DEBUG")
    """
    logging.basicConfig(
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
        format=f"%(asctime)s [{service}] %(levelname)s %(name)s — %(message)s",
    )
