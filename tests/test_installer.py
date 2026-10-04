import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]


class InstallerDefinitionTests(unittest.TestCase):
    def test_installer_offers_an_optional_desktop_shortcut(self):
        definition = (PROJECT / "installer" / "TerritorySanyokLauncher.iss").read_text(encoding="utf-8")
        self.assertIn('[Tasks]', definition)
        self.assertIn('Name: "desktopicon"', definition)
        self.assertIn('Создать ярлык на рабочем столе', definition)

    def test_installer_is_per_user_and_has_no_game_payload(self):
        definition = (PROJECT / "installer" / "TerritorySanyokLauncher.iss").read_text(encoding="utf-8")
        self.assertIn('PrivilegesRequired=lowest', definition)
        self.assertIn('{localappdata}', definition)
        self.assertNotIn('Arma 3', definition)

