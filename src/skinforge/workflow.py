"""Validated, non-destructive execution of AI-proposed texture edits."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from skinforge.texture import SUPPORTED_INPUTS, tint_texture


class EditWorkflowError(ValueError):
    """Raised when an AI edit recipe is invalid or unsafe."""


def parse_edit_recipe(raw: str) -> dict[str, Any]:
    """Parse strict JSON returned by the AI provider; reject markdown and unknown operations."""
    try:
        recipe = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise EditWorkflowError("AI did not return valid JSON. Ask it to regenerate the edit recipe.") from exc
    if not isinstance(recipe, dict) or not isinstance(recipe.get("edits"), list):
        raise EditWorkflowError("Recipe must be a JSON object with an 'edits' list.")
    if len(recipe["edits"]) > 20:
        raise EditWorkflowError("A single AI recipe may contain at most 20 edits.")
    for index, edit in enumerate(recipe["edits"]):
        if not isinstance(edit, dict) or edit.get("operation") != "tint_texture":
            raise EditWorkflowError(f"Edit {index + 1}: only the supported tint_texture operation is allowed.")
        source = edit.get("source")
        color = edit.get("color")
        strength = edit.get("strength", 0.35)
        if not isinstance(source, str) or not source or Path(source).is_absolute():
            raise EditWorkflowError(f"Edit {index + 1}: source must be a relative asset path.")
        if ".." in Path(source).parts or "\\" in source or "\x00" in source:
            raise EditWorkflowError(f"Edit {index + 1}: unsafe source path.")
        if Path(source).suffix.lower() not in SUPPORTED_INPUTS:
            raise EditWorkflowError(f"Edit {index + 1}: source is not a supported raster texture.")
        if not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise EditWorkflowError(f"Edit {index + 1}: color must be a hex RGB value such as #8b5cf6.")
        if isinstance(strength, bool) or not isinstance(strength, (int, float)) or not 0 <= strength <= 1:
            raise EditWorkflowError(f"Edit {index + 1}: strength must be between 0 and 1.")
        for field in ("brightness", "contrast", "saturation"):
            value = edit.get(field, 1.0)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 2:
                raise EditWorkflowError(f"Edit {index + 1}: {field} must be between 0 and 2.")
    return recipe


def apply_edit_recipe(
    recipe: dict[str, Any], asset_root: str | Path, output_root: str | Path
) -> dict[str, Any]:
    """Apply validated edits to a separate output tree, never overwriting input assets."""
    root = Path(asset_root).expanduser().resolve()
    output = Path(output_root).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Asset folder does not exist: {root}")
    if output == root or root in output.parents:
        raise EditWorkflowError("Output folder must be separate from the input asset folder.")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Output folder must be empty to avoid overwriting files: {output}")
    planned: list[tuple[dict[str, Any], Path, Path]] = []
    seen_outputs: set[Path] = set()
    for edit in recipe["edits"]:
        source = (root / edit["source"]).resolve()
        if root not in source.parents or not source.is_file():
            raise EditWorkflowError(f"Source asset is missing or outside the selected folder: {edit['source']}")
        relative = source.relative_to(root)
        destination = output / relative.with_suffix(".png")
        if destination in seen_outputs:
            raise EditWorkflowError(f"Multiple edits target the same output: {destination}")
        if destination.exists():
            raise FileExistsError(f"Refusing to overwrite output: {destination}")
        seen_outputs.add(destination)
        planned.append((edit, source, destination))

    # Validate the entire plan before writing any output, avoiding avoidable partial edits.
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for edit, source, destination in planned:
        destination.parent.mkdir(parents=True, exist_ok=True)
        results.append(tint_texture(\n            source, destination, edit["color"], strength=float(edit.get("strength", 0.35)),\n            brightness=float(edit.get("brightness", 1.0)),\n            contrast=float(edit.get("contrast", 1.0)),\n            saturation=float(edit.get("saturation", 1.0)),\n        ))
    report = {"operation_count": len(results), "input_root": str(root), "output_root": str(output), "results": results}
    (output / "skinforge-edit-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
