from __future__ import annotations

import os
from typing import Any

try:
    from langfuse import get_client, observe
except Exception:  # pragma: no cover
    def observe(*args: Any, **kwargs: Any):
        def decorator(func):
            return func
        return decorator

    def get_client() -> Any:
        return _DummyClient()

    class _DummyClient:
        def update_current_trace(self, **kwargs: Any) -> None:
            return None

        def update_current_span(self, **kwargs: Any) -> None:
            return None

        def flush(self) -> None:
            return None


class _LangfuseContext:
    def update_current_trace(self, **kwargs: Any) -> None:
        get_client().update_current_trace(**kwargs)

    def update_current_observation(self, **kwargs: Any) -> None:
        usage_details = kwargs.pop("usage_details", None)
        metadata = kwargs.pop("metadata", None) or {}
        if usage_details:
            metadata = {**metadata, "usage_details": usage_details}
        get_client().update_current_span(metadata=metadata, **kwargs)

    def flush(self) -> None:
        get_client().flush()


try:
    langfuse_context = _LangfuseContext()
except Exception:  # pragma: no cover
    class _DummyContext:
        def update_current_trace(self, **kwargs: Any) -> None:
            return None

        def update_current_observation(self, **kwargs: Any) -> None:
            return None

        def flush(self) -> None:
            return None

    langfuse_context = _DummyContext()


def tracing_enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))
