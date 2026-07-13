import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from utils import clip_export_config as export_config


class ClipParserExportPromptTests(unittest.TestCase):
    def test_directory_prompt_retries_and_saves_verified_choice(self):
        expected = Path("D:/verified").resolve()
        with (
            patch.object(export_config, "load_default_export_directory", return_value=None),
            patch.object(
                export_config,
                "save_default_export_directory",
                side_effect=[ValueError, expected],
            ) as save_default,
            patch("builtins.input", side_effect=["missing", str(expected)]),
        ):
            result = export_config.prompt_for_export_directory()

        self.assertEqual(result, expected)
        self.assertEqual(save_default.call_args_list, [call("missing"), call(str(expected))])

    def test_species_selection_accepts_repeated_searches_and_enter_to_finish(self):
        finder = Mock()
        finder.search_species.side_effect = [
            [(3, "Spring Peeper")],
            [(7, "Wood Frog")],
        ]
        with patch("builtins.input", side_effect=["1", "wood", "1", ""]):
            selected = export_config.select_species(finder, "peeper")

        self.assertEqual(selected, [(3, "Spring Peeper"), (7, "Wood Frog")])


if __name__ == "__main__":
    unittest.main()
