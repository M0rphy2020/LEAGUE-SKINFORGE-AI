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
    """Load supported settings from the user config and project .env, preserving process env."""
    env_files = (Path.home() / ".skinforge" / ".env", Path.cwd() / ".env")
    allowed = {"SKINFORGE_AI_BASE_URL", "SKINFORGE_AI_MODEL", "SKINFORGE_AI_API_KEY"}
    for env_file in env_files:
        if not env_file.is_file():
            continue
        try:
            lines = env_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
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
                    "You are SkinForge AI, a specialist assistant for League of Legends custom-skin "
                    "asset development. You are not a general chatbot. Turn the user's visual goal into "
                    "a practical, reversible work order grounded only in supplied package metadata and "
                    "asset inventory. Respond with these sections: Goal and visual specification; "
                    "Candidate assets with exact paths and evidence; Proposed changes by asset type; "
                    "Tools or format support still required; Validation checklist; Risks and unknowns. "
                    "Distinguish confirmed facts from hypotheses. Never invent a file, decoded BIN field, "
                    "model capability, or successful test. If evidence is insufficient, ask for the exact "
                    "missing input instead of guessing. Prefer a non-destructive workflow with backups and "
                    "a separate output folder. Never propose anti-cheat bypass, live memory manipulation, "
                    "credential access, or destructive actions. The separate constrained edit workflow can apply user-confirmed raster tint recipes only; this planner itself does not edit assets, compile a skin, or verify in-game behavior."
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


def create_edit_recipe(request: str, inventory: dict[str, Any]) -> str:
    """Ask the configured model for a strict, executable recipe using supported texture operations."""
    _load_local_env()
    base_url = os.getenv("SKINFORGE_AI_BASE_URL", "").rstrip("/")
    api_key = os.getenv("SKINFORGE_AI_API_KEY", "")
    model = os.getenv("SKINFORGE_AI_MODEL", "")
    if not base_url or not model:
        raise AIConfigurationError(
            "Configure SKINFORGE_AI_BASE_URL and SKINFORGE_AI_MODEL in AI Settings first."
        )
    payload = {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are SkinForge AI, a League of Legends custom-skin texture assistant. "
                    "Return JSON only, exactly shaped as {\"summary\":\"...\",\"edits\":["
                    "{\"operation\":\"tint_texture\",\"source\":\"relative/path.png\","
                    "\"color\":\"#RRGGBB\",\"strength\":0.0}]}. You may only propose "
                    "tint_texture operations on raster image files explicitly listed in the supplied "
                    "inventory. source must exactly match a listed relative path. Use at most 20 edits. "
                    "Strength must be 0..1. If no appropriate supported texture exists, return an empty "
                    "edits list and explain why in summary. Never invent paths. Do not propose commands, "
                    "code, model edits, DDS/TEX edits, BIN edits, game memory changes, or anti-cheat bypass."
                ),
            },
            {
                "role": "user",
                "content": "Visual request:\n" + request + "\n\nAvailable asset inventory:\n"
                + json.dumps(inventory, ensure_ascii=False)[:40000],
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
        raise RuntimeError(f"AI edit recipe request failed: {exc}") from exc
