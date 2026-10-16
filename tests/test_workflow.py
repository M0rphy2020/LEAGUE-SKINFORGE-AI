from __future__ import annotations

import json
from pathlib import Path

import pytest

from skinforge.workflow import EditWorkflowError, apply_edit_recipe, parse_edit_recipe


def test_parse_edit_recipe_rejects_path_traversal() -> None:
    with pytest.raises(EditWorkflowError, match="unsafe source path"):
        parse_edit_recipe(json.dumps({"edits": [{"operation": "tint_texture", "source": "../secret.png", "color": "#ffffff"}]}))


def test_parse_edit_recipe_rejects_unknown_operations() -> None:
    with pytest.raises(EditWorkflowError, match="only the supported"):
        parse_edit_recipe(json.dumps({"edits": [{"operation": "run_command"}]}))


def test_apply_recipe_requires_separate_empty_output(tmp_path: Path) -> None:
    root = tmp_path / "assets"
    root.mkdir()
    output = root / "generated"
    with pytest.raises(EditWorkflowError, match="separate"):
        apply_edit_recipe({"edits": []}, root, output)
