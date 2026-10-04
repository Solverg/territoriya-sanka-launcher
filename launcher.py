"""Offline launcher for the local Arma 3 Territory of Sanyok build."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from updater import apply_staged_update, check_for_update, read_settings, stage_update

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
# A public clone must not embed an owner's installation path.  The portable
# launcher uses its validated cache, configuration, Steam, and registry routes.
DEFAULT_GAME_DIR: Path | None = None
DEFAULT_MOD_BUILD_DIR = ROOT / "mods" / "arma3-contact-fuse-drone" / ".hemttout" / "build"
CONFIG_FILE = HERE / "launcher.config.json"
APP_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share")) / "UniversalModder" / "Arma3ContactFuseLauncher"
LOCATION_CACHE_FILE = APP_DATA_DIR / "game-location.json"
UPDATES_DIR = APP_DATA_DIR / "updates"
SUPPORTED_GAME_VERSION = "1.94"
LAUNCHER_VERSION = "1.0.2"
HOST, PORT = "127.0.0.1", 8765

UPDATE_LOCK = threading.Lock()
UPDATE_STATE: dict[str, Any] = {
    "phase": "idle",
    "progress": 0,
    "message": "Проверяем обновления лаунчера…",
    "blocking": True,
}


def update_status() -> dict[str, Any]:
    with UPDATE_LOCK:
        return dict(UPDATE_STATE)


def set_update_status(**changes: Any) -> dict[str, Any]:
    with UPDATE_LOCK:
        UPDATE_STATE.update(changes)
        return dict(UPDATE_STATE)


def load_config() -> dict[str, Any]:
    """Read the old portable override without making it the primary cache."""
    config: dict[str, Any] = {}
    if CONFIG_FILE.is_file():
        try:
            saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                config = saved
        except (OSError, ValueError):
            pass
    return config


def load_location_cache() -> dict[str, str]:
    try:
        cached = json.loads(LOCATION_CACHE_FILE.read_text(encoding="utf-8"))
        if isinstance(cached.get("game_dir"), str) and cached["game_dir"].strip():
            return {"game_dir": cached["game_dir"].strip(), "source": str(cached.get("source", "cache"))}
    except (OSError, ValueError, AttributeError):
        pass
    return {}


def save_location_cache(game_dir: Path, source: str) -> bool:
    """Keep only a validated local install directory outside the project."""
    try:
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        temporary_file = LOCATION_CACHE_FILE.with_suffix(".tmp")
        temporary_file.write_text(
            json.dumps({"game_dir": str(game_dir), "source": source}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary_file.replace(LOCATION_CACHE_FILE)
        return True
    except OSError:
        return False


def executable_in(game_dir: Path) -> Path:
    return game_dir / "arma3_x64.exe"


def file_version(executable: Path) -> str | None:
    """Return Windows FILEVERSION without starting or otherwise changing the game."""
    if os.name != "nt" or not executable.is_file():
        return None
    try:
        import ctypes
        from ctypes import wintypes

        version = ctypes.WinDLL("version", use_last_error=True)
        size = version.GetFileVersionInfoSizeW(str(executable), None)
        if not size:
            return None
        buffer = ctypes.create_string_buffer(size)
        if not version.GetFileVersionInfoW(str(executable), 0, size, buffer):
            return None
        value = ctypes.c_void_p()
        value_length = wintypes.UINT()
        if not version.VerQueryValueW(buffer, "\\", ctypes.byref(value), ctypes.byref(value_length)):
            return None

        class VSFixedFileInfo(ctypes.Structure):
            _fields_ = [
                ("dwSignature", wintypes.DWORD), ("dwStrucVersion", wintypes.DWORD),
                ("dwFileVersionMS", wintypes.DWORD), ("dwFileVersionLS", wintypes.DWORD),
                ("dwProductVersionMS", wintypes.DWORD), ("dwProductVersionLS", wintypes.DWORD),
                ("dwFileFlagsMask", wintypes.DWORD), ("dwFileFlags", wintypes.DWORD),
                ("dwFileOS", wintypes.DWORD), ("dwFileType", wintypes.DWORD),
                ("dwFileSubtype", wintypes.DWORD), ("dwFileDateMS", wintypes.DWORD),
                ("dwFileDateLS", wintypes.DWORD),
            ]

        info = ctypes.cast(value, ctypes.POINTER(VSFixedFileInfo)).contents
        return f"{info.dwFileVersionMS >> 16}.{info.dwFileVersionMS & 0xffff}"
    except (AttributeError, OSError):
        return None


def steam_roots() -> list[Path]:
    roots = [Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Steam", Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Steam"]
    if os.name != "nt":
        return roots
    try:
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for key_name in (r"Software\Valve\Steam", r"SOFTWARE\WOW6432Node\Valve\Steam"):
                try:
                    with winreg.OpenKey(hive, key_name) as key:
                        steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
                        roots.append(Path(steam_path))
                except OSError:
                    continue
    except ImportError:
        pass
    return roots


def steam_library_dirs(steam_root: Path) -> list[Path]:
    libraries = [steam_root]
    library_file = steam_root / "steamapps" / "libraryfolders.vdf"
    try:
        for raw_path in re.findall(r'"path"\s+"([^"]+)"', library_file.read_text(encoding="utf-8", errors="ignore"), re.IGNORECASE):
            libraries.append(Path(raw_path.replace("\\\\", "\\")))
    except OSError:
        pass
    return libraries


def registry_game_dirs() -> list[Path]:
    if os.name != "nt":
        return []
    found: list[Path] = []
    try:
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for key_name in (r"SOFTWARE\Bohemia Interactive Studio\Arma 3", r"SOFTWARE\WOW6432Node\Bohemia Interactive Studio\Arma 3"):
                try:
                    with winreg.OpenKey(hive, key_name) as key:
                        for value_name in ("MAIN", "InstallPath", "Path"):
                            try:
                                path, _ = winreg.QueryValueEx(key, value_name)
                                found.append(Path(path))
                                break
                            except OSError:
                                continue
                except OSError:
                    continue
    except ImportError:
        pass
    return found


def candidate_game_dirs() -> list[tuple[Path, str]]:
    candidates: list[tuple[Path, str]] = []
    cached = load_location_cache()
    if cached:
        candidates.append((Path(cached["game_dir"]), cached["source"]))
    configured = load_config().get("game_dir")
    if configured:
        candidates.append((Path(configured), "launcher.config.json"))
    if DEFAULT_GAME_DIR is not None:
        candidates.append((DEFAULT_GAME_DIR, "стандартная папка"))
    candidates.extend((directory, "реестр Bohemia") for directory in registry_game_dirs())
    for steam_root in steam_roots():
        candidates.extend((library / "steamapps" / "common" / "Arma 3", "библиотека Steam") for library in steam_library_dirs(steam_root))
    return candidates


def mod_build_dir() -> Path:
    """Use an explicit local mod build when this launcher is cloned separately."""
    configured = load_config().get("mod_build_dir")
    return Path(configured).expanduser() if isinstance(configured, str) and configured.strip() else DEFAULT_MOD_BUILD_DIR


def game_details(game_dir: Path) -> dict[str, Any]:
    executable = executable_in(game_dir)
    exists = executable.is_file()
    version = file_version(executable) if exists else None
    compatible = exists and version == SUPPORTED_GAME_VERSION
    return {"path": str(executable), "exists": exists, "version": version, "compatible": compatible}


def find_game() -> tuple[Path | None, str | None]:
    seen: set[str] = set()
    for game_dir, source in candidate_game_dirs():
        normalized = os.path.normcase(os.path.abspath(game_dir))
        if normalized in seen:
            continue
        seen.add(normalized)
        if game_details(game_dir)["compatible"]:
            save_location_cache(game_dir, source)
            return game_dir, source
    return None, None


def game_is_running() -> bool:
    """Read the exact process name; never terminates or modifies a process."""
    if os.name != "nt":
        return False
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq arma3_x64.exe", "/FO", "CSV", "/NH"],
        capture_output=True, text=True, check=False, creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return "arma3_x64.exe" in result.stdout.lower()


def status() -> dict[str, Any]:
    game_dir, source = find_game()
    game = game_details(game_dir) if game_dir else {"path": "", "exists": False, "version": None, "compatible": False}
    build_dir = mod_build_dir()
    mod_ready = build_dir.is_dir() and (build_dir / "addons" / "umcfd_main.pbo").is_file()
    return {
        "ready": game["compatible"] and mod_ready,
        "game": {"name": "Arma 3 1.94", **game, "source": source},
        "mods": [{"id": "umcfd", "name": "Contact Fuse Drone", "description": "Квадрокоптеры с контактным зарядом для всех фракций", "path": str(build_dir), "exists": mod_ready}],
        "maps": [],
        "launcher": {"name": "Территория Санька: Королевская Битва", "version": LAUNCHER_VERSION},
    }


class LauncherHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(HERE / "dist" / "client"), **kwargs)

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def send_json(self, body: dict[str, Any], code: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/status":
            self.send_json(status())
            return
        if self.path == "/api/update/status":
            self.send_json(update_status())
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/api/update/start":
            self.send_json(start_forced_update(self.server))
            return
        if self.path == "/api/game-path":
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
                game_dir = Path(payload.get("game_dir", "")).expanduser()
            except (OSError, ValueError, TypeError):
                self.send_json({"message": "Введите путь к папке Arma 3."}, HTTPStatus.BAD_REQUEST)
                return
            details = game_details(game_dir)
            if not details["exists"]:
                self.send_json({"message": "В этой папке не найден arma3_x64.exe."}, HTTPStatus.BAD_REQUEST)
                return
            if not details["compatible"]:
                version = details["version"] or "неизвестной версии"
                self.send_json({"message": f"Найдена Arma 3 {version}; требуется версия {SUPPORTED_GAME_VERSION}."}, HTTPStatus.BAD_REQUEST)
                return
            if not save_location_cache(game_dir, "указано игроком"):
                self.send_json({"message": "Не удалось записать локальный кэш пути."}, HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self.send_json({"message": "Путь к Arma 3 сохранён локально.", "status": status()})
            return
        if self.path != "/api/launch":
            self.send_json({"message": "Маршрут не найден."}, HTTPStatus.NOT_FOUND)
            return
        current = status()
        if not current["game"]["compatible"]:
            self.send_json({"message": "Не найдена совместимая Arma 3 1.94. Укажите папку игры в лаунчере."}, HTTPStatus.BAD_REQUEST)
            return
        if not current["mods"][0]["exists"]:
            self.send_json({"message": "Не найдена собранная PBO мода. Сначала выполните HEMTT build."}, HTTPStatus.BAD_REQUEST)
            return
        if game_is_running():
            self.send_json({"message": "Arma 3 уже запущена. Повторный запуск намеренно заблокирован."}, HTTPStatus.CONFLICT)
            return
        game_executable = Path(current["game"]["path"])
        mod_dir = Path(current["mods"][0]["path"])
        command = [str(game_executable), f"-mod={mod_dir}", "-world=empty", "-noSplash"]
        process = subprocess.Popen(command, cwd=str(game_executable.parent))
        self.send_json({"message": f"Arma 3 запущена (PID {process.pid}) с «Территория Санька: Королевская Битва»."})


def begin_replacement() -> None:
    """Start the short-lived Windows helper after all update checks succeeded."""
    pending = apply_staged_update(UPDATES_DIR)
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    helper = APP_DATA_DIR / "install-pending-update.cmd"
    restart_script = HERE / "run-launcher.cmd"
    helper.write_text(
        "@echo off\r\nsetlocal\r\ntimeout /t 2 /nobreak >nul\r\n"
        f'robocopy "{pending}" "{HERE}" /E /R:1 /W:1 /XD node_modules .git /XF launcher.config.json MODLOG.md\r\n'
        f'start "" "{restart_script}"\r\n',
        encoding="utf-8",
    )
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    subprocess.Popen(["cmd", "/c", str(helper)], creationflags=creationflags)


def start_forced_update(server: ThreadingHTTPServer) -> dict[str, Any]:
    """Check, verify, install, and restart automatically once per process."""
    with UPDATE_LOCK:
        if UPDATE_STATE["phase"] != "idle":
            return dict(UPDATE_STATE)
        UPDATE_STATE.update(phase="checking", progress=3, message="Проверяем обновления лаунчера…", blocking=True)

    def run() -> None:
        settings = read_settings(load_config())
        checked = check_for_update(settings, LAUNCHER_VERSION)
        if not checked.get("enabled"):
            set_update_status(phase="disabled", progress=100, message=checked["message"], blocking=False)
            return
        if not checked.get("available"):
            set_update_status(
                phase="up_to_date", progress=100, message=checked["message"], blocking=False,
                current_version=checked.get("current_version"), latest_version=checked.get("latest_version"),
            )
            return

        set_update_status(phase="downloading", progress=8, message="Готовим обновление…", blocking=True, latest_version=checked.get("latest_version"))

        def progress(value: int, message: str) -> None:
            set_update_status(phase="downloading", progress=value, message=message, blocking=True)

        staged = stage_update(settings, LAUNCHER_VERSION, UPDATES_DIR, progress)
        if not staged.get("staged"):
            set_update_status(phase="failed", progress=100, message=staged.get("message", "Не удалось подготовить обновление."), blocking=False)
            return
        try:
            set_update_status(phase="installing", progress=98, message="Устанавливаем обновление…", blocking=True)
            begin_replacement()
            set_update_status(phase="restarting", progress=100, message="Обновление установлено. Перезапускаем лаунчер…", blocking=True)
            threading.Timer(0.45, server.shutdown).start()
        except (OSError, ValueError, json.JSONDecodeError) as error:
            set_update_status(phase="failed", progress=100, message=f"Не удалось установить обновление: {error}.", blocking=False)

    threading.Thread(target=run, daemon=True, name="launcher-forced-update").start()
    return update_status()


def main() -> int:
    no_browser = "--no-browser" in sys.argv[1:]
    if not (HERE / "dist" / "client" / "index.html").is_file():
        print("Сначала выполните: pnpm run build", file=sys.stderr)
        return 1
    find_game()  # Validate any cached directory and refresh it once per launcher start.
    server = ThreadingHTTPServer((HOST, PORT), LauncherHandler)
    url = f"http://{HOST}:{PORT}"
    print(f"Лаунчер доступен по адресу {url}")
    if not no_browser:
        webbrowser.open(url)
    start_forced_update(server)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

