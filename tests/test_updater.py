import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from updater import apply_staged_update, is_newer, read_settings


class UpdaterTests(unittest.TestCase):
    def test_settings_stay_disabled_until_a_repository_exists(self):
        settings = read_settings({"update": {"github_repository": ""}})
        self.assertFalse(settings.enabled)
        self.assertEqual(settings.asset_name, "territoriya-sanka-launcher.zip")

    def test_versions_compare_without_treating_prereleases_as_newer(self):
        self.assertTrue(is_newer("v0.2.0", "0.1.9"))
        self.assertFalse(is_newer("v0.1.0-beta.1", "0.1.0"))

    def test_staged_archive_requires_a_single_launcher_folder(self):
        with tempfile.TemporaryDirectory() as temporary:
            updates = Path(temporary) / "updates"
            version = updates / "0.2.0"
            version.mkdir(parents=True)
            archive = version / "territoriya-sanka-launcher.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("launcher/launcher.py", "print('ok')")
                bundle.writestr("launcher/run-launcher.cmd", "@echo off")
                bundle.writestr("launcher/dist/client/index.html", "<!doctype html>")
            archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
            (version / "update.json").write_text(json.dumps({"archive": archive.name, "sha256": archive_hash}), encoding="utf-8")

            pending = apply_staged_update(updates)

            self.assertTrue((pending / "launcher.py").is_file())
            self.assertTrue((pending / "dist" / "client" / "index.html").is_file())
