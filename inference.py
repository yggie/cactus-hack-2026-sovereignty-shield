"""Local LLM inference via Cactus Compute Engine.

All inference runs on-device via LFM2.5-1.2B-Instruct. No cloud fallback.

The Cactus Python bindings live in cactus/python/src/ (cloned repo)
and the built dylib at cactus/cactus/build/libcactus.dylib.
"""

from __future__ import annotations

import atexit
import json
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Resolve paths relative to this file (project root)
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent
_CACTUS_PYTHON_SRC = _PROJECT_ROOT / "cactus" / "python" / "src"

# Model weight locations (first match wins)
_WEIGHT_CANDIDATES = [
    _PROJECT_ROOT / ".venv" / "lib" / "python3.12" / "weights" / "lfm2.5-1.2b-instruct",
    _PROJECT_ROOT / "cactus" / "weights" / "lfm2.5-1.2b-instruct",
    Path.home() / ".cactus" / "models" / "lfm2.5-1.2b-instruct",
]

MODEL_NAME = "lfm2.5-1.2b-instruct"

# ---------------------------------------------------------------------------
# Import the Cactus FFI bindings
# ---------------------------------------------------------------------------
if _CACTUS_PYTHON_SRC.is_dir():
    sys.path.insert(0, str(_CACTUS_PYTHON_SRC))

from cactus import cactus_init, cactus_complete, cactus_destroy, cactus_reset  # type: ignore[import-untyped]

# ---------------------------------------------------------------------------
# Singleton model handle
# ---------------------------------------------------------------------------
_model: Any = None
_model_path: str | None = None


def _find_weights() -> str | None:
    for p in _WEIGHT_CANDIDATES:
        if p.is_dir():
            return str(p)
    return None


def get_model() -> Any:
    """Lazy-load and return the model handle.

    Raises RuntimeError if weights are not found.
    """
    global _model, _model_path

    if _model is not None:
        return _model

    weights = _find_weights()
    if weights is None:
        raise RuntimeError(
            f"Model weights for {MODEL_NAME} not found. "
            f"Searched: {[str(p) for p in _WEIGHT_CANDIDATES]}"
        )

    _model_path = weights
    _model = cactus_init(weights)
    atexit.register(_cleanup)
    return _model


def _cleanup() -> None:
    global _model
    if _model is not None:
        cactus_destroy(_model)
        _model = None


def reset_model() -> None:
    """Clear the KV cache between unrelated conversations."""
    if _model is not None:
        cactus_reset(_model)


def complete(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    max_tokens: int = 1024,
    force_tools: bool = False,
    confidence_threshold: float = 0.01,
) -> dict[str, Any]:
    """Run a completion via Cactus / LFM2.5-1.2B-Instruct.

    Returns:
        Parsed response dict with keys: success, response,
        function_calls, confidence, total_time_ms, etc.
    """
    model = get_model()

    cactus_tools = None
    if tools:
        cactus_tools = json.dumps([{"type": "function", "function": t} for t in tools])

    raw = cactus_complete(
        model,
        messages,
        tools=cactus_tools,
        force_tools=force_tools,
        max_tokens=max_tokens,
        confidence_threshold=confidence_threshold,
    )

    return _parse_response(raw)


def _parse_response(raw: str) -> dict[str, Any]:
    """Parse the JSON response from cactus_complete, ignoring trailing noise."""
    depth = 0
    end = -1
    for i, ch in enumerate(raw):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end == -1:
        return {
            "success": False,
            "error": "no_json_in_response",
            "response": raw,
            "function_calls": [],
            "confidence": 0.0,
            "total_time_ms": 0.0,
        }

    try:
        return json.loads(raw[:end])
    except json.JSONDecodeError:
        return {
            "success": False,
            "error": "json_parse_error",
            "response": raw[:end],
            "function_calls": [],
            "confidence": 0.0,
            "total_time_ms": 0.0,
        }
