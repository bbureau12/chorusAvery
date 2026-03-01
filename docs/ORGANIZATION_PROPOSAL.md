# Organization Proposal

This is a low-risk cleanup plan focused on maintainability without breaking working workflows.

## Principles

- Preserve current script behavior first.
- Normalize paths and naming before moving code.
- Make each phase testable and reversible.

## Phase 1: Documentation and command stability

Goals:
- Keep docs aligned with what actually runs.
- Establish one canonical run path from repo root.

Actions:
- Maintain `README`, `SETUP`, `PIPELINE`, `RUNBOOK`, `SCRIPT_REFERENCE`, `DATA_CONTRACTS`.
- Mark high-use scripts explicitly in docs.

Exit criteria:
- New contributors can run ingestion to training using docs only.

## Phase 2: Path and config normalization

Goals:
- Remove hidden path assumptions.

Actions:
- Standardize DB path to `./db/chorusAvery.db`.
- Add a single config module (for DB path, data roots, model roots).
- Update scripts that currently use `./chorusAvery.db` or `models/complete` inconsistently.

Exit criteria:
- No script depends on alternate DB path unless explicitly configured.

## Phase 3: Import hygiene (no file moves yet)

Goals:
- Reduce fragility from `sys.path` manipulation.

Actions:
- Add `__init__.py` files under `scripts/` and `utils/` trees.
- Replace bare imports where possible (`utils/split_wav.py` import fix).
- Standardize local imports to project-root-relative import style.

Exit criteria:
- Core scripts run from repo root without ad-hoc import hacks.

## Phase 4: Script taxonomy cleanup

Goals:
- Separate stable workflows from experimental/one-off code.

Actions:
- Keep production-like workflows in place:
- `scripts/import`, `scripts/training`, `scripts/validation`, `scripts/review`
- Move low-frequency one-offs to an archive folder (for example `scripts/_archive/`) with an index doc.
- Rename typos gradually (for example `spectogram` to `spectrogram`) with compatibility shims.

Exit criteria:
- New team members can identify "safe to run" scripts quickly.

## Phase 5: Thin package extraction

Goals:
- Share core logic between scripts without copy-paste.

Actions:
- Extract reusable functions into a small package namespace (for example `chorus/`):
- `chorus/audio.py`
- `chorus/spectrogram.py`
- `chorus/db.py`
- Keep existing scripts as wrappers that call extracted functions.

Exit criteria:
- At least chunking, clip parsing, and dataset build reuse package-level helpers.

## Immediate low-risk fixes to queue

1. Wire `--auto` correctly in `scripts/training/eval/evaluate_with_gradcam.py` (`main(args.auto)`).
2. Resolve DB path drift between root and `db/` file locations.
3. Align model directory assumptions (`models/` vs `models/complete/`).
4. Add a simple `scripts/doctor.py` preflight checker (ffmpeg, db path, required folders).

## Suggested folder posture (now)

Keep:
- `scripts/` as execution entrypoints.
- `utils/` as shared helpers.

Add:
- `scripts/_archive/` for low-confidence one-off scripts after review.
- `docs/changelog/` for cleanup decisions if you want traceability.

## Related docs

- [docs/REORGANIZATION_PLAN.md](REORGANIZATION_PLAN.md)
- [docs/DEPENDENCY_MAP.md](DEPENDENCY_MAP.md)
- [docs/SCRIPT_REFERENCE.md](SCRIPT_REFERENCE.md)
- [docs/DATA_CONTRACTS.md](DATA_CONTRACTS.md)
