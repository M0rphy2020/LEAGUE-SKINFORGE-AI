"""Release-based update checks and safe wheel installation for SkinForge AI."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from skinforge import __version__

REPOSITORY = "M0rphy2020/LEAGUE-SKINFORGE-AI"
RELEASES_API = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPOSITORY}/releases/latest"
_USER_AGENT = "SkinForge-AI-Updater"


class UpdateError(RuntimeError):
    """Raised when a release cannot be checked or installed safely."""


def _github_token() -> str:
    token = os.getenv("SKINFORGE_GITHUB_TOKEN", "").strip()
    if token:
        return token
    gh = shutil.which("gh")
    if gh:
        try:
            result = subprocess.run(
                [gh, "auth", "token"],
                check=True,
                capture_output=True,
                text=True,
                timeout=8,
            )
            return result.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
    return ""


def _request(url: str, token: str, *, accept: str = "application/vnd.github+json") -> bytes:
    headers = {"Accept": accept, "User-Agent": _USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise UpdateError(
            "Could not reach GitHub Releases. Check your internet connection and repository access."
        ) from exc


def _version_tuple(value: str) -> tuple[int, ...]:
    match = re.fullmatch(r"v?(\d+(?:\.\d+)*)(?:[-+][0-9A-Za-z.-]+)?", value.strip())
    if not match:
        raise UpdateError(f"Unsupported release version: {value}")
    return tuple(int(part) for part in match.group(1).split("."))


def check_for_update() -> dict[str, Any]:
    """Return latest release metadata and whether it is newer than the installed version."""
    token = _github_token()
    try:
        release = json.loads(_request(RELEASES_API, token).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateError("GitHub returned invalid release metadata.") from exc

    if release.get("draft") or release.get("prerelease"):
        raise UpdateError("The latest GitHub release is not a stable release.")
    tag = str(release.get("tag_name", ""))
    latest = tag.removeprefix("v")
    if not latest:
        raise UpdateError("GitHub release metadata does not include a version tag.")
    assets = [
        asset for asset in release.get("assets", [])
        if str(asset.get("name", "")).lower().endswith(".whl")
        and "skinforge" in str(asset.get("name", "")).lower()
    ]
    return {
        "current_version": __version__,
        "latest_version": latest,
        "update_available": _version_tuple(latest) > _version_tuple(__version__),
        "release_url": release.get("html_url") or RELEASES_PAGE,
        "wheel": assets[0] if assets else None,
        "token_available": bool(token),
    }


def install_latest_update(release_info: dict[str, Any]) -> str:
    """Download the wheel attached to a checked release, verify its digest if present, install it."""
    if not release_info.get("update_available"):
        raise UpdateError("SkinForge AI is already up to date.")
    wheel = release_info.get("wheel")
    if not isinstance(wheel, dict):
        raise UpdateError(
            "This release has no SkinForge wheel attached yet. Open the release page for details."
        )
    name = str(wheel.get("name", ""))
    if Path(name).name != name or not name.lower().endswith(".whl"):
        raise UpdateError("The release contains an invalid wheel filename.")
    url = str(wheel.get("browser_download_url", ""))
    if not url.startswith(f"https://github.com/{REPOSITORY}/releases/download/"):
        raise UpdateError("The wheel download URL is not an official SkinForge release asset.")

    token = _github_token()
    data = _request(url, token, accept="application/octet-stream")
    digest = hashlib.sha256(data).hexdigest()
    expected = str(wheel.get("digest") or "")
    if expected.startswith("sha256:") and digest.lower() != expected[7:].lower():
        raise UpdateError("The downloaded update failed its SHA-256 integrity check.")

    with tempfile.TemporaryDirectory(prefix="skinforge-update-") as temp_dir:
        wheel_path = Path(temp_dir) / name
        wheel_path.write_bytes(data)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "--no-deps", str(wheel_path)],
                capture_output=True,
                text=True,
                timeout=180,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise UpdateError(f"Could not run pip to install the update: {exc}") from exc
        if result.returncode:
            details = (result.stderr or result.stdout or "pip returned an error").strip()
            raise UpdateError(f"Update installation failed: {details[-1800:]}")
    return str(release_info.get("latest_version", "the latest version"))
