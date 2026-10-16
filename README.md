# SkinForge AI

AI-assisted League of Legends custom-skin research and packaging toolkit.

> Status: early development. This project does not promise universal compatibility or guaranteed in-game behavior. All edits are performed on copies and should be validated in a controlled local setup.

## Goals

- Inspect `.fantome` ZIP containers safely and report their contents.
- Inspect WAD assets through a supported external `wadtools` installation.
- Identify text/JSON BIN candidates without pretending to decode opaque proprietary formats.
- Produce reproducible reports, integrity checks, and safe workspace copies.
- Add an optional AI planning layer through an OpenAI-compatible API, with explicit human approval before file modifications.
- Build toward a desktop UI, asset-reference analysis, and verified export workflows.

## Initial scope

The first milestone is a reliable CLI and test suite for package inspection. Actual model/texture/animation authoring and game-client testing require specialized tools and must be added and validated incrementally.

## Requirements

- Python 3.11+
- Optional: `wadtools` from [LeagueToolkit/wadtools](https://github.com/LeagueToolkit/wadtools) for WAD operations.
- Optional: an OpenAI-compatible API endpoint for AI-assisted planning.

## Quick start

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e .
skinforge inspect path/to/skin.fantome
skinforge validate path/to/skin.fantome
skinforge doctor
```

## Safety

- Never run unknown binaries embedded in a skin package.
- Work on copies; preserve source packages and write outputs to a separate directory.
- Treat AI suggestions as proposals, not proof that an asset will work in-game.
- Do not use this project to bypass anti-cheat, tamper with accounts, or modify live game memory.

## Development

```bash
python -m pip install -e '.[dev]'
pytest
```

See `docs/ROADMAP.md` for planned milestones.
