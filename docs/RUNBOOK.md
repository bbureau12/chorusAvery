# Runbook

Common workflows and commands for regular development.

Run commands from repository root unless noted otherwise.

## Environment

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Preflight

```powershell
python scripts\doctor.py --skip-birdnet
python scripts\doctor.py --strict
```

## Ingestion and detection

```powershell
python scripts\step_1_chunk_generator.py
python scripts\step_2_clip_parserv2.py
python scripts\run_birdnet.py
```

## Labeling and review

```powershell
python scripts\sound_labeler.py
python scripts\filter_review_tool.py
python scripts\review\species_review.py
```

## Dataset and training

```powershell
python scripts\training\dataset_builder.py
python scripts\training\train_test_eval_latest.py
```

## Evaluation and validation

```powershell
python scripts\training\eval\evaluate_with_gradcam.py
python scripts\validation\validate_self.py
python scripts\validation\validate_file.py
python scripts\validation\validate_cohorts.py
```

## Data quality and maintenance

```powershell
python scripts\file_maintenance\file_maintenance.py
python scripts\analysis\date_bias_analysis.py
```

## Troubleshooting checklist

- Confirm active venv and installed dependencies.
- Confirm FFmpeg and BirdNET model availability.
- Confirm database path expected by active script.
- Confirm working directory is repo root.
- Confirm destination folders exist and are writable.

## Related Docs

- [docs/PIPELINE.md](PIPELINE.md)
- [docs/REPO_MAP.md](REPO_MAP.md)
- [SETUP.md](../SETUP.md)
