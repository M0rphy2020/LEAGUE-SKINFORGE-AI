from __future__ import annotations

from pathlib import Path

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image

from skinforge.texture import TextureEditError, tint_texture


def test_tint_creates_new_texture_and_preserves_alpha(tmp_path: Path) -> None:
    source = tmp_path / "input.png"
    output = tmp_path / "output.png"
    image = Image.new("RGBA", (2, 1))
    image.putdata([(255, 255, 255, 0), (20, 40, 60, 128)])
    image.save(source)

    report = tint_texture(source, output, "#ff0000", strength=0.5)

    with Image.open(output) as result:
        assert list(result.getchannel("A").getdata()) == [0, 128]
        assert result.getpixel((1, 0)) != (20, 40, 60, 128)
    assert source.read_bytes() != output.read_bytes()
    assert report["alpha_preserved"] is True
    assert len(report["source_sha256"]) == 64


def test_tint_refuses_overwrite_and_same_path(tmp_path: Path) -> None:
    source = tmp_path / "input.png"
    Image.new("RGBA", (1, 1), (1, 2, 3, 255)).save(source)
    with pytest.raises(TextureEditError, match="must differ"):
        tint_texture(source, source, "#ff0000")
    output = tmp_path / "existing.png"
    output.write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        tint_texture(source, output, "#ff0000")


def test_tint_rejects_game_specific_formats(tmp_path: Path) -> None:
    source = tmp_path / "input.dds"
    source.write_bytes(b"not a dds")
    with pytest.raises(TextureEditError, match="DDS/TEX"):
        tint_texture(source, tmp_path / "output.png", "#ff0000")
