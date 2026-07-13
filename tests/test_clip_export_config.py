import tempfile
import unittest
from pathlib import Path

from utils.clip_export_config import (
    export_clip_if_selected,
    load_default_export_directory,
    load_session_config,
    save_default_export_directory,
    save_session_config,
)


class ClipExportConfigTests(unittest.TestCase):
    def test_verified_directory_is_remembered(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            preferences = root / "preferences.json"
            expected = root / "exports"
            expected.mkdir()

            save_default_export_directory(expected, preferences)

            self.assertEqual(load_default_export_directory(preferences), expected.resolve())

    def test_invalid_directory_is_not_saved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            preferences = Path(temp_dir) / "preferences.json"
            with self.assertRaises(ValueError):
                save_default_export_directory(Path(temp_dir) / "missing", preferences)
            self.assertFalse(preferences.exists())

    def test_session_config_loads_species_ids(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            session = root / "session.json"
            exports = root / "exports"
            exports.mkdir()

            save_session_config([(3, "Spring Peeper")], exports, session)
            loaded = load_session_config(session)

            self.assertEqual(loaded["species_ids"], {3})
            self.assertEqual(loaded["export_directory"], exports.resolve())

    def test_session_config_with_missing_destination_is_ignored(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            session = root / "session.json"
            session.write_text(
                '{"species": [{"id": 3, "name": "Spring Peeper"}], '
                '"export_directory": "missing"}',
                encoding="utf-8",
            )

            self.assertIsNone(load_session_config(session))

    def test_matching_species_is_exported_once(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "clip.wav"
            source.write_bytes(b"audio")
            exports = root / "exports"
            exports.mkdir()
            config = {"species_ids": {3}, "export_directory": exports}

            exported = export_clip_if_selected(
                source,
                [(3, "Spring Peeper"), (3, "Spring Peeper")],
                [(3, "Spring Peeper")],
                config,
            )

            self.assertEqual(exported, exports / "clip.wav")
            self.assertEqual(exported.read_bytes(), b"audio")
            self.assertEqual(len(list(exports.iterdir())), 1)

    def test_non_species_label_with_same_id_is_not_exported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "clip.wav"
            source.write_bytes(b"audio")
            exports = root / "exports"
            exports.mkdir()
            config = {"species_ids": {3}, "export_directory": exports}

            exported = export_clip_if_selected(
                source,
                [(3, "Wind")],
                [(3, "Spring Peeper")],
                config,
            )

            self.assertIsNone(exported)
            self.assertEqual(list(exports.iterdir()), [])

    def test_existing_filename_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "clip.wav"
            source.write_bytes(b"new")
            exports = root / "exports"
            exports.mkdir()
            (exports / "clip.wav").write_bytes(b"old")
            config = {"species_ids": {3}, "export_directory": exports}

            exported = export_clip_if_selected(
                source,
                [(3, "Spring Peeper")],
                [(3, "Spring Peeper")],
                config,
            )

            self.assertEqual(exported, exports / "clip_1.wav")
            self.assertEqual((exports / "clip.wav").read_bytes(), b"old")
            self.assertEqual(exported.read_bytes(), b"new")


if __name__ == "__main__":
    unittest.main()
