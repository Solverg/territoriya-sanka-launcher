import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import launcher


class LauncherConfigurationTests(unittest.TestCase):
    def test_game_details_accepts_either_arma_executable_without_a_version_gate(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temporary:
            game_dir = Path(temporary)
            (game_dir / "arma3.exe").touch()
            details = launcher.game_details(game_dir)

        self.assertTrue(details["exists"])
        self.assertTrue(details["compatible"])
        self.assertTrue(details["path"].endswith("arma3.exe"))

    def test_steam_manifest_finds_a_renamed_arma_install_folder(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temporary:
            steam = Path(temporary) / "Steam"
            library = Path(temporary) / "Games"
            (steam / "steamapps").mkdir(parents=True)
            (library / "steamapps" / "common" / "Arma 3 — Custom").mkdir(parents=True)
            (steam / "steamapps" / "libraryfolders.vdf").write_text(
                '"libraryfolders" { "0" { "path" "' + str(library).replace("\\", "\\\\") + '" } }',
                encoding="utf-8",
            )
            (library / "steamapps" / "appmanifest_107410.acf").write_text(
                '"AppState" { "appid" "107410" "installdir" "Arma 3 — Custom" }', encoding="utf-8",
            )
            with patch("launcher.steam_roots", return_value=[steam]):
                candidates = launcher.candidate_game_dirs()

        self.assertIn((library / "steamapps" / "common" / "Arma 3 — Custom", "манифест Steam"), candidates)

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

    def test_embedded_window_adapts_to_the_usable_screen_size(self):
        self.assertEqual(launcher.LAUNCHER_NAME, "Территория Санька: Королевская Битва")
        self.assertEqual(launcher.adaptive_window_geometry((1920, 1080)), ((960, 640), (520, 480)))
        self.assertEqual(launcher.adaptive_window_geometry((800, 600)), ((776, 552), (520, 480)))
        self.assertEqual(launcher.adaptive_window_geometry((400, 300)), ((376, 252), (376, 252)))
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
        self.assertIn("ЛОКАЛЬНЫЙ РЕЖИМ", app)
        self.assertNotIn("GITHUB DELIVERY", app)
        self.assertIn("@media (max-width: 599px)", styles)

