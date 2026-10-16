# Roadmap

## Milestone 0: Safe foundation
- [x] Project packaging and CLI entry point
- [x] Read-only ZIP/Fantome inventory
- [x] ZIP CRC and path-safety validation
- [x] Conservative BIN candidate inspection
- [x] Optional wadtools adapter
- [x] Optional AI planning endpoint
- [ ] Run CI and validate on Windows

## Milestone 1: Real asset understanding
- [ ] Define a plugin interface for supported WAD/BIN/texture/model tools
- [ ] Add structured manifests for skin packages and asset references
- [ ] Build cross-file reference reports for particles, animations, sounds, and spell resources
- [ ] Add golden test fixtures from legally usable sample assets
- [ ] Record game patch and tool versions in every report

## Milestone 2: Safe editing
- [ ] Workspace snapshots and reversible change sets
- [ ] Diff view before any package mutation
- [ ] Format-specific validators and deterministic exports
- [ ] Fantome manifest generation based on documented schema
- [ ] Optional preview/render integrations

## Milestone 3: AI-assisted authoring
- [ ] Task planner with explicit fact/hypothesis separation
- [ ] Retrieval over local tool docs and asset manifests
- [ ] Human approval before changes are applied
- [ ] Asset-generation adapters for textures and supported model formats
- [ ] Automated regression reports

## Milestone 4: Desktop UX
- [ ] Desktop UI with project browser and logs
- [ ] Package inspector, diff viewer, and export wizard
- [ ] Guided troubleshooting for missing effects and animations

## Non-goals
- Anti-cheat bypass, game-memory manipulation, account access, or stealth mechanisms.
- Claims of 100% in-game compatibility without an actual reproducible test.
