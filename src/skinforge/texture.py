"""Non-destructive raster texture editing for custom-skin workflows.

Only common raster formats are supported here. Game-specific DDS/TEX containers,
3D models, animation, and BIN data require dedicated adapters and are never guessed.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

SUPPORTED_INPUTS = {".png", ".jpg", ".jpeg", ".tga", ".bmp", ".webp"}
SUPPORTED_OUTPUTS = {".png", ".tga", ".bmp", ".webp"}


class TextureEditError(ValueError):
    """Raised when a texture cannot be safely transformed."""


def tint_texture(
    source: str | Path,
    destination: str | Path,
    color: str,
    *,
    strength: float = 0.35,
    brightness: float = 1.0,
    contrast: float = 1.0,
    saturation: float = 1.0,
) -> dict[str, Any]:
    """Blend a chosen RGB tint into a raster texture, preserving alpha, to a new file."""
    try:
        from PIL import Image, ImageColor, ImageEnhance
    except ImportError as exc:
        raise TextureEditError(
            "Texture editing needs Pillow. Install it with: python -m pip install 'skinforge-ai[texture]'"
        ) from exc

    src = Path(source).expanduser().resolve()
    dst = Path(destination).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(src)
    if src.suffix.lower() not in SUPPORTED_INPUTS:
        raise TextureEditError(
            f"Unsupported source format {src.suffix or '(no extension)'}. "
            "Supported inputs: PNG, JPG, TGA, BMP, WEBP. DDS/TEX need a dedicated decoder."
        )
    if dst.suffix.lower() not in SUPPORTED_OUTPUTS:
        raise TextureEditError("Output must be PNG, TGA, BMP, or WEBP.")
    if src == dst:
        raise TextureEditError("Source and destination must differ; originals are never overwritten.")
    if dst.exists():
        raise FileExistsError(f"Output already exists: {dst}")
    if not 0.0 <= strength <= 1.0:
        raise TextureEditError("Strength must be between 0.0 and 1.0.")
    for name, value in (("brightness", brightness), ("contrast", contrast), ("saturation", saturation)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0.0 <= value <= 2.0:
            raise TextureEditError(f"{name.capitalize()} must be between 0.0 and 2.0.")
    try:
        rgb = ImageColor.getrgb(color)
    except (ValueError, TypeError) as exc:
        raise TextureEditError(f"Invalid color {color!r}; use a value such as #8b5cf6.") from exc

    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(src) as original:
            image = original.convert("RGBA")
            alpha = image.getchannel("A")
            overlay = Image.new("RGBA", image.size, (*rgb, 255))
            # Blend in RGB only, then restore the original alpha exactly.
            base_rgb = image.convert("RGB")
            tinted_rgb = Image.blend(base_rgb, overlay.convert("RGB"), strength)
            tinted_rgb = ImageEnhance.Brightness(tinted_rgb).enhance(brightness)
            tinted_rgb = ImageEnhance.Contrast(tinted_rgb).enhance(contrast)
            tinted_rgb = ImageEnhance.Color(tinted_rgb).enhance(saturation)
            tinted = tinted_rgb.convert("RGBA")
            tinted.putalpha(alpha)
            if dst.suffix.lower() == ".jpg" or dst.suffix.lower() == ".jpeg":
                raise TextureEditError("JPEG output is intentionally disabled to preserve transparency.")
            tinted.save(dst)
    except OSError as exc:
        raise TextureEditError(f"Could not read or write texture: {exc}") from exc

    def sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    return {
        "source": str(src),
        "output": str(dst),
        "size": list(tinted.size),
        "tint": color,
        "strength": strength,
        "brightness": brightness,
        "contrast": contrast,
        "saturation": saturation,
        "alpha_preserved": True,
        "source_sha256": sha256(src),
        "output_sha256": sha256(dst),
    }
