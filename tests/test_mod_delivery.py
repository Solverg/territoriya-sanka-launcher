import hashlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mod_delivery import install_mod, read_settings


def archive_bytes(root: str = "contact-fuse-drone", pbo: str = "umcfd_main.pbo") -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(f"{root}/mod.cpp", 'name = "Own mod";')
        archive.writestr(f"{root}/addons/{pbo}", b"own-pbo")
    return stream.getvalue()


def manifest_bytes(bundle: bytes, archive: str = "contact-fuse-drone.zip", root: str = "contact-fuse-drone", version: str = "1.1.0") -> bytes:
    return json.dumps({
        "version": version,
        "archive": archive,
        "sha256": hashlib.sha256(bundle).hexdigest(),
        "bytes": len(bundle),
        "root": root,
    }).encode()


class ModDeliveryTests(unittest.TestCase):
    def test_defaults_use_the_public_mod_folder(self):
        settings = read_settings({}, "mods/contact-fuse-drone/mod-manifest.json")
        self.assertTrue(settings.enabled)
        self.assertEqual(settings.manifest_path, "mods/contact-fuse-drone/mod-manifest.json")

    def test_checked_archive_is_installed_outside_the_game_directory(self):
        bundle = archive_bytes()
        manifest = manifest_bytes(bundle)
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "mods" / "contact-fuse-drone"
            with patch("mod_delivery._request", side_effect=[manifest, bundle]):
                install_mod(read_settings({}, "mods/contact-fuse-drone/mod-manifest.json"), destination, "umcfd_main.pbo", "Contact Fuse Drone")
            self.assertEqual((destination / "addons" / "umcfd_main.pbo").read_bytes(), b"own-pbo")

    def test_bad_checksum_does_not_install_a_mod(self):
        bundle = archive_bytes()
        manifest = json.dumps({
            "version": "1.1.0",
            "archive": "contact-fuse-drone.zip",
            "sha256": "0" * 64,
            "bytes": len(bundle),
            "root": "contact-fuse-drone",
        }).encode()
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "mods" / "contact-fuse-drone"
            with patch("mod_delivery._request", side_effect=[manifest, bundle]):
                with self.assertRaisesRegex(ValueError, "Контрольная сумма"):
                    install_mod(read_settings({}, "mods/contact-fuse-drone/mod-manifest.json"), destination, "umcfd_main.pbo", "Contact Fuse Drone")
            self.assertFalse(destination.exists())

    def test_each_mod_source_keeps_its_own_manifest(self):
        settings = read_settings({"mod_sources": {"umfc": {"manifest_path": "mods/fuel-canister/mod-manifest.json"}}}, "mods/fuel-canister/mod-manifest.json", "umfc")
        self.assertEqual(settings.manifest_path, "mods/fuel-canister/mod-manifest.json")

    def test_fuel_archive_requires_its_own_pbo(self):
        bundle = archive_bytes("fuel-canister", "umfc_main.pbo")
        manifest = manifest_bytes(bundle, "fuel-canister.zip", "fuel-canister", "1.0.0")
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "mods" / "fuel-canister"
            with patch("mod_delivery._request", side_effect=[manifest, bundle]):
                install_mod(read_settings({}, "mods/fuel-canister/mod-manifest.json", "umfc"), destination, "umfc_main.pbo", "Канистра с топливом")
            self.assertTrue((destination / "addons" / "umfc_main.pbo").is_file())

    def test_matching_receipt_skips_archive_download(self):
        bundle = archive_bytes()
        manifest = manifest_bytes(bundle)
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "mods" / "contact-fuse-drone"
            (destination / "addons").mkdir(parents=True)
            (destination / "addons" / "umcfd_main.pbo").write_bytes(b"current-pbo")
            (destination.parent / ".contact-fuse-drone-package.json").write_text(
                json.dumps({"format": 1, "version": "1.1.0", "archive_sha256": hashlib.sha256(bundle).hexdigest()}),
                encoding="utf-8",
            )
            with patch("mod_delivery._request", return_value=manifest) as request:
                result = install_mod(read_settings({}, "mods/contact-fuse-drone/mod-manifest.json"), destination, "umcfd_main.pbo", "Contact Fuse Drone")
            self.assertEqual(request.call_count, 1)
            self.assertEqual(result["version"], "1.1.0")
            self.assertEqual((destination / "addons" / "umcfd_main.pbo").read_bytes(), b"current-pbo")

    def test_legacy_package_is_replaced_and_receipted(self):
        bundle = archive_bytes()
        manifest = manifest_bytes(bundle)
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "mods" / "contact-fuse-drone"
            (destination / "addons").mkdir(parents=True)
            (destination / "addons" / "umcfd_main.pbo").write_bytes(b"old-pbo")
            with patch("mod_delivery._request", side_effect=[manifest, bundle]):
                result = install_mod(read_settings({}, "mods/contact-fuse-drone/mod-manifest.json"), destination, "umcfd_main.pbo", "Contact Fuse Drone")
            self.assertEqual(result["version"], "1.1.0")
            self.assertEqual((destination / "addons" / "umcfd_main.pbo").read_bytes(), b"own-pbo")
            receipt = json.loads((destination.parent / ".contact-fuse-drone-package.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["version"], "1.1.0")
            self.assertEqual(receipt["archive_sha256"], hashlib.sha256(bundle).hexdigest())
