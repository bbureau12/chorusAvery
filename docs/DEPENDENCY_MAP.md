# ChorusAvery Dependency Map

> Generated for safe reorganization planning. All import relationships between Python files in the project.

---

## Table of Contents
1. [sys.path Manipulation Patterns](#syspath-manipulation-patterns)
2. [utils/ Module Imports](#utils-module-imports)
3. [Internal Cross-Dependencies](#internal-cross-dependencies)
4. [Per-File Import Detail](#per-file-import-detail)
5. [Reverse Dependency Index (Who Imports What)](#reverse-dependency-index)
6. [Circular Dependencies](#circular-dependencies)
7. [Entry Points vs Library Modules](#entry-points-vs-library-modules)

---

## sys.path Manipulation Patterns

All files that modify `sys.path` to enable `utils.*` or `scripts.*` imports:

| File | Pattern |
|------|---------|
| `scripts/run_birdnet.py` | `sys.path.append(str(Path(__file__).resolve().parent.parent))` |
| `scripts/import_csv_to_db.py` | `sys.path.append(str(Path(__file__).resolve().parent.parent))` |
| `scripts/training/dataset_builder.py` | `project_root = ...join('..', '..')` then `sys.path.insert(0, project_root)` |
| `scripts/training/train_test_eval_latest.py` | `project_root = ...join('..', '..')` then `sys.path.insert(0, project_root)` |
| `scripts/training/non_animal_pipeline.py` | `project_root = ...join('..', '..')` then `sys.path.insert(0, project_root)` |
| `scripts/training/non_animal_pipeline_multiselect.py` | `project_root = ...join('..', '..')` then `sys.path.insert(0, project_root)` |
| `scripts/training/non_animal_pipeline_multiselect_category.py` | `project_root = ...join('..', '..')` then `sys.path.insert(0, project_root)` |
| `scripts/training/non_animal_pipeline_multiselect_granular.py` | `project_root = ...join('..', '..')` then `sys.path.insert(0, project_root)` |
| `scripts/training/non_animal_pipeline_multiselect_multiclass.py` | `project_root = ...join('..', '..')` then `sys.path.insert(0, project_root)` |
| `scripts/training/collection/species_pipeline_v0.py` | `project_root = ...join('..', '..', '..')` then `sys.path.insert(0, project_root)` |
| `scripts/training/eval/evaluate_with_gradcam.py` | `project_root = ...join('..', '..', '..')` then `sys.path.insert(0, project_root)` |
| `scripts/training/eval/mixed_species_evaluator.py` | `project_root = ...join('..', '..', '..')` then `sys.path.insert(0, project_root)` |
| `scripts/validation/validate_self.py` | `project_root = ...join('..', '..')` then `sys.path.insert(0, project_root)` |
| `scripts/validation/validate_file.py` | `project_root = ...join('..', '..')` then `sys.path.insert(0, project_root)` |
| `scripts/validation/validate_cohorts.py` | `project_root = ...join('..', '..')` then `sys.path.insert(0, project_root)` |
| `scripts/augmentation/species_nonspecies_augmentor.py` | `project_root = ...join('..', '..')` then `sys.path.insert(0, project_root)` |

All `project_root` values resolve to **`D:\Projects\ChorusAvery\chorusAvery`** (the workspace root).

---

## utils/ Module Imports

### Internal dependencies within utils/

| utils/ file | Imports from utils/ |
|-------------|-------------------|
| `utils/split_wav.py` | `from boost_if_needed import boost_if_needed` (**bare import** — only works if `utils/` is on sys.path or CWD) |
| `utils/load_detections_from_csv.py` | `from utils.db import get_db_connection` (absolute-style import) |
| All other utils/ files | **No local imports** — only stdlib/external |

> **⚠ Warning**: `utils/split_wav.py` uses a bare import `from boost_if_needed import boost_if_needed` which assumes `utils/` is the CWD or on sys.path. This is fragile.

### utils/ files that are imported by scripts

| utils/ module | Imported by |
|--------------|-------------|
| `utils.augmentation_helpers` | `scripts/training/dataset_builder.py`, `scripts/training/non_animal_pipeline.py`, `scripts/training/non_animal_pipeline_multiselect.py`, `scripts/training/non_animal_pipeline_multiselect_category.py`, `scripts/training/non_animal_pipeline_multiselect_granular.py`, `scripts/training/non_animal_pipeline_multiselect_multiclass.py` |
| `utils.entityfinder` | `scripts/augmentation/species_nonspecies_augmentor.py` |
| `utils.filter_existing_files` | `scripts/training/collection/collect_negative_clips.py` |
| `utils.generate_spectogram` | `scripts/augmentation/augmentation_generator.py`, `scripts/training/collection/collect_negative_clips.py`, `scripts/training/collection/species_pipeline_v0.py`, `scripts/training/dataset_builder.py`, `scripts/training/eval/evaluate_with_gradcam.py`, `scripts/training/eval/mixed_species_evaluator.py`, `scripts/training/non_animal_pipeline.py`, `scripts/training/non_animal_pipeline_multiselect.py`, `scripts/training/non_animal_pipeline_multiselect_category.py`, `scripts/training/non_animal_pipeline_multiselect_granular.py`, `scripts/training/non_animal_pipeline_multiselect_multiclass.py`, `scripts/validation/validate_cohorts.py`, `scripts/validation/validate_self.py` |
| `utils.grad_cam` | `scripts/training/eval/evaluate_with_gradcam.py` |
| `utils.insert_detections` | `scripts/import_csv_to_db.py` |
| `utils.load_detections_from_csv` | `scripts/run_birdnet.py` |
| `utils.load_model` | `scripts/training/eval/evaluate_with_gradcam.py` |
| `utils.location_selector` | `scripts/run_birdnet.py` |
| `utils.model_spec_writer` | `scripts/validation/validate_cohorts.py` |
| `utils.split_wav` | `scripts/run_birdnet.py` |
| `utils.trainer_spec_writer` | `scripts/training/train_test_eval_latest.py` |
| `utils.db` | `utils/load_detections_from_csv.py` (internal utils→utils dependency) |
| `utils.boost_if_needed` | `utils/split_wav.py` (internal utils→utils, bare import) |

### utils/ files that are NEVER imported by any other file
- `utils/compile_negative_annotations.py` (empty file)
- `utils/datetime.py`
- `utils/generate_clips.py`
- `utils/lora_manager.py`
- `utils/prune_clips_by_volume.py`
- `utils/quietHorizon.py`
- `utils/review_unmapped_species.py`
- `utils/sync_detection_species.py`
- `utils/sync_species_codes.py`

> **⚠ Warning**: `utils/datetime.py` shadows the stdlib `datetime` module. Any file doing `from datetime import datetime` while `utils/` is on sys.path could accidentally import this instead of the stdlib.

---

## Internal Cross-Dependencies

### scripts → scripts imports

| Importing file | Imports from |
|---------------|-------------|
| `scripts/augmentation/species_nonspecies_augmentor.py` | `scripts.augmentation.augmentation_generator.AugmentedClipGenerator` |
| `scripts/training/collection/species_pipeline_v0.py` | `scripts.augmentation.species_nonspecies_augmentor.SpeciesAugmentor`, `scripts.training.collection.collect_negative_clips.NegativeClipGenerator` |
| `scripts/training/dataset_builder.py` | `scripts.training.collection.collect_negative_clips.NegativeClipGenerator` |
| `scripts/hugging_face/transformer/build_manifest_multiclass_audio_1.py` | `scripts.training.collection.collect_negative_clips.NegativeClipGenerator` |
| `scripts/hugging_face/transformer/collect_negative_clips.py` | `training.collection.collect_negative_clips.NegativeClipGenerator` (⚠ different import style) |
| `scripts/hugging_face/transformer/train_ast_3.py` | `dataset_audio_2.load_manifest` (bare import — sibling file) |
| `scripts/training/eval/mixed_species_evaulator_test.py` | `mixed_species_evaluator.MixedSpeciesEvaluator` (bare import — sibling file) |

### Dependency chains (transitive)

```
species_pipeline_v0.py
  → species_nonspecies_augmentor.py
    → augmentation_generator.py → utils.generate_spectogram
    → utils.entityfinder
  → collect_negative_clips.py → utils.filter_existing_files, utils.generate_spectogram
  → utils.generate_spectogram

dataset_builder.py
  → collect_negative_clips.py → utils.filter_existing_files, utils.generate_spectogram
  → utils.augmentation_helpers
  → utils.generate_spectogram

evaluate_with_gradcam.py
  → utils.load_model
  → utils.grad_cam
  → utils.generate_spectogram
```

---

## Per-File Import Detail

### Root-level scripts (`scripts/*.py`)

| File | Standard Library | External Packages | Local Imports |
|------|-----------------|-------------------|---------------|
| `step_1_chunk_generator.py` | os, sqlite3, datetime | pydub | — |
| `step_2_clip_parserv2.py` | os, json, math, datetime | matplotlib, pydub | — |
| `run_birdnet.py` | os, subprocess, csv, sys, uuid, pathlib | pydub | `utils.load_detections_from_csv`, `utils.location_selector`, `utils.split_wav` |
| `sound_labeler.py` | random, shutil, sqlite3, os, datetime, json, re | numpy, pydub, simpleaudio, scipy, matplotlib, timezonefinder, pytz | — |
| `filter_review_tool.py` | os, shutil, sqlite3 | pydub, simpleaudio | — |
| `import_csv_to_db.py` | csv, sys, pathlib | — | `utils.insert_detections` |
| `plot_clips.py` | os | matplotlib, numpy, pydub | — |
| `gap_finder.py` | sqlite3, pathlib | — | — |
| `gap_scanner.py` | os, pathlib, sqlite3 | pydub | — |
| `soundparser.py` | os, math | pydub | — |
| `convertclipsto16b.py` | os | pydub | — |
| `mergefiles.py` | csv, pathlib | pydub | — |

### scripts/training/*.py

| File | Standard Library | External Packages | Local Imports |
|------|-----------------|-------------------|---------------|
| `build_animal_dataset.py` | os, shutil, sqlite3, random | pydub, tqdm, numpy, librosa, matplotlib | — |
| `build_non_animal_dataset.py` | os, shutil, sqlite3, random | pydub, tqdm, numpy, librosa, matplotlib | — |
| `build_species_dataset.py` | os, shutil, sqlite3, random | pydub, tqdm, numpy, librosa, matplotlib | — |
| `check_dataset_balance.py` | os | — | — |
| `dataset_builder.py` | datetime, os, sys, sqlite3, json, random, shutil, re | pydub | `utils.augmentation_helpers`, `utils.generate_spectogram`, `scripts.training.collection.collect_negative_clips` |
| `frog_specific_trainer_temp.py` | os, shutil, random | pydub, tqdm, librosa, numpy, matplotlib | — |
| `frog_trainer_negative.py` | os, shutil, random | pydub, tqdm, librosa, numpy, matplotlib | — |
| `new_species_pipeline.py` | *(entirely commented out)* | — | — |
| `non_animal_pipeline.py` | os, random, shutil, sqlite3, sys, argparse | pydub | `utils.augmentation_helpers`, `utils.generate_spectogram` |
| `non_animal_pipeline_multiselect.py` | os, random, shutil, sqlite3, sys, re | pydub | `utils.augmentation_helpers`, `utils.generate_spectogram` |
| `non_animal_pipeline_multiselect_category.py` | os, random, shutil, sqlite3, sys, re | pydub | `utils.augmentation_helpers`, `utils.generate_spectogram` |
| `non_animal_pipeline_multiselect_granular.py` | os, random, shutil, sqlite3, sys, re | pydub | `utils.augmentation_helpers`, `utils.generate_spectogram` |
| `non_animal_pipeline_multiselect_multiclass.py` | os, random, shutil, sqlite3, sys, re, csv, itertools | pydub | `utils.augmentation_helpers`, `utils.generate_spectogram` |
| `rebalance_datasets.py` | os, random | — | — |
| `test_harness.py` | os, random | numpy, tensorflow | — |
| `train_test_eval.py` | *(entirely commented out)* | — | — |
| `train_test_eval_latest.py` | os, random, sys, datetime, json, itertools, shutil | numpy, tensorflow, matplotlib, sklearn, seaborn | `utils.trainer_spec_writer` |
| `train_test_eval_multiselect.py` | datetime, os, json | tensorflow, pandas, numpy, matplotlib, sklearn, seaborn | — |

### scripts/training/collection/*.py

| File | Standard Library | External Packages | Local Imports |
|------|-----------------|-------------------|---------------|
| `collect_negative_clips.py` | os, random, shutil, sqlite3, json | pydub | `utils.filter_existing_files`, `utils.generate_spectogram` |
| `species_pipeline_v0.py` | os, random, shutil, sqlite3, sys | pydub, numpy, matplotlib, scipy | `utils.generate_spectogram`, `scripts.augmentation.species_nonspecies_augmentor`, `scripts.training.collection.collect_negative_clips` |

### scripts/training/eval/*.py

| File | Standard Library | External Packages | Local Imports |
|------|-----------------|-------------------|---------------|
| `evaluate_with_gradcam.py` | os, sys, argparse, random, sqlite3 | numpy, cv2, matplotlib, pydub, tensorflow | `utils.load_model`, `utils.grad_cam`, `utils.generate_spectogram` |
| `mixed_species_evaluator.py` | os, json, sqlite3, random, sys | numpy, matplotlib, sklearn, tensorflow, pydub | `utils.generate_spectogram` |
| `mixed_species_evaulator_test.py` | — | — | `mixed_species_evaluator` (bare) |
| `new_model_eval.py` | os, random | numpy, tensorflow | — |

### scripts/validation/*.py

| File | Standard Library | External Packages | Local Imports |
|------|-----------------|-------------------|---------------|
| `validate_cohorts.py` | os, random, sqlite3, sys | tensorflow, numpy, pydub, matplotlib, tqdm | `utils.generate_spectogram`, `utils.model_spec_writer` |
| `validate_file.py` | os, random, sys | tensorflow, numpy | — |
| `validate_self.py` | os, sqlite3, random, sys | tensorflow, numpy, pydub, matplotlib, scipy | `utils.generate_spectogram` |

### scripts/augmentation/*.py

| File | Standard Library | External Packages | Local Imports |
|------|-----------------|-------------------|---------------|
| `augmentation_generator.py` | os, random, sqlite3, csv | pydub | `utils.generate_spectogram` |
| `batch_augment.py` | os | pydub | — |
| `species_nonspecies_augmentor.py` | os, random, sys | — | `utils.entityfinder`, `scripts.augmentation.augmentation_generator` |

### scripts/batch_load/*.py

| File | Standard Library | External Packages | Local Imports |
|------|-----------------|-------------------|---------------|
| `batch_insert.py` | os, random, shutil, sqlite3 | pydub, numpy, matplotlib, scipy | — |

### scripts/review/*.py

| File | Standard Library | External Packages | Local Imports |
|------|-----------------|-------------------|---------------|
| `species_review.py` | datetime, json, sqlite3, os | pydub, simpleaudio | — |

### scripts/sound_isolation/*.py

| File | Standard Library | External Packages | Local Imports |
|------|-----------------|-------------------|---------------|
| `bandpassfilter.py` | os, random, sqlite3 | librosa, numpy, matplotlib, scipy, pydub, soundfile | — |
| `bandpass_filter_clips.py` | sqlite3, os, datetime | pydub, scipy, soundfile | — |
| `fingerprint_isolation.py` | — | numpy, soundfile, scipy | — |

### scripts/sound_isolation/clustering/*.py

| File | Standard Library | External Packages | Local Imports |
|------|-----------------|-------------------|---------------|
| `avg_clustered_spectograms.py` | os, collections | numpy, PIL | — |
| `cluster_representative_samples.py` | os, shutil | numpy, PIL, sklearn | — |
| `cluster_spectograms.py` | os | numpy, PIL, sklearn, matplotlib | — |
| `remove_representative_fingerprint.py` | os, io | numpy, pydub, librosa, matplotlib, tensorflow, scipy, PIL | — |

### scripts/spectogram_comparison/*.py

| File | Standard Library | External Packages | Local Imports |
|------|-----------------|-------------------|---------------|
| `species_spectogram.py` | sqlite3, os, random | numpy, matplotlib, scipy | — |

### scripts/modification/*.py

| File | Standard Library | External Packages | Local Imports |
|------|-----------------|-------------------|---------------|
| `boost_clip_audio.py` | os | pydub | — |

### scripts/hugging_face/transformer/*.py

| File | Standard Library | External Packages | Local Imports |
|------|-----------------|-------------------|---------------|
| `build_manifest_multiclass_audio_1.py` | os, csv, sqlite3, pathlib, random, argparse | pydub | `scripts.training.collection.collect_negative_clips` |
| `collect_negative_clips.py` | — | — | `training.collection.collect_negative_clips` (⚠ bare — needs CWD=`scripts/`) |
| `dataset_audio_2.py` | — | datasets (HF), pandas | — |
| `train_ast_3.py` | os, json | transformers, numpy, sklearn | `dataset_audio_2` (bare — sibling) |

### scripts/hugging_face/transformer/inference/*.py

| File | Standard Library | External Packages | Local Imports |
|------|-----------------|-------------------|---------------|
| `gradio_demo.py` | json | torch, gradio, torchaudio, transformers | — |
| `inference.py` | json, sys | transformers, torchaudio | — |

### scripts/import/*.py

| File | Standard Library | External Packages | Local Imports |
|------|-----------------|-------------------|---------------|
| `import_new_soundfile.py` | os, shutil, sqlite3, datetime | — | — |

### scripts/file_maintenance/*.py

| File | Standard Library | External Packages | Local Imports |
|------|-----------------|-------------------|---------------|
| `file_maintenance.py` | os, json, hashlib, shutil, datetime, pathlib | — | — |

### scripts/one-off/*.py

| File | Standard Library | External Packages | Local Imports |
|------|-----------------|-------------------|---------------|
| `batch_replace_species.py` | sqlite3 | — | — |
| `convert_utc_clips.py` | sqlite3, datetime | pytz | — |
| `delete_model_wavs.py` | os | — | — |
| `move_mechanical_tests.py` | os, shutil | — | — |
| `parent_orphaned_clips.py` | sqlite3, os, re | — | — |

### scripts/readings/*.py

| File | Standard Library | External Packages | Local Imports |
|------|-----------------|-------------------|---------------|
| `import_readings.py` | requests, json, sqlite3, datetime, os | — | — |
| `import_temperatures.py` | os, sqlite3, glob | pandas | — |

### scripts/tuning/*.py

| File | Standard Library | External Packages | Local Imports |
|------|-----------------|-------------------|---------------|
| `fine-tune.py` | os | pydub | — |

### scripts/analysis/*.py

| File | Standard Library | External Packages | Local Imports |
|------|-----------------|-------------------|---------------|
| `date_bias_analysis.py` | pathlib, argparse, sqlite3, re, wave, contextlib, datetime | pandas, numpy | — |

### notebooks/*.py

| File | Standard Library | External Packages | Local Imports |
|------|-----------------|-------------------|---------------|
| `hf.py` | — | datasets (HF) | — |

### utils/ files

| File | Standard Library | External Packages | Local Imports |
|------|-----------------|-------------------|---------------|
| `augmentation_helpers.py` | random | pydub | — |
| `boost_if_needed.py` | — | pydub | — |
| `compile_negative_annotations.py` | *(empty file)* | — | — |
| `datetime.py` | datetime | — | — |
| `db.py` | pathlib, sqlite3 | — | — |
| `entityfinder.py` | sqlite3 | — | — |
| `filter_existing_files.py` | os | — | — |
| `generate_clips.py` | os, random, shutil, sqlite3 | pydub | — |
| `generate_spectogram.py` | — | librosa, matplotlib, numpy, cv2 | — |
| `grad_cam.py` | — | tensorflow, numpy, cv2 | — |
| `insert_detections.py` | sqlite3, datetime | — | — |
| `load_detections_from_csv.py` | csv, sqlite3, pathlib | — | `utils.db` |
| `load_model.py` | os, json | — | — |
| `location_selector.py` | pathlib, sqlite3 | — | — |
| `lora_manager.py` | os, json, shutil | — | — |
| `model_spec_writer.py` | json, os | — | — |
| `prune_clips_by_volume.py` | argparse, json, os, sys, typing | pydub (optional via try/except) | — |
| `quietHorizon.py` | os, shutil, sqlite3 | — | — |
| `review_unmapped_species.py` | sqlite3, pathlib | pydub, simpleaudio | — |
| `split_wav.py` | pathlib | pydub | `boost_if_needed` (bare import) |
| `sync_detection_species.py` | sqlite3, pathlib | — | — |
| `sync_species_codes.py` | sqlite3, pathlib | — | — |
| `trainer_spec_writer.py` | json, os | — | — |

---

## Reverse Dependency Index

### Which utils/ modules are consumed and by whom

```
utils.augmentation_helpers
  ├── scripts/training/dataset_builder.py
  ├── scripts/training/non_animal_pipeline.py
  ├── scripts/training/non_animal_pipeline_multiselect.py
  ├── scripts/training/non_animal_pipeline_multiselect_category.py
  ├── scripts/training/non_animal_pipeline_multiselect_granular.py
  └── scripts/training/non_animal_pipeline_multiselect_multiclass.py

utils.boost_if_needed
  └── utils/split_wav.py (bare import)

utils.db
  └── utils/load_detections_from_csv.py

utils.entityfinder
  └── scripts/augmentation/species_nonspecies_augmentor.py

utils.filter_existing_files
  └── scripts/training/collection/collect_negative_clips.py

utils.generate_spectogram   ←← MOST WIDELY USED
  ├── scripts/augmentation/augmentation_generator.py
  ├── scripts/training/collection/collect_negative_clips.py
  ├── scripts/training/collection/species_pipeline_v0.py
  ├── scripts/training/dataset_builder.py
  ├── scripts/training/eval/evaluate_with_gradcam.py
  ├── scripts/training/eval/mixed_species_evaluator.py
  ├── scripts/training/non_animal_pipeline.py
  ├── scripts/training/non_animal_pipeline_multiselect.py
  ├── scripts/training/non_animal_pipeline_multiselect_category.py
  ├── scripts/training/non_animal_pipeline_multiselect_granular.py
  ├── scripts/training/non_animal_pipeline_multiselect_multiclass.py
  ├── scripts/validation/validate_cohorts.py
  └── scripts/validation/validate_self.py

utils.grad_cam
  └── scripts/training/eval/evaluate_with_gradcam.py

utils.insert_detections
  └── scripts/import_csv_to_db.py

utils.load_detections_from_csv
  └── scripts/run_birdnet.py

utils.load_model
  └── scripts/training/eval/evaluate_with_gradcam.py

utils.location_selector
  └── scripts/run_birdnet.py

utils.model_spec_writer
  └── scripts/validation/validate_cohorts.py

utils.split_wav
  └── scripts/run_birdnet.py

utils.trainer_spec_writer
  └── scripts/training/train_test_eval_latest.py
```

### Which scripts are imported by other scripts

```
scripts.augmentation.augmentation_generator
  └── scripts/augmentation/species_nonspecies_augmentor.py

scripts.augmentation.species_nonspecies_augmentor
  └── scripts/training/collection/species_pipeline_v0.py

scripts.training.collection.collect_negative_clips
  ├── scripts/training/dataset_builder.py
  ├── scripts/training/collection/species_pipeline_v0.py
  └── scripts/hugging_face/transformer/build_manifest_multiclass_audio_1.py

training.collection.collect_negative_clips  [bare — different import form]
  └── scripts/hugging_face/transformer/collect_negative_clips.py

mixed_species_evaluator  [bare — sibling import]
  └── scripts/training/eval/mixed_species_evaulator_test.py

dataset_audio_2  [bare — sibling import]
  └── scripts/hugging_face/transformer/train_ast_3.py
```

---

## Circular Dependencies

**No circular dependencies detected.** The dependency graph is a DAG:

```
scripts/training/collection/species_pipeline_v0.py
  → scripts/augmentation/species_nonspecies_augmentor.py
    → scripts/augmentation/augmentation_generator.py  (leaf — only imports utils)
    → utils/entityfinder.py  (leaf)
  → scripts/training/collection/collect_negative_clips.py  (leaf — only imports utils)
```

All other inter-script imports are one-directional.

---

## Entry Points vs Library Modules

### Entry Points (scripts with `if __name__ == "__main__":`)

**Root scripts:**
- `scripts/step_1_chunk_generator.py` — *(inferred, no guard but standalone)*
- `scripts/step_2_clip_parserv2.py` — *(inferred, no guard but standalone)*
- `scripts/run_birdnet.py` ✓
- `scripts/sound_labeler.py` ✓
- `scripts/filter_review_tool.py` ✓
- `scripts/import_csv_to_db.py` ✓
- `scripts/mergefiles.py` ✓
- `scripts/gap_finder.py` ✓
- `scripts/gap_scanner.py` ✓
- `scripts/soundparser.py` — *(inferred)*
- `scripts/convertclipsto16b.py` — *(inferred)*
- `scripts/plot_clips.py` — *(inferred)*

**Training scripts:**
- `scripts/training/build_animal_dataset.py` ✓
- `scripts/training/build_non_animal_dataset.py` ✓
- `scripts/training/build_species_dataset.py` ✓
- `scripts/training/dataset_builder.py` ✓
- `scripts/training/frog_specific_trainer_temp.py` ✓
- `scripts/training/frog_trainer_negative.py` ✓
- `scripts/training/non_animal_pipeline.py` ✓
- `scripts/training/non_animal_pipeline_multiselect.py` ✓
- `scripts/training/non_animal_pipeline_multiselect_category.py` ✓
- `scripts/training/non_animal_pipeline_multiselect_granular.py` ✓
- `scripts/training/non_animal_pipeline_multiselect_multiclass.py` ✓
- `scripts/training/collection/species_pipeline_v0.py` ✓
- `scripts/training/eval/evaluate_with_gradcam.py` ✓
- `scripts/training/eval/mixed_species_evaulator_test.py` ✓
- `scripts/training/eval/new_model_eval.py` ✓

**Validation:**
- `scripts/validation/validate_self.py` ✓
- `scripts/validation/validate_file.py` ✓
- `scripts/validation/validate_cohorts.py` ✓

**Other:**
- `scripts/augmentation/batch_augment.py` ✓
- `scripts/batch_load/batch_insert.py` ✓
- `scripts/review/species_review.py` ✓
- `scripts/sound_isolation/bandpassfilter.py` ✓
- `scripts/sound_isolation/bandpass_filter_clips.py` ✓
- `scripts/analysis/date_bias_analysis.py` ✓
- `scripts/tuning/fine-tune.py` ✓
- `scripts/import/import_new_soundfile.py` ✓
- `scripts/file_maintenance/file_maintenance.py` ✓
- `scripts/one-off/batch_replace_species.py` ✓
- `scripts/one-off/delete_model_wavs.py` ✓
- `scripts/one-off/parent_orphaned_clips.py` ✓
- `scripts/hugging_face/transformer/build_manifest_multiclass_audio_1.py` ✓
- `scripts/hugging_face/transformer/train_ast_3.py` ✓
- `scripts/hugging_face/transformer/inference/inference.py` ✓
- `scripts/hugging_face/transformer/inference/gradio_demo.py` ✓

### Library Modules (imported by other files, no standalone execution or used as classes)

- `utils/augmentation_helpers.py` — provides `split_data`, `pad_audio`, `overlay_noise`, `polarize_volume`
- `utils/boost_if_needed.py` — provides `boost_if_needed()`
- `utils/db.py` — provides `get_db_connection()`
- `utils/entityfinder.py` — provides `EntityFinder` class
- `utils/filter_existing_files.py` — provides `filter_existing_files()`
- `utils/generate_spectogram.py` — provides `generate_mel_spectrogram()`, `load_spectrogram()`, `get_spectrogram_settings()`
- `utils/grad_cam.py` — provides `compute_gradcam()`, `overlay_gradcam()`
- `utils/insert_detections.py` — provides `insert_detection()`
- `utils/load_detections_from_csv.py` — provides `load_detections_from_csv()`
- `utils/load_model.py` — provides `list_models()`, `choose_model()`, `extract_species_id()`, `extract_results_folder()`
- `utils/location_selector.py` — provides `choose_location()`
- `utils/model_spec_writer.py` — provides `SpecWriter` class
- `utils/split_wav.py` — provides `split_wav()`
- `utils/trainer_spec_writer.py` — provides `write_trainer_specs()`
- `scripts/augmentation/augmentation_generator.py` — provides `AugmentedClipGenerator` class
- `scripts/augmentation/species_nonspecies_augmentor.py` — provides `SpeciesAugmentor` class
- `scripts/training/collection/collect_negative_clips.py` — provides `NegativeClipGenerator` class
- `scripts/training/eval/mixed_species_evaluator.py` — provides `MixedSpeciesEvaluator` class
- `scripts/hugging_face/transformer/dataset_audio_2.py` — provides `load_manifest()`

### Dual-Purpose (both imported AND have `__main__` guard)

- `utils/generate_clips.py` ✓ (has `__main__` but is a standalone util)
- `utils/lora_manager.py` ✓
- `utils/prune_clips_by_volume.py` ✓
- `utils/review_unmapped_species.py` ✓
- `utils/sync_detection_species.py` ✓
- `utils/sync_species_codes.py` ✓

### Dead/Inactive Code

- `scripts/training/train_test_eval.py` — entirely commented out
- `scripts/training/new_species_pipeline.py` — entirely commented out
- `utils/compile_negative_annotations.py` — empty file

---

## Hazards & Notes for Reorganization

1. **`utils/datetime.py` shadows stdlib** — If `utils/` is ever added to `sys.path`, `from datetime import datetime` will resolve to this file instead of the standard library module. Consider renaming.

2. **`utils/split_wav.py` uses bare import** — `from boost_if_needed import boost_if_needed` only works if CWD is `utils/` or `utils/` is on sys.path. Should be `from utils.boost_if_needed import boost_if_needed`.

3. **Two different patterns for sys.path manipulation:**
   - `sys.path.append(str(Path(__file__).resolve().parent.parent))` — used by `run_birdnet.py`, `import_csv_to_db.py`
   - `project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))` + `sys.path.insert(0, project_root)` — used by most training/validation scripts

4. **`scripts/hugging_face/transformer/collect_negative_clips.py`** uses `from training.collection.collect_negative_clips import ...` (assumes `scripts/` is CWD or on path) — different from all other files that use `from scripts.training.collection...`.

5. **Bare sibling imports** in `scripts/training/eval/mixed_species_evaulator_test.py` and `scripts/hugging_face/transformer/train_ast_3.py` assume CWD is their own directory.

6. **No `__init__.py` files** anywhere — no proper Python packages. All cross-module imports rely on `sys.path` hacks.

7. **`utils/generate_spectogram.py` is the most critical dependency** — imported by 13 scripts. Any changes to its API will have wide impact.

---

## External Package Summary

| Package | Used by (count) | Category |
|---------|----------------|----------|
| `pydub` | 30+ files | Audio processing |
| `numpy` | 20+ files | Numerical |
| `matplotlib` | 15+ files | Visualization |
| `tensorflow`/`keras` | 10+ files | ML model training/eval |
| `sqlite3` (stdlib) | 20+ files | Database |
| `scipy` | 8 files | Signal processing |
| `librosa` | 8 files | Audio analysis |
| `sklearn` | 5 files | ML metrics |
| `simpleaudio` | 4 files | Audio playback |
| `cv2` (opencv) | 3 files | Image processing |
| `PIL` (Pillow) | 4 files | Image processing |
| `soundfile` | 3 files | Audio I/O |
| `tqdm` | 5 files | Progress bars |
| `pandas` | 3 files | Data manipulation |
| `seaborn` | 2 files | Visualization |
| `transformers` (HF) | 3 files | Transformer models |
| `torchaudio` | 2 files | Audio for PyTorch |
| `torch` | 1 file | PyTorch |
| `gradio` | 1 file | Web UI |
| `datasets` (HF) | 2 files | Dataset loading |
| `pytz` | 2 files | Timezone |
| `timezonefinder` | 1 file | Timezone lookup |
| `requests` | 1 file | HTTP |
