"""Local-only inference module via Cactus / LFM2.5-1.2B-Instruct.

All inference runs on-device. No cloud fallback, no mocks.
"""

from __future__ import annotations

import time
from typing import Any

from inference import MODEL_NAME, complete, reset_model


# In-memory routing history for the dashboard
routing_history: list[dict[str, Any]] = []


def generate(
    messages: list[dict[str, Any]],
    max_tokens: int = 1024,
) -> dict[str, Any]:
    """Run text inference on-device via LFM2.5-1.2B-Instruct.

    Returns dict with: response, source, confidence, total_time, model.
    """
    reset_model()

    system_msg = {"role": "system", "content": (
        "You are a forensic analyst using the Sheffield STIM Matrix. "
        "Analyse communications for: "
        "1) Language-based vulnerability (grooming, flattery, false promises), "
        "2) Third-party control (instructions, demands, restricting movement), "
        "3) Psychological isolation (cutting off support networks, secrecy), "
        "4) Financial coercion (debt traps, withholding pay, threats over money). "
        "Quote the exact concerning text and explain which STIM indicator it triggers."
    )}
    full_messages = [system_msg] + messages

    result = complete(
        messages=full_messages,
        max_tokens=max_tokens,
    )

    return {
        "response": result.get("response", ""),
        "source": "local",
        "confidence": result.get("confidence", 0.0),
        "total_time": result.get("total_time_ms", 0.0) / 1000.0,
        "model": MODEL_NAME,
    }


# Keep generate_hybrid as the public API name for backward compat with api.py / analyzer.py
def generate_hybrid(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,  # ignored — text-only model
    cloud_consent: bool = False,  # ignored — local only
) -> dict[str, Any]:
    """Run local-only inference. Extra params kept for API compatibility."""
    start = time.time()

    result = generate(messages)

    # Extract prompt for history
    last_user_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    routing_history.append({
        "timestamp": time.time(),
        "prompt": last_user_msg[:100],
        "source": "local",
        "confidence": result.get("confidence", 0.0),
        "latency": result.get("total_time", time.time() - start),
        "response": (result.get("response") or "")[:200],
        "model": MODEL_NAME,
    })

    return result
