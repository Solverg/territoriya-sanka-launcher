import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import launcher


class LauncherConfigurationTests(unittest.TestCase):
    def test_explicit_mod_build_directory_overrides_development_default(self):
        with patch("launcher.load_config", return_value={"mod_build_dir": "example-mod-build"}):
            self.assertEqual(launcher.mod_build_dir(), Path("example-mod-build"))

    def test_blank_mod_build_directory_keeps_development_default(self):
        with patch("launcher.load_config", return_value={"mod_build_dir": "  "}):
            self.assertEqual(launcher.mod_build_dir(), launcher.DEFAULT_MOD_BUILD_DIR)
