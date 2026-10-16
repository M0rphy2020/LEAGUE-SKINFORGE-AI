"""SkinForge command-line interface."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from skinforge import __version__
from skinforge.ai import AIConfigurationError, create_plan
from skinforge.archive import ArchiveInspectionError, extract_zip_safe, inspect_zip, validate_zip, write_report
from skinforge.bininspect import inspect_bin
from skinforge.wad import doctor as wadtools_doctor
from skinforge.wad import extract_wad, install_wadtools


def _print_json(value: object) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(prog="skinforge", description="SkinForge AI asset toolkit")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    inspect_cmd = commands.add_parser("inspect", help="Inspect a ZIP-based .fantome container")
    inspect_cmd.add_argument("file", type=Path)
    inspect_cmd.add_argument("--report", type=Path, help="Write JSON report to this path")

    validate_cmd = commands.add_parser("validate", help="Validate archive paths and CRCs")
    validate_cmd.add_argument("file", type=Path)
    validate_cmd.add_argument("--report", type=Path)

    extract_archive_cmd = commands.add_parser("archive-extract", help="Safely extract a validated ZIP/Fantome package")
    extract_archive_cmd.add_argument("file", type=Path)
    extract_archive_cmd.add_argument("--output", type=Path, required=True)

    bin_cmd = commands.add_parser("bin-inspect", help="Identify readable BIN candidates")
    bin_cmd.add_argument("file", type=Path)

    extract_cmd = commands.add_parser("wad-extract", help="Extract WAD using wadtools")
    extract_cmd.add_argument("file", type=Path)
    extract_cmd.add_argument("--output", type=Path, required=True)

    commands.add_parser("doctor", help="Check optional tool availability")
    commands.add_parser("setup", help="Install the official wadtools dependency on Windows")

    plan_cmd = commands.add_parser("ai-plan", help="Ask an AI endpoint for an investigation plan")
    plan_cmd.add_argument("file", type=Path)
    plan_cmd.add_argument("--request", required=True, help="Describe the issue or desired custom skin")

    args = parser.parse_args()
    try:
        if args.command == "inspect":
            report = inspect_zip(args.file)
            _print_json(report)
            if args.report:
                print(f"Report written to {write_report(report, args.report)}")
        elif args.command == "validate":
            report = validate_zip(args.file)
            _print_json(report)
            if args.report:
                write_report(report, args.report)
            if not report["valid"]:
                raise SystemExit(2)
        elif args.command == "archive-extract":
            _print_json(extract_zip_safe(args.file, args.output))
        elif args.command == "bin-inspect":
            _print_json(inspect_bin(args.file))
        elif args.command == "wad-extract":
            result = extract_wad(args.file, args.output)
            print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            if result.returncode:
                raise SystemExit(result.returncode)
        elif args.command == "doctor":
            _print_json({
                "python": sys.version.split()[0],
                "wadtools": wadtools_doctor(),
                "ai_configured": bool(os.getenv("SKINFORGE_AI_BASE_URL") and os.getenv("SKINFORGE_AI_MODEL")),
                "ai_note": "AI plans investigations only; it does not yet author complete working skins.",
            })
        elif args.command == "setup":
            executable = install_wadtools()
            print(f"wadtools is ready: {executable}")
            print("Next: run `skinforge doctor` to verify the setup.")
        elif args.command == "ai-plan":
            report = inspect_zip(args.file)
            print(create_plan(args.request, report))
    except (OSError, ArchiveInspectionError, AIConfigurationError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
