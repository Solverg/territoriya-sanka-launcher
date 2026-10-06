"""Verified GitHub delivery for the launcher's Arma 3 addons.

The downloaded archive is restricted to the launcher's own application-data
folder.  It never writes to the Arma 3 directory, Steam, BattlEye, or saves.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
REF_PATTERN = re.compile(r"^[A-Za-z0-9._/-]+$")
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
MAX_EXTRACTED_BYTES = 100 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 100


@dataclass(frozen=True)
class ModDeliverySettings:
    repository: str
    ref: str
    manifest_path: str

    @property
    def enabled(self) -> bool:
        return bool(
            REPOSITORY_PATTERN.fullmatch(self.repository)
            and REF_PATTERN.fullmatch(self.ref)
            and not self.ref.startswith("/")
            and ".." not in Path(self.ref).parts
            and self.manifest_path.startswith("mods/")
            and ".." not in Path(self.manifest_path).parts
        )


@dataclass(frozen=True)
class ModManifest:
    version: str
    archive: str
    sha256: str
    bytes: int
    root: str


def _receipt_path(destination: Path) -> Path:
    """Keep the downloaded-package identity beside, rather than inside, a mod."""
    return destination.parent / f".{destination.name}-package.json"


def _matches_installed_package(destination: Path, manifest: ModManifest, required_pbo: str) -> bool:
    """A legacy folder without our receipt is deliberately refreshed once."""
    if not (destination / "addons" / required_pbo).is_file():
        return False
    try:
        receipt = json.loads(_receipt_path(destination).read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return False
    return (
        isinstance(receipt, dict)
        and receipt.get("format") == 1
        and receipt.get("version") == manifest.version
        and receipt.get("archive_sha256") == manifest.sha256
    )


def _write_receipt(destination: Path, manifest: ModManifest) -> None:
    receipt_path = _receipt_path(destination)
    temporary = receipt_path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(
            {"format": 1, "version": manifest.version, "archive_sha256": manifest.sha256},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    temporary.replace(receipt_path)


def read_settings(
    config: dict[str, Any], default_manifest_path: str, mod_id: str = "umcfd"
) -> ModDeliverySettings:
    """Read one mod source, retaining the old Contact Fuse override only for it."""
    configured_sources = config.get("mod_sources")
    source = configured_sources.get(mod_id) if isinstance(configured_sources, dict) else None
    if not isinstance(source, dict):
        source = config.get("mod") if mod_id == "umcfd" and isinstance(config.get("mod"), dict) else {}
    return ModDeliverySettings(
        repository=str(source.get("github_repository", "Solverg/territoriya-sanka-launcher")).strip(),
        ref=str(source.get("ref", "main")).strip(),
        manifest_path=str(source.get("manifest_path", default_manifest_path)).strip(),
    )


def _raw_url(settings: ModDeliverySettings, path: str) -> str:
    return f"https://raw.githubusercontent.com/{settings.repository}/{settings.ref}/{path}"


def _request(url: str, on_progress: Callable[[float], None] | None = None) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Territory-Sanyok-Launcher", "Accept": "application/octet-stream"})
    with urllib.request.urlopen(request, timeout=20) as response:
        content_length = response.length
        if content_length is not None and content_length > MAX_DOWNLOAD_BYTES:
            raise ValueError("Файл мода слишком большой.")
        parts: list[bytes] = []
        total = 0
        while chunk := response.read(64 * 1024):
            total += len(chunk)
            if total > MAX_DOWNLOAD_BYTES:
                raise ValueError("Файл мода слишком большой.")
            parts.append(chunk)
            if on_progress and content_length:
                on_progress(min(total / content_length, 1.0))
    if on_progress:
        on_progress(1.0)
    return b"".join(parts)


def _manifest(payload: bytes) -> ModManifest:
    try:
        data = json.loads(payload.decode("utf-8"))
        version = str(data["version"])
        archive = str(data["archive"])
        digest = str(data["sha256"]).lower()
        size = int(data["bytes"])
        root = str(data["root"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("Манифест мода имеет неверный формат.") from error
    if (
        not VERSION_PATTERN.fullmatch(version)
        or Path(archive).name != archive
        or not archive.endswith(".zip")
        or not SHA256_PATTERN.fullmatch(digest)
        or not 0 < size <= MAX_DOWNLOAD_BYTES
        or Path(root).name != root
        or root in {"", ".", ".."}
    ):
        raise ValueError("Манифест мода содержит небезопасные данные.")
    return ModManifest(version=version, archive=archive, sha256=digest, bytes=size, root=root)


def _safe_extract(archive_data: bytes, manifest: ModManifest, destination: Path, required_pbo: str) -> Path:
    with zipfile.ZipFile(io.BytesIO(archive_data)) as archive:
        members = archive.infolist()
        unsafe = any(
            Path(member.filename).is_absolute()
            or ".." in Path(member.filename).parts
            or (member.external_attr >> 16) & 0o170000 == 0o120000
            for member in members
        )
        roots = {Path(member.filename).parts[0] for member in members if member.filename.strip("/")}
        if (
            not members
            or len(members) > MAX_ARCHIVE_MEMBERS
            or unsafe
            or roots != {manifest.root}
            or sum(member.file_size for member in members) > MAX_EXTRACTED_BYTES
        ):
            raise ValueError("ZIP-архив мода содержит небезопасные пути.")
        archive.extractall(destination)
    unpacked = destination / manifest.root
    if not (unpacked / "addons" / required_pbo).is_file():
        raise ValueError(f"В архиве нет addons/{required_pbo}.")
    return unpacked


def install_mod(
    settings: ModDeliverySettings,
    destination: Path,
    required_pbo: str,
    display_name: str,
    on_progress: Callable[[int, str], None] | None = None,
) -> dict[str, str]:
    """Download, checksum, validate, and atomically install the bundled mod."""
    if not settings.enabled:
        raise ValueError("GitHub-источник мода не настроен безопасно.")

    def progress(value: int, message: str) -> None:
        if on_progress:
            on_progress(value, message)

    progress(5, f"Проверяем версию {display_name}…")
    try:
        manifest = _manifest(_request(_raw_url(settings, settings.manifest_path)))
        if _matches_installed_package(destination, manifest, required_pbo):
            progress(100, f"{display_name} уже актуален (v{manifest.version}).")
            return {"version": manifest.version, "message": f"{display_name} уже актуален (v{manifest.version})."}
        manifest_folder = str(Path(settings.manifest_path).parent).replace("\\", "/")
        progress(12, f"Скачиваем {display_name}…")
        archive_data = _request(
            _raw_url(settings, f"{manifest_folder}/{manifest.archive}"),
            lambda fraction: progress(12 + int(fraction * 72), f"Скачиваем {display_name}… {int(fraction * 100)}%"),
        )
        if len(archive_data) != manifest.bytes:
            raise ValueError("Размер ZIP-архива не совпал с манифестом.")
        progress(86, "Проверяем контрольную сумму мода…")
        if hashlib.sha256(archive_data).hexdigest() != manifest.sha256:
            raise ValueError("Контрольная сумма ZIP-архива мода не совпала.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="verified-mod-", dir=destination.parent) as temporary:
            extracted = _safe_extract(archive_data, manifest, Path(temporary), required_pbo)
            staging = destination.with_name(f".{destination.name}-staging")
            if staging.exists():
                shutil.rmtree(staging)
            shutil.copytree(extracted, staging)
            progress(96, "Устанавливаем проверенный мод локально…")
            backup = destination.with_name(f".{destination.name}-previous")
            if backup.exists():
                shutil.rmtree(backup)
            if destination.exists():
                destination.replace(backup)
            try:
                staging.replace(destination)
                _write_receipt(destination, manifest)
            except OSError:
                if backup.exists():
                    if destination.exists():
                        shutil.rmtree(destination)
                    backup.replace(destination)
                raise
            if backup.exists():
                shutil.rmtree(backup)
        progress(100, f"{display_name} v{manifest.version} установлен и готов.")
        return {"version": manifest.version, "message": f"{display_name} v{manifest.version} установлен и готов."}
    except (OSError, ValueError, urllib.error.URLError, urllib.error.HTTPError, zipfile.BadZipFile) as error:
        raise ValueError(f"Не удалось установить мод: {error}.") from error
