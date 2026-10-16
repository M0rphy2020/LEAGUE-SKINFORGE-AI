from pathlib import Path

from skinforge.assets import index_assets


def test_asset_index_categorizes_files_and_hashes(tmp_path: Path) -> None:
    (tmp_path / "textures").mkdir()
    (tmp_path / "textures" / "champion.dds").write_bytes(b"texture")
    (tmp_path / "champion.bin").write_bytes(b"bin")

    report = index_assets(tmp_path)
    assert report["file_count"] == 2
    assert report["category_counts"] == {"bin": 1, "texture": 1}
    assert len(report["files"][0]["sha256"]) == 64


def test_asset_index_can_skip_hashing(tmp_path: Path) -> None:
    (tmp_path / "unknown.asset").write_bytes(b"data")
    report = index_assets(tmp_path, hash_files=False)
    assert report["files"][0]["category"] == "other"
    assert "sha256" not in report["files"][0]
