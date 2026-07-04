"""Structured logging configuration for all AURA services.

Configures a consistent log format that includes the service name,
making it easy to filter logs when running the full stack.
"""
import logging
import sys

def configure_logging(service: str, level: str = "INFO") -> None:
    """Configures stdout logging for a service.

    Sets up a logging.StreamHandler writing to stdout with a
    format that includes the service name and log level.

    Args:
        service: Human-readable service name used as a prefix in every log line.
        level:   Log level string: "DEBUG", "INFO", "WARNING" or "ERROR".
    """
    logging.basicConfig(
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
        format=f"%(asctime)s [{service}] %(levelname)s %(name)s — %(message)s",
    )
