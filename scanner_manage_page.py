import glob
import json
import os
import re
import shutil
import sys

from PyQt5.QtCore import QCoreApplication

import basic_def
from scanner_add_page import normalize_scanner

try:
    import winreg
except Exception:
    winreg = None

try:
    import win32com.client
except Exception:
    win32com = None


def _normalize_path(value):
    raw = str(value or "").strip().strip('"')
    if not raw:
        return ""
    if raw.lower().startswith(("steam://", "http://", "https://")):
        return raw.lower()
    return os.path.normcase(os.path.normpath(raw))


def _safe_name(value):
    text = str(value or "").strip() or "unnamed"
    text = re.sub(r"[\\/:*?\"<>|]+", "_", text)
    return text[:140].strip() or "unnamed"


def _is_hidden(path):
    name = os.path.basename(path).strip()
    return bool(name.startswith("."))


def _load_ignored_targets():
    try:
        basic_def.load_config()
    except Exception:
        pass

    raw = basic_def.config.get("Settings", "ignored_apps", fallback="[]")
    try:
        ignored = json.loads(raw)
    except Exception:
        ignored = []

    targets = set()
    for item in ignored if isinstance(ignored, list) else []:
        target = _normalize_path((item or {}).get("path"))
        if target:
            targets.add(target)
    return targets


def _is_ignored(target, ignored_targets):
    normalized = _normalize_path(target)
    return bool(normalized and normalized in ignored_targets)


def _get_work_folder():
    try:
        basic_def.load_config()
    except Exception:
        pass

    work_folder = getattr(basic_def, "folder", "") or getattr(basic_def, "folder_selected", "")
    work_folder = str(work_folder or "").strip()
    if not work_folder:
        work_folder = os.path.realpath(os.path.join(os.path.dirname(sys.executable), "appfolder"))

    os.makedirs(work_folder, exist_ok=True)
    return work_folder


def _write_url_shortcut(path, url):
    content = "[InternetShortcut]\nURL=" + url + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _create_lnk(shortcut_path, target_path, arguments="", working_dir="", icon_location=""):
    if win32com is None:
        raise RuntimeError("win32com is unavailable")
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.TargetPath = target_path
    if arguments:
        shortcut.Arguments = arguments
    if working_dir:
        shortcut.WorkingDirectory = working_dir
    if icon_location:
        shortcut.IconLocation = icon_location
    shortcut.save()


def _detect_steam_root():
    candidates = []

    if winreg is not None:
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
            steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
            if steam_path:
                candidates.append(steam_path)
        except Exception:
            pass

    env_x86 = os.environ.get("PROGRAMFILES(X86)")
    if env_x86:
        candidates.append(os.path.join(env_x86, "Steam"))
    env_pf = os.environ.get("PROGRAMFILES")
    if env_pf:
        candidates.append(os.path.join(env_pf, "Steam"))

    for item in candidates:
        if item and os.path.exists(item):
            return os.path.normpath(item)
    return ""


def _steam_library_paths(steam_root):
    roots = []
    if not steam_root:
        return roots

    steamapps_main = os.path.join(steam_root, "steamapps")
    if os.path.isdir(steamapps_main):
        roots.append(steamapps_main)

    library_vdf = os.path.join(steamapps_main, "libraryfolders.vdf")
    if os.path.exists(library_vdf):
        try:
            with open(library_vdf, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            for raw_path in re.findall(r'"path"\s+"([^"]+)"', text):
                p = raw_path.replace("\\\\", "\\")
                steamapps_path = os.path.join(p, "steamapps")
                if os.path.isdir(steamapps_path):
                    roots.append(steamapps_path)
        except Exception:
            pass

    unique = []
    seen = set()
    for p in roots:
        norm = _normalize_path(p)
        if norm and norm not in seen:
            seen.add(norm)
            unique.append(p)
    return unique


def _parse_steam_name(acf_path):
    try:
        with open(acf_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception:
        return ""

    m = re.search(r'"name"\s+"([^"]+)"', text)
    return m.group(1).strip() if m else ""


def _scan_steam(scanner, work_folder, ignored_targets, progress_cb, dry_run=False):
    source = str(scanner.get("source", "")).strip()
    steam_root = source or _detect_steam_root()
    if not steam_root or not os.path.isdir(steam_root):
        return 0, 0, 1, QCoreApplication.translate("ScannerManagePage", "Steam 根路径未找到")

    steamapps_dirs = _steam_library_paths(steam_root)
    if not steamapps_dirs:
        return 0, 0, 1, QCoreApplication.translate("ScannerManagePage", "Steam 库未找到")

    created = skipped = errors = 0
    scanner_name = scanner.get("name") or "Steam"

    for steamapps in steamapps_dirs:
        manifests = glob.glob(os.path.join(steamapps, "appmanifest_*.acf"))
        for manifest in manifests:
            appid_match = re.search(r"appmanifest_(\d+)\.acf$", manifest, flags=re.IGNORECASE)
            if not appid_match:
                continue

            appid = appid_match.group(1)
            app_name = _parse_steam_name(manifest) or f"SteamApp {appid}"
            run_url = f"steam://rungameid/{appid}"

            if _is_ignored(run_url, ignored_targets):
                skipped += 1
                continue

            try:
                # base name is just the app name (no scanner prefix)
                base_name = app_name
                out_path = os.path.join(work_folder, f"{_safe_name(base_name)}.url") if work_folder else ""
                if out_path and os.path.exists(out_path):
                    skipped += 1
                    continue

                if not dry_run:
                    _write_url_shortcut(out_path, run_url)
                created += 1
                # dry-run 消息附带目标路径，供调用方用于忽略列表
                msg = (f"[{scanner_name}] found: {app_name}\t{run_url}"
                       if dry_run else f"[{scanner_name}] added: {app_name}")
                progress_cb(msg)
            except Exception as e:
                errors += 1
                progress_cb(f"[{scanner_name}] failed: {app_name} ({e})")

    return created, skipped, errors, QCoreApplication.translate("ScannerManagePage", "Steam 扫描已完成")


def _get_epic_manifest_dirs(source):
    dirs = []
    if source:
        dirs.append(source)
    else:
        program_data = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
        dirs.append(os.path.join(program_data, "Epic", "EpicGamesLauncher", "Data", "Manifests"))
    return [d for d in dirs if d and os.path.isdir(d)]


def _scan_epic(scanner, work_folder, ignored_targets, progress_cb, dry_run=False):
    source = str(scanner.get("source", "")).strip()
    manifest_dirs = _get_epic_manifest_dirs(source)
    if not manifest_dirs:
        return 0, 0, 1, QCoreApplication.translate("ScannerManagePage", "Epic 清单目录未找到")

    created = skipped = errors = 0
    scanner_name = scanner.get("name") or "Epic"

    for manifest_dir in manifest_dirs:
        for path in glob.glob(os.path.join(manifest_dir, "*.item")):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    data = json.load(f)
            except Exception:
                errors += 1
                continue

            app_name = data.get("DisplayName") or data.get("AppName") or os.path.splitext(os.path.basename(path))[0]
            launch = str(data.get("LaunchExecutable") or data.get("Executable") or "").strip()
            install = str(data.get("InstallLocation") or "").strip()

            exe_path = launch
            if exe_path and not os.path.isabs(exe_path) and install:
                exe_path = os.path.join(install, exe_path)
            exe_path = os.path.normpath(exe_path) if exe_path else ""

            if not exe_path:
                skipped += 1
                continue
            if _is_ignored(exe_path, ignored_targets):
                skipped += 1
                continue

            try:
                # use app_name directly and skip if target exists
                out_path = os.path.join(work_folder, f"{_safe_name(app_name)}.lnk") if work_folder else ""
                if out_path and os.path.exists(out_path):
                    skipped += 1
                    continue

                if not dry_run:
                    _create_lnk(
                        out_path,
                        target_path=exe_path,
                        working_dir=os.path.dirname(exe_path) if os.path.isabs(exe_path) else "",
                        icon_location=exe_path,
                    )
                created += 1
                msg = (f"[{scanner_name}] found: {app_name}\t{exe_path}"
                       if dry_run else f"[{scanner_name}] added: {app_name}")
                progress_cb(msg)
            except Exception as e:
                errors += 1
                progress_cb(f"[{scanner_name}] failed: {app_name} ({e})")

    return created, skipped, errors, QCoreApplication.translate("ScannerManagePage", "Epic 扫描已完成")


def _iter_files(source, recursive):
    if recursive:
        for root, _, files in os.walk(source):
            for name in files:
                yield os.path.join(root, name)
    else:
        for name in os.listdir(source):
            p = os.path.join(source, name)
            if os.path.isfile(p):
                yield p


def _scan_custom(scanner, work_folder, ignored_targets, progress_cb, dry_run=False):
    source = str(scanner.get("source", "")).strip()
    if not source or not os.path.isdir(source):
        return 0, 0, 1, "Custom source folder not found"

    recursive = bool(scanner.get("recursive", True))
    include_hidden = bool(scanner.get("include_hidden", False))
    scanner_name = scanner.get("name") or "Custom"

    created = skipped = errors = 0
    for src in _iter_files(source, recursive):
        if not include_hidden and _is_hidden(src):
            continue

        ext = os.path.splitext(src)[1].lower()
        if ext not in (".exe", ".lnk", ".url"):
            continue

        if _is_ignored(src, ignored_targets):
            skipped += 1
            continue

        app_name = os.path.splitext(os.path.basename(src))[0]
        try:
            base_name = app_name
            if ext == ".exe":
                out_path = os.path.join(work_folder, f"{_safe_name(base_name)}.lnk") if work_folder else ""
                if out_path and os.path.exists(out_path):
                    skipped += 1
                    continue
                if not dry_run:
                    _create_lnk(
                        out_path,
                        target_path=src,
                        working_dir=os.path.dirname(src),
                        icon_location=src,
                    )
            else:
                out_path = os.path.join(work_folder, f"{_safe_name(base_name)}{ext}") if work_folder else ""
                if out_path and os.path.exists(out_path):
                    skipped += 1
                    continue
                if not dry_run:
                    shutil.copy2(src, out_path)
            created += 1
            msg = (f"[{scanner_name}] found: {app_name}\t{src}"
                   if dry_run else f"[{scanner_name}] added: {app_name}")
            progress_cb(msg)
        except Exception as e:
            errors += 1
            progress_cb(f"[{scanner_name}] failed: {app_name} ({e})")

    return created, skipped, errors, QCoreApplication.translate("ScannerManagePage", "自定义扫描已完成")


def _parse_rom_extensions(value):
    text = str(value or "").strip()
    if not text:
        text = ".zip,.7z,.iso,.cue,.chd"
    exts = set()
    for part in text.split(","):
        ext = part.strip().lower()
        if not ext:
            continue
        if not ext.startswith("."):
            ext = "." + ext
        exts.add(ext)
    return exts


def _scan_rom(scanner, work_folder, ignored_targets, progress_cb, dry_run=False):
    source = str(scanner.get("source", "")).strip()
    emulator = str(scanner.get("emulator_path", "")).strip()
    if not source or not os.path.isdir(source):
        return 0, 0, 1, "ROM source folder not found"
    if not emulator:
        return 0, 0, 1, "ROM emulator path is empty"

    recursive = bool(scanner.get("recursive", True))
    include_hidden = bool(scanner.get("include_hidden", False))
    args_tpl = str(scanner.get("emulator_args", "{rom}")).strip() or "{rom}"
    exts = _parse_rom_extensions(scanner.get("rom_extensions", ""))
    scanner_name = scanner.get("name") or "ROM"

    created = skipped = errors = 0
    for src in _iter_files(source, recursive):
        if not include_hidden and _is_hidden(src):
            continue
        if os.path.splitext(src)[1].lower() not in exts:
            continue
        if _is_ignored(src, ignored_targets):
            skipped += 1
            continue

        rom_name = os.path.splitext(os.path.basename(src))[0]
        try:
            quoted_rom = f'"{src}"'
            arguments = args_tpl.replace("{rom}", quoted_rom)
            if "{rom}" not in args_tpl:
                arguments = (args_tpl + " " + quoted_rom).strip()

            base_name = rom_name
            out_path = os.path.join(work_folder, f"{_safe_name(base_name)}.lnk") if work_folder else ""
            if out_path and os.path.exists(out_path):
                skipped += 1
                continue

            if not dry_run:
                _create_lnk(
                    out_path,
                    target_path=emulator,
                    arguments=arguments,
                    working_dir=os.path.dirname(emulator),
                    icon_location=emulator,
                )
            created += 1
            msg = (f"[{scanner_name}] found: {rom_name}\t{src}"
                   if dry_run else f"[{scanner_name}] added: {rom_name}")
            progress_cb(msg)
        except Exception as e:
            errors += 1
            progress_cb(f"[{scanner_name}] failed: {rom_name} ({e})")

    return created, skipped, errors, QCoreApplication.translate("ScannerManagePage", "ROM 扫描已完成")


def run_scanner(scanner, work_folder, ignored_targets, progress_cb=lambda _msg: None, dry_run=False):
    s = normalize_scanner(scanner)
    scanner_type = s.get("type", "custom")

    if scanner_type == "steam":
        return _scan_steam(s, work_folder, ignored_targets, progress_cb, dry_run=dry_run)
    if scanner_type == "epic":
        return _scan_epic(s, work_folder, ignored_targets, progress_cb, dry_run=dry_run)
    if scanner_type == "rom":
        return _scan_rom(s, work_folder, ignored_targets, progress_cb, dry_run=dry_run)
    return _scan_custom(s, work_folder, ignored_targets, progress_cb, dry_run=dry_run)
