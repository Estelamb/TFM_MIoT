"""
Compatibility shim — InferenceBackend has moved.

This module re-exports :class:`InferenceBackend` from its new location
at :mod:`aura_hw.backends.inference.base` so that any external code
that imported from the old path continues to work without changes.

New code should import directly from the new path:

    from aura_hw.backends.inference.base import InferenceBackend
"""
from aura_hw.backends.inference.base import InferenceBackend  # noqa: F401

__all__ = ["InferenceBackend"]
