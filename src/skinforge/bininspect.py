"""Conservative BIN inspection helpers.

BIN is a family of game-specific binary formats. This module only identifies
plain-text/JSON candidates; it does not claim to decode opaque Riot BIN data.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def inspect_bin(path: str | Path, sample_bytes: int = 256) -> dict[str, Any]:
    source = Path(path)
    data = source.read_bytes()
    result: dict[str, Any] = {
        "file": str(source),
        "size": len(data),
        "magic_hex": data[:16].hex(" "),
        "utf8_text_candidate": False,
        "json_candidate": False,
        "note": "Opaque BIN data requires a compatible dedicated parser.",
    }
    try:
        text = data.decode("utf-8-sig")
        printable = sum(ch.isprintable() or ch in "\\r\\n\\t" for ch in text)
        result["utf8_text_candidate"] = bool(text) and printable / max(len(text), 1) > 0.95
        if result["utf8_text_candidate"]:
            try:
                json.loads(text)
                result["json_candidate"] = True
                result["note"] = "Valid JSON text detected."
            except json.JSONDecodeError:
                result["note"] = "Readable UTF-8 text detected, but it is not JSON."
    except UnicodeDecodeError:
        pass
    result["sample_hex"] = data[:sample_bytes].hex(" ")
    # Show readable strings with byte offsets to make opaque BIN files inspectable
    # without pretending this is a complete Riot BIN semantic decoder.
    strings = []
    for match in re.finditer(rb"[\x20-\x7e]{4,}", data):
        strings.append({"offset": match.start(), "text": match.group().decode("ascii", errors="replace")})
        if len(strings) >= 500:
            break
    result["readable_strings"] = strings
    result["strings_truncated"] = len(strings) >= 500
    result["hex_preview_bytes"] = min(len(data), max(sample_bytes, 4096))
    result["hex_preview"] = data[:result["hex_preview_bytes"]].hex(" ")
    return result
