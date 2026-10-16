# SkinForge AI

AI-assisted League of Legends custom-skin inspection and development toolkit.

> **Status: early development.** The current version inspects and validates `.fantome` ZIP containers, can extract `.wad.client` archives through LeagueToolkit `wadtools`, and asks an optional AI endpoint for an investigation plan. It does not yet generate complete working 3D skins or guarantee in-game behavior.

## Visual desktop app

After installing, launch the graphical workspace with:

```powershell
skinforge-gui
```

The desktop workspace provides package browsing, validation, guarded extraction, an asset inventory table, and an AI work-plan panel. It uses Python's built-in Tkinter UI, so it does not require a large GUI framework. The current AI panel proposes a skin-development plan; it does not yet modify 3D models or textures automatically.

## Quick install on Windows

Requirements: Python 3.11+ and Windows PowerShell. From the repository folder, run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
```

The bootstrap installs SkinForge into the current Python environment, installs the official `wadtools` dependency for your Windows user through the upstream installer, and runs a health check. It does not require administrator privileges and skips Explorer context-menu integration. `wadtools` is installed from the official LeagueToolkit repository: https://github.com/LeagueToolkit/wadtools.

If you already installed SkinForge, run `skinforge setup` to install `wadtools`, or `skinforge doctor` to check dependencies.

## Basic commands

```powershell
skinforge inspect "C:\path\to\skin.fantome"
skinforge validate "C:\path\to\skin.fantome"
skinforge bin-inspect "C:\path\to\asset.bin"
skinforge wad-extract "C:\path\to\Champion.wad.client" --output .\extracted
skinforge doctor
```

`inspect` reports package contents and hashes. `validate` checks archive paths and CRCs. `archive-extract` validates the ZIP/Fantome archive before extracting it, blocks traversal and symlink entries, and refuses a non-empty destination. `wad-extract` delegates WAD extraction to LeagueToolkit `wadtools` and also refuses a non-empty destination. `asset-index` categorizes extracted files (textures, models, materials, animation, audio, BIN, WAD and other), reports sizes and can compute SHA-256 hashes.

## AI: what works today?

SkinForge AI is a domain-focused orchestration layer for custom-skin development, not a newly trained foundation model. It uses a configurable compatible model and supplies League asset context, workflow constraints and validation requirements. A truly autonomous asset-editing agent still needs robust BIN/model/texture adapters and reversible build tools; those are not present yet.

The AI layer sends a package report and your request to an OpenAI-compatible chat-completions endpoint. It can produce an investigation plan and separate confirmed observations from hypotheses. It currently **does not** directly edit model/texture/animation assets, compile a custom skin, or verify the result in-game.

To configure it, copy `.env.example` to `.env` and set your provider's base URL, model name, and API key if required. Keep `.env` private and never commit credentials. Then run:

```powershell
skinforge ai-plan "C:\path\to\skin.fantome" --request "Describe the issue or custom-skin goal"
```

The project loads only the three documented `SKINFORGE_AI_*` settings from `.env`; existing process environment values take precedence. AI output is advisory.

## Current capabilities and next milestones

- Safe archive inspection, SHA-256 reporting, CRC/path validation, and guarded ZIP/Fantome extraction.
- `wadtools` integration for `.wad` and `.wad.client` extraction.
- Deterministic asset inventory with file-type categories and optional SHA-256 hashing.
- Conservative BIN inspection for readable text/JSON candidates; opaque BIN data is not falsely claimed to be decoded.
- Optional AI-assisted investigation plans.
- Visual desktop workspace with package inspection, guarded extraction, asset inventory and an AI planning panel.
- Planned: deeper BIN parsing, cross-asset references, reversible asset edits, texture/model workflows, previewing, and validated package building.

## Development

```powershell
python -m pip install -e ".[dev]"
pytest
ruff check src tests
```

## Safety

- Never run unknown binaries embedded in a skin package.
- Preserve originals and work on copies.
- Treat AI suggestions as proposals, not proof of compatibility.
- The project is not intended for anti-cheat bypass, account tampering, or live game-memory modification.

See `docs/ROADMAP.md` for planned milestones.
