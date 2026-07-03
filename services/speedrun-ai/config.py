# Copyright: Speedrun contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""
Env-driven settings for the AI generation service.

OFF-BY-DEFAULT CONTRACT
-----------------------
AI generation is a graded kill-switch. The service is ENABLED only when BOTH:

  * ``SPEEDRUN_AI_ENABLED`` is truthy (default "0"/off), AND
  * ``OPENAI_API_KEY`` is present (non-empty).

If either is missing the service refuses to generate (the FastAPI ``/generate``
route returns HTTP 503). The correctness of the study app must never depend on
this service being up.

The API key is NEVER printed, logged, or serialized. ``__repr__`` masks it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

_TRUTHY = frozenset({"1", "true", "yes", "on", "y", "t"})

# A current, configurable default model. Overridable via OPENAI_MODEL.
DEFAULT_MODEL = "gpt-4o"


def _is_truthy(value: str | None) -> bool:
    return bool(value) and value.strip().lower() in _TRUTHY


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of the service configuration.

    Read once from the environment via :func:`load_settings`. The API key is
    held but never emitted — :meth:`__repr__` masks it.
    """

    enabled_flag: bool
    api_key: str | None
    model: str

    @property
    def has_key(self) -> bool:
        return bool(self.api_key)

    def is_enabled(self) -> bool:
        """True iff the flag is truthy AND an API key is present."""
        return self.enabled_flag and self.has_key

    def __repr__(self) -> str:  # never leak the key
        return (
            "Settings("
            f"enabled_flag={self.enabled_flag}, "
            f"has_key={self.has_key}, "
            f"model={self.model!r})"
        )


def load_settings() -> Settings:
    """Build a :class:`Settings` snapshot from the current environment."""
    key = os.environ.get("OPENAI_API_KEY") or None
    return Settings(
        enabled_flag=_is_truthy(os.environ.get("SPEEDRUN_AI_ENABLED")),
        api_key=key,
        model=os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL,
    )


def is_enabled() -> bool:
    """Convenience: is the service enabled right now (reads the environment)."""
    return load_settings().is_enabled()
