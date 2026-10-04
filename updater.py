"""GitHub Releases update support for the local launcher only.

The updater never accesses the Arma 3 directory or the mod build. A release is
first downloaded to the user's local application-data folder and checked against
the SHA-256 value published with that same release. Replacing launcher files is
performed only after those checks succeed.
"""

from __future__ import annotations

import hashlib
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

GITHUB_API = "https://api.github.com"
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
VERSION_PATTERN = re.compile(r"^v?(\d+(?:\.\d+){0,3})(?:[-+].*)?$")
MAX_DOWNLOAD_BYTES = 150 * 1024 * 1024
MAX_EXTRACTED_BYTES = 300 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 10_000


@dataclass(frozen=True)
class UpdateSettings:
    repository: str
    asset_name: str
    checksum_asset: str

    @property
    def enabled(self) -> bool:
        return bool(REPOSITORY_PATTERN.fullmatch(self.repository))


def read_settings(config: dict[str, Any]) -> UpdateSettings:
    update = config.get("update") if isinstance(config.get("update"), dict) else {}
    return UpdateSettings(
        repository=str(update.get("github_repository", "")).strip(),
        asset_name=str(update.get("asset_name", "territoriya-sanka-launcher.zip")).strip(),
        checksum_asset=str(update.get("checksum_asset", "SHA256SUMS.txt")).strip(),
    )


def version_key(version: str) -> tuple[int, ...] | None:
    match = VERSION_PATTERN.fullmatch(version.strip())
    return tuple(int(part) for part in match.group(1).split(".")) if match else None


def is_newer(candidate: str, current: str) -> bool:
    candidate_key, current_key = version_key(candidate), version_key(current)
    if candidate_key is None or current_key is None:
        return False
    width = max(len(candidate_key), len(current_key))
    return candidate_key + (0,) * (width - len(candidate_key)) > current_key + (0,) * (width - len(current_key))


def _request(url: str, on_progress: Callable[[float], None] | None = None) -> bytes:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "Territory-Sanyok-Launcher"})
    with urllib.request.urlopen(request, timeout=12) as response:
        content_length = response.length
        if content_length is not None and content_length > MAX_DOWNLOAD_BYTES:
            raise ValueError("Файл обновления слишком большой.")
        if on_progress:
            on_progress(0.0)
        chunks: list[bytes] = []
        total = 0
        while chunk := response.read(64 * 1024):
            total += len(chunk)
            if total > MAX_DOWNLOAD_BYTES:
                raise ValueError("Файл обновления слишком большой.")
            chunks.append(chunk)
            if on_progress and content_length:
                on_progress(min(total / content_length, 1.0))
    if on_progress:
        on_progress(1.0)
    return b"".join(chunks)


def _release(settings: UpdateSettings) -> tuple[dict[str, Any] | None, str | None]:
    if not settings.enabled:
        return None, "GitHub-репозиторий ещё не настроен."
    try:
        raw = _request(f"{GITHUB_API}/repos/{settings.repository}/releases/latest")
        release = json.loads(raw.decode("utf-8"))
        if not isinstance(release, dict):
            raise ValueError("GitHub вернул некорректный ответ.")
        return release, None
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None, "В GitHub Releases пока нет опубликованной версии."
        return None, f"Не удалось проверить GitHub Releases: {error}."
    except (OSError, ValueError, urllib.error.URLError) as error:
        return None, f"Не удалось проверить GitHub Releases: {error}."


def check_for_update(settings: UpdateSettings, current_version: str) -> dict[str, Any]:
    release, error = _release(settings)
    if error:
        return {"enabled": settings.enabled, "available": False, "current_version": current_version, "message": error}
    assert release is not None
    tag = str(release.get("tag_name", "")).strip()
    asset_names = {str(asset.get("name", "")): asset for asset in release.get("assets", []) if isinstance(asset, dict)}
    if not tag or not version_key(tag):
        return {"enabled": True, "available": False, "current_version": current_version, "message": "В последнем релизе GitHub нет корректного номера версии."}
    if settings.asset_name not in asset_names or settings.checksum_asset not in asset_names:
        return {"enabled": True, "available": False, "current_version": current_version, "latest_version": tag, "message": "В релизе нет ZIP-архива или SHA256SUMS.txt для лаунчера."}
    available = is_newer(tag, current_version)
    return {
        "enabled": True,
        "available": available,
        "current_version": current_version,
        "latest_version": tag,
        "release_url": str(release.get("html_url", "")),
        "message": "Доступна новая версия лаунчера." if available else "Установлена актуальная версия лаунчера.",
    }


def _asset_url(release: dict[str, Any], name: str) -> str:
    for asset in release.get("assets", []):
        if isinstance(asset, dict) and asset.get("name") == name and isinstance(asset.get("browser_download_url"), str):
            return asset["browser_download_url"]
    raise ValueError(f"В релизе отсутствует {name}.")


def _expected_checksum(checksums: bytes, archive_name: str) -> str:
    for line in checksums.decode("utf-8", errors="replace").splitlines():
        match = re.fullmatch(r"([A-Fa-f0-9]{64})\s+\*?(.+)", line.strip())
        if match and match.group(2).replace("\\", "/").endswith(archive_name):
            return match.group(1).lower()
    raise ValueError(f"В SHA256SUMS.txt нет контрольной суммы для {archive_name}.")


def stage_update(
    settings: UpdateSettings,
    current_version: str,
    updates_dir: Path,
    on_progress: Callable[[int, str], None] | None = None,
) -> dict[str, Any]:
    def progress(value: int, message: str) -> None:
        if on_progress:
            on_progress(value, message)

    progress(8, "Проверяем сведения о новой версии…")
    checked = check_for_update(settings, current_version)
    if not checked.get("available"):
        return checked
    release, error = _release(settings)
    if error or release is None:
        return {**checked, "message": error or "Не удалось получить сведения о релизе."}
    try:
        progress(12, "Скачиваем обновление…")
        archive = _request(
            _asset_url(release, settings.asset_name),
            lambda fraction: progress(12 + int(fraction * 76), f"Скачиваем обновление… {int(fraction * 100)}%"),
        )
        progress(89, "Загружаем контрольную сумму…")
        expected = _expected_checksum(_request(_asset_url(release, settings.checksum_asset)), settings.asset_name)
        progress(93, "Проверяем контрольную сумму…")
        actual = hashlib.sha256(archive).hexdigest()
        if actual != expected:
            raise ValueError("Контрольная сумма ZIP-архива не совпала.")
        progress(96, "Готовим проверенное обновление…")
        version = str(checked["latest_version"]).lstrip("v")
        destination = updates_dir / version
        destination.mkdir(parents=True, exist_ok=True)
        archive_path = destination / settings.asset_name
        archive_path.write_bytes(archive)
        (destination / "update.json").write_text(json.dumps({"archive": settings.asset_name, "version": checked["latest_version"], "sha256": actual}, ensure_ascii=False), encoding="utf-8")
        progress(97, "Обновление проверено и готово к установке.")
        return {**checked, "staged": True, "message": "Обновление проверено и готово к установке."}
    except (OSError, ValueError, urllib.error.URLError, urllib.error.HTTPError) as error:
        return {**checked, "staged": False, "message": f"Не удалось подготовить обновление: {error}."}


def apply_staged_update(updates_dir: Path) -> Path:
    """Expand a verified staged bundle into a local replacement folder.

    The caller creates a short-lived helper only after this validation succeeds.
    Archives must contain exactly one top-level ``launcher`` folder so that a
    release cannot write beside the launcher installation.
    """
    candidates = sorted(updates_dir.glob("*/update.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not candidates:
        raise ValueError("Нет подготовленного обновления.")
    metadata_file = candidates[0]
    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    archive_path = metadata_file.parent / str(metadata.get("archive", ""))
    if not archive_path.is_file() or hashlib.sha256(archive_path.read_bytes()).hexdigest() != metadata.get("sha256"):
        raise ValueError("Подготовленный архив не прошёл повторную проверку SHA-256.")
    temporary = Path(tempfile.mkdtemp(prefix="territory-sanyok-update-", dir=updates_dir))
    try:
        with zipfile.ZipFile(archive_path) as archive:
            members = archive.infolist()
            unsafe_member = any(
                Path(member.filename).is_absolute()
                or ".." in Path(member.filename).parts
                or (member.external_attr >> 16) & 0o170000 == 0o120000
                for member in members
            )
            if not members or len(members) > MAX_ARCHIVE_MEMBERS or unsafe_member:
                raise ValueError("ZIP-архив содержит небезопасные пути.")
            if sum(member.file_size for member in members) > MAX_EXTRACTED_BYTES:
                raise ValueError("Распакованное обновление слишком большое.")
            roots = {Path(member.filename).parts[0] for member in members if member.filename.strip("/")}
            if roots != {"launcher"}:
                raise ValueError("ZIP-архив должен содержать единственную папку launcher/.")
            archive.extractall(temporary)
        source = temporary / "launcher"
        if not (source / "launcher.py").is_file() or not (source / "run-launcher.cmd").is_file() or not (source / "dist" / "client" / "index.html").is_file():
            raise ValueError("В обновлении отсутствуют обязательные файлы лаунчера.")
        destination = updates_dir / "pending-install"
        if destination.exists():
            shutil.rmtree(destination)
        shutil.move(str(source), str(destination))
        return destination
    finally:
        shutil.rmtree(temporary, ignore_errors=True)

