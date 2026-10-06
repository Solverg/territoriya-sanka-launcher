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
        self.assertIn('DefaultDirName={code:GetInstallDir}', definition)
        self.assertIn("LocalAppData := GetEnv('LOCALAPPDATA');", definition)
        self.assertIn("CloseApplications=yes", definition)
        self.assertIn("RestartApplications=no", definition)
        self.assertNotIn('Arma 3', definition)

    def test_shortcut_paths_do_not_reuse_the_display_name_with_a_colon(self):
        definition = (PROJECT / "installer" / "TerritorySanyokLauncher.iss").read_text(encoding="utf-8")
        self.assertIn('#define AppShortcutName "Территория Санька - Королевская Битва"', definition)
        self.assertIn('#define AppDesktopShortcutName "Территория Санька"', definition)
        self.assertIn('DefaultGroupName={#AppShortcutName}', definition)
        self.assertIn('Name: "{autoprograms}\\{#AppShortcutName}"', definition)
        self.assertIn('Name: "{autodesktop}\\{#AppDesktopShortcutName}"', definition)
        self.assertNotIn('DefaultGroupName={#AppName}', definition)

    def test_packaged_launcher_uses_the_exe_icon_and_webview_runtime(self):
        build = (PROJECT / "scripts" / "build-app.ps1").read_text(encoding="utf-8")
        definition = (PROJECT / "installer" / "TerritorySanyokLauncher.iss").read_text(encoding="utf-8")
        self.assertIn('--icon "$(Join-Path $project \'public\\\\assets\\\\launcher-icon.ico\')"', build)
        self.assertIn('--collect-all webview', build)
        self.assertTrue((PROJECT / "public" / "assets" / "launcher-icon.png").is_file())
        self.assertTrue((PROJECT / "public" / "assets" / "launcher-icon.ico").is_file())
        self.assertIn('Filename: "{app}\\{#AppExeName}"', definition)

    def test_installer_reuses_an_existing_install_and_prevents_downgrade(self):
        definition = (PROJECT / "installer" / "TerritorySanyokLauncher.iss").read_text(encoding="utf-8")
        self.assertIn('Inno Setup: App Path', definition)
        self.assertIn('DisplayVersion', definition)
        self.assertIn("CompareLauncherVersions(InstalledVersion, '{#AppVersion}')", definition)
        self.assertIn('function CompareLauncherVersions', definition)
        self.assertIn('Установка версии {#AppVersion} отменена', definition)
        self.assertIn('будет обновлена до версии {#AppVersion} в той же папке', definition)
