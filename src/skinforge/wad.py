"""WAD tooling integration and per-user automatic installer."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

INSTALLER_URL = "https://raw.githubusercontent.com/LeagueToolkit/wadtools/main/scripts/install-wadtools.ps1"


class WadtoolsUnavailable(RuntimeError):
    """Raised when the external wadtools executable is not installed."""


def _user_install_path() -> Path | None:
    if platform.system() != "Windows":
        return None
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "wadtools" / "bin" / "wadtools.exe"
    profile = os.getenv("USERPROFILE")
    return Path(profile) / ".wadtools" / "bin" / "wadtools.exe" if profile else None


def locate_wadtools() -> str | None:
    found = shutil.which("wadtools") or shutil.which("wadtools.exe")
    if found:
        return found
    installed = _user_install_path()
    return str(installed) if installed and installed.is_file() else None


def install_wadtools() -> str:
    """Install the official latest Windows release for the current user.

    The official LeagueToolkit installer is downloaded from its fixed upstream URL
    and run without Explorer shell integration or administrator privileges.
    """
    if platform.system() != "Windows":
        raise WadtoolsUnavailable(
            "Automatic setup currently supports Windows x64. On other systems, install a "
            "matching binary from https://github.com/LeagueToolkit/wadtools/releases."
        )
    existing = locate_wadtools()
    if existing:
        return existing
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if not powershell:
        raise WadtoolsUnavailable("PowerShell was not found. Install PowerShell, then retry `skinforge setup`.")

    with tempfile.TemporaryDirectory(prefix="skinforge-wadtools-") as temp_dir:
        installer = Path(temp_dir) / "install-wadtools.ps1"
        request = urllib.request.Request(
            INSTALLER_URL,
            headers={"User-Agent": "SkinForge-AI-setup", "Accept": "text/plain"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                script = response.read(1_000_001)
            if len(script) > 1_000_000:
                raise WadtoolsUnavailable("Downloaded installer exceeded the 1 MB safety limit.")
            installer.write_bytes(script)
        except (OSError, TimeoutError) as exc:
            raise WadtoolsUnavailable(f"Could not download the official wadtools installer: {exc}") from exc

        result = subprocess.run(
            [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(installer), "-NoShellIntegration"],
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise WadtoolsUnavailable(f"wadtools installer failed (exit {result.returncode}): {detail[-2000:]}")

    executable = locate_wadtools()
    if not executable:
        raise WadtoolsUnavailable(
            "The installer completed but wadtools.exe could not be found. Open a new terminal and run `skinforge doctor`."
        )
    return executable


def doctor() -> dict[str, str | bool]:
    executable = locate_wadtools()
    if not executable:
        return {
            "available": False,
            "executable": "",
            "message": "wadtools is not installed. Run `skinforge setup` to install it automatically on Windows.",
        }
    try:
        result = subprocess.run(
            [executable, "--version"], capture_output=True, text=True, timeout=10, check=False
        )
        output = (result.stdout or result.stderr).strip()
        return {
            "available": result.returncode == 0,
            "executable": executable,
            "message": output or f"wadtools exited with code {result.returncode}",
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "executable": executable, "message": str(exc)}


def extract_wad(source: str | Path, output_dir: str | Path) -> subprocess.CompletedProcess[str]:
    """Extract a WAD to a new, separate output directory via wadtools."""
    executable = locate_wadtools()
    if not executable:
        raise WadtoolsUnavailable("Run `skinforge setup` to install wadtools, then retry.")
    src = Path(source).resolve()
    out = Path(output_dir).resolve()
    if not src.is_file():
        raise FileNotFoundError(src)
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"Refusing to extract into a non-empty directory: {out}")
    out.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        [executable, "extract", "-i", str(src), "-o", str(out)],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
