from pathlib import Path
import zipfile

import pytest

from skinforge.archive import ArchiveInspectionError, inspect_zip, validate_zip


def make_archive(path: Path, members: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    return path


def test_inspect_zip_reports_entries_and_hash(tmp_path: Path) -> None:
    archive = make_archive(tmp_path / "sample.fantome", {"META/info.json": b'{"name":"demo"}'})
    report = inspect_zip(archive)
    assert report["entry_count"] == 1
    assert report["entries"][0]["path"] == "META/info.json"
    assert len(report["sha256"]) == 64


def test_validate_zip_passes_for_normal_archive(tmp_path: Path) -> None:
    archive = make_archive(tmp_path / "good.fantome", {"data/file.bin": b"sample"})
    assert validate_zip(archive)["valid"] is True


def test_traversal_entry_is_reported(tmp_path: Path) -> None:
    archive = make_archive(tmp_path / "bad.fantome", {"../outside.txt": b"no"})
    report = validate_zip(archive)
    assert report["valid"] is False
    assert report["unsafe_paths"] == ["../outside.txt"]


def test_non_zip_is_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "not.zip"
    bad.write_bytes(b"not a zip")
    with pytest.raises(ArchiveInspectionError):
        inspect_zip(bad)
