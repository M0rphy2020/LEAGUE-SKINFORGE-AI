"""Optional AI planning via an OpenAI-compatible chat-completions endpoint.

The AI proposes a plan only. It cannot execute commands or write files.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


class AIConfigurationError(RuntimeError):
    pass


def create_plan(request: str, report: dict[str, Any]) -> str:
    base_url = os.getenv("SKINFORGE_AI_BASE_URL", "").rstrip("/")
    api_key = os.getenv("SKINFORGE_AI_API_KEY", "")
    model = os.getenv("SKINFORGE_AI_MODEL", "")
    if not base_url or not model:
        raise AIConfigurationError(
            "Set SKINFORGE_AI_BASE_URL and SKINFORGE_AI_MODEL. "
            "Set SKINFORGE_AI_API_KEY if your provider requires authentication."
        )
    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are SkinForge AI, a cautious game-asset analysis assistant. "
                    "Return a practical investigation plan based only on supplied metadata. "
                    "Do not claim assets work without tests. Never propose anti-cheat bypass, "
                    "live memory manipulation, credential access, or destructive actions. "
                    "Separate confirmed facts from hypotheses."
                ),
            },
            {
                "role": "user",
                "content": "User request:\n" + request + "\n\nPackage report:\n"
                + json.dumps(report, ensure_ascii=False)[:40_000],
            },
        ],
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(base_url + "/chat/completions", data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            result = json.loads(response.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"]
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"AI request failed: {exc}") from exc
