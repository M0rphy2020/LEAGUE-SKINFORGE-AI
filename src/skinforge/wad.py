"""Optional adapter for LeagueToolkit wadtools; no bundled binary execution."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class WadtoolsUnavailable(RuntimeError):
    """Raised when the external wadtools executable is not installed."""


def locate_wadtools() -> str | None:
    return shutil.which("wadtools") or shutil.which("wadtools.exe")


def doctor() -> dict[str, str | bool]:
    executable = locate_wadtools()
    if not executable:
        return {
            "available": False,
            "executable": "",
            "message": "wadtools was not found on PATH. Install it from LeagueToolkit/wadtools.",
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
        raise WadtoolsUnavailable(
            "Install LeagueToolkit/wadtools and ensure its executable is on PATH."
        )
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
