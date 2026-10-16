"""Optional AI planning via an OpenAI-compatible chat-completions endpoint.

The AI proposes an investigation plan only. It cannot execute commands or write files.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


class AIConfigurationError(RuntimeError):
    """Raised when the AI endpoint is not configured."""


def _load_local_env() -> None:
    """Load simple KEY=VALUE settings from .env without overriding process env."""
    env_file = Path.cwd() / ".env"
    if not env_file.is_file():
        return
    allowed = {"SKINFORGE_AI_BASE_URL", "SKINFORGE_AI_MODEL", "SKINFORGE_AI_API_KEY"}
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key in allowed and key not in os.environ and value:
            os.environ[key] = value


def create_plan(request: str, report: dict[str, Any]) -> str:
    _load_local_env()
    base_url = os.getenv("SKINFORGE_AI_BASE_URL", "").rstrip("/")
    api_key = os.getenv("SKINFORGE_AI_API_KEY", "")
    model = os.getenv("SKINFORGE_AI_MODEL", "")
    if not base_url or not model:
        raise AIConfigurationError(
            "Configure SKINFORGE_AI_BASE_URL and SKINFORGE_AI_MODEL in a local .env file. "
            "Set SKINFORGE_AI_API_KEY if your provider requires authentication. "
            "See .env.example."
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
                    "Separate confirmed facts from hypotheses. This version plans work only: "
                    "it cannot directly edit assets, compile a skin, or verify in-game behavior."
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
