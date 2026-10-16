"""Safe, read-only inspection of ZIP-based skin containers such as .fantome."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

MAX_ENTRIES = 100_000
MAX_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024
MAX_RATIO = 2_000


class ArchiveInspectionError(ValueError):
    """Raised when an archive is malformed or exceeds safety limits."""


def _safe_member_name(name: str) -> bool:
    path = PurePosixPath(name.replace("\\", "/"))
    return not path.is_absolute() and ".." not in path.parts and not (path.parts and ":" in path.parts[0])


def inspect_zip(path: str | Path) -> dict[str, Any]:
    """Inspect a ZIP container without extracting its contents."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)

    try:
        with zipfile.ZipFile(source) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_ENTRIES:
                raise ArchiveInspectionError(f"Archive contains too many entries ({len(entries)}).")
            total_size = sum(item.file_size for item in entries)
            if total_size > MAX_UNCOMPRESSED_BYTES:
                raise ArchiveInspectionError("Archive exceeds the 2 GiB uncompressed safety limit.")

            results = []
            unsafe = []
            for item in entries:
                safe = _safe_member_name(item.filename)
                if not safe:
                    unsafe.append(item.filename)
                ratio = item.file_size / max(item.compress_size, 1)
                results.append({
                    "path": item.filename,
                    "size": item.file_size,
                    "compressed_size": item.compress_size,
                    "compression_ratio": round(ratio, 2),
                    "is_dir": item.is_dir(),
                    "safe_path": safe,
                })

            return {
                "file": str(source),
                "container_type": "zip/fantome-compatible" if source.suffix.lower() == ".fantome" else "zip",
                "size": source.stat().st_size,
                "sha256": digest.hexdigest(),
                "entry_count": len(entries),
                "uncompressed_size": total_size,
                "unsafe_paths": unsafe,
                "suspicious_compression_entries": [
                    item["path"] for item in results
                    if item["compression_ratio"] > MAX_RATIO and item["size"] > 10_000_000
                ],
                "entries": results,
            }
    except zipfile.BadZipFile as exc:
        raise ArchiveInspectionError(f"Not a valid ZIP container: {source.name}") from exc


def validate_zip(path: str | Path) -> dict[str, Any]:
    """Run CRC checks and structural safety checks without extracting files."""
    report = inspect_zip(path)
    issues: list[str] = []
    if report["unsafe_paths"]:
        issues.append("Archive contains path-traversal or absolute-path entries.")
    if report["suspicious_compression_entries"]:
        issues.append("Archive contains entries with an unusually high compression ratio.")
    try:
        with zipfile.ZipFile(path) as archive:
            bad_member = archive.testzip()
            if bad_member:
                issues.append(f"CRC failure in entry: {bad_member}")
    except (OSError, zipfile.BadZipFile) as exc:
        issues.append(f"Archive read failed: {exc}")
    report["valid"] = not issues
    report["issues"] = issues
    return report



def extract_zip_safe(path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    """Extract a ZIP/Fantome archive without allowing traversal or symlink entries."""
    import shutil

    source = Path(path)
    target = Path(output_dir).resolve()
    report = validate_zip(source)
    if not report["valid"]:
        raise ArchiveInspectionError(
            "Archive failed validation; refusing extraction: " + "; ".join(report["issues"])
        )
    if target.exists() and any(target.iterdir()):
        raise FileExistsError(f"Refusing to extract into a non-empty directory: {target}")

    target.mkdir(parents=True, exist_ok=True)
    extracted: list[str] = []
    try:
        with zipfile.ZipFile(source) as archive:
            for item in archive.infolist():
                if not _safe_member_name(item.filename):
                    raise ArchiveInspectionError(f"Unsafe archive path: {item.filename}")
                file_type = (item.external_attr >> 16) & 0o170000
                if file_type == 0o120000:
                    raise ArchiveInspectionError(f"Symbolic links are not supported: {item.filename}")
                destination = (target / item.filename).resolve()
                if destination != target and target not in destination.parents:
                    raise ArchiveInspectionError(f"Archive path escapes destination: {item.filename}")
                if item.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(item, "r") as src, destination.open("wb") as dst:
                    while chunk := src.read(1024 * 1024):
                        dst.write(chunk)
                extracted.append(item.filename)
    except Exception:
        shutil.rmtree(target, ignore_errors=True)
        raise
    return {
        "source": str(source),
        "output": str(target),
        "extracted_count": len(extracted),
        "files": extracted,
    }


def write_report(report: dict[str, Any], output: str | Path) -> Path:
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return target
