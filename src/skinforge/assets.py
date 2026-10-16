"""Build a deterministic inventory of extracted skin assets."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

CATEGORIES = {
    "texture": {".dds", ".tex", ".png", ".jpg", ".jpeg", ".tga", ".bmp", ".webp"},
    "model": {".skn", ".skl", ".obj", ".fbx", ".gltf", ".glb"},
    "material": {".material", ".mat"},
    "animation": {".anm", ".anim"},
    "audio": {".wem", ".bnk", ".ogg", ".wav", ".mp3"},
    "bin": {".bin"},
    "wad": {".wad", ".client"},
}


def _category(path: Path) -> str:
    suffix = path.suffix.lower()
    for category, extensions in CATEGORIES.items():
        if suffix in extensions:
            return category
    return "other"


def index_assets(root: str | Path, *, hash_files: bool = True) -> dict[str, Any]:
    """Inventory files under a directory without modifying them."""
    base = Path(root).resolve()
    if not base.is_dir():
        raise NotADirectoryError(base)

    files: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(base).as_posix()
        category = _category(path)
        counts[category] = counts.get(category, 0) + 1
        item: dict[str, Any] = {
            "path": relative,
            "size": path.stat().st_size,
            "extension": path.suffix.lower(),
            "category": category,
        }
        if hash_files:
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            item["sha256"] = digest.hexdigest()
        files.append(item)

    return {
        "root": str(base),
        "file_count": len(files),
        "category_counts": dict(sorted(counts.items())),
        "files": files,
    }
