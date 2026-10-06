import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import launcher


class LauncherConfigurationTests(unittest.TestCase):
    def test_explicit_mod_build_directory_overrides_managed_default(self):
        with patch("launcher.load_config", return_value={"mod_build_dir": "example-mod-build"}):
            self.assertEqual(launcher.mod_build_dir(), Path("example-mod-build"))

    def test_blank_mod_build_directory_keeps_development_default(self):
        with patch("launcher.load_config", return_value={"mod_build_dir": "  "}):
            self.assertEqual(launcher.mod_build_dir(), launcher.DEFAULT_MOD_DIR)
            self.assertTrue(launcher.uses_managed_mod_dir())

    def test_each_mod_uses_an_isolated_managed_directory(self):
        self.assertNotEqual(launcher.mod_build_dir("umcfd"), launcher.mod_build_dir("umfc"))
        with patch("launcher.load_config", return_value={"mod_build_dirs": {"umfc": "fuel-build"}}):
            self.assertEqual(launcher.mod_build_dir("umfc"), Path("fuel-build"))
            self.assertFalse(launcher.uses_managed_mod_dir("umfc"))

    def test_launch_command_joins_enabled_mods_with_one_arma_argument(self):
        command = launcher.build_game_command(
            Path("C:/Games/Arma 3/arma3_x64.exe"),
            [{"path": "C:/Mods/contact-fuse-drone"}, {"path": "C:/Mods/fuel-canister"}],
        )
        self.assertEqual(
            command,
            [
                "C:\\Games\\Arma 3\\arma3_x64.exe",
                "-mod=C:\\Mods\\contact-fuse-drone;C:\\Mods\\fuel-canister",
                "-world=empty",
                "-noSplash",
            ],
        )

    def test_embedded_window_has_a_local_launcher_title_and_safe_minimum_size(self):
        self.assertEqual(launcher.LAUNCHER_NAME, "Территория Санька: Королевская Битва")
        self.assertEqual(launcher.WINDOW_SIZE, (960, 640))
        self.assertEqual(launcher.WINDOW_MIN_SIZE, (900, 580))
        self.assertEqual(launcher.WINDOW_ICON.name, "launcher-icon.ico")

    def test_compact_layout_keeps_page_fixed_and_scrolls_only_tile_content(self):
        project = Path(__file__).resolve().parents[1]
        styles = (project / "src" / "styles.css").read_text(encoding="utf-8")
        app = (project / "src" / "App.jsx").read_text(encoding="utf-8")
        self.assertIn("html, body, #root { width: 100%; height: 100%; overflow: hidden; }", styles)
        self.assertIn(".content-grid { flex: 1 1 auto; min-height: 0; display: grid; grid-template-columns: 1.06fr 1.25fr 0.85fr;", styles)
        self.assertIn(".tile-scroll { flex: 1 1 auto; min-height: 0; margin-top: 7px; overflow-y: auto;", styles)
        self.assertIn('className="tile-scroll mods-scroll"', app)
        self.assertIn('className="tile-scroll maps-scroll"', app)
