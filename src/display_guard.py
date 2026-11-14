"""Display Layout Guard.

Keeps physical display resolution and position stable while a watched desktop-suite
process is running. Standard library only; no administrator rights required.
"""

import ctypes
import json
import os
import struct
import sys
import time
from ctypes import wintypes

MUTEX_NAME = "Local\\DisplayLayoutGuard"
DEFAULT_CONFIG = {
    "watch_process": "example-suite.exe",
    "virtual_id_prefix": "",
    "poll_seconds": 0.4,
    "log_max_bytes": 2 * 1024 * 1024,
}

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)


class DISPLAY_DEVICEW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("DeviceName", wintypes.WCHAR * 32),
        ("DeviceString", wintypes.WCHAR * 128),
        ("StateFlags", wintypes.DWORD),
        ("DeviceID", wintypes.WCHAR * 128),
        ("DeviceKey", wintypes.WCHAR * 128),
    ]


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


def base_dir():
    root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    path = os.path.join(root, "DisplayLayoutGuard")
    os.makedirs(path, exist_ok=True)
    return path


BASE = base_dir()
CONFIG_PATH = os.path.join(BASE, "config.json")
LOG_PATH = os.path.join(BASE, "display_guard.log")


def load_config():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8") as handle:
            json.dump(DEFAULT_CONFIG, handle, indent=2)
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return dict(DEFAULT_CONFIG)
    merged = dict(DEFAULT_CONFIG)
    merged.update({k: data[k] for k in DEFAULT_CONFIG if k in data})
    return merged


CONFIG = load_config()


def rotate_log():
    try:
        limit = int(CONFIG["log_max_bytes"])
        if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > limit:
            backup = LOG_PATH + ".1"
            if os.path.exists(backup):
                os.remove(backup)
            os.rename(LOG_PATH, backup)
    except Exception:
        pass


def log(message):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as handle:
            handle.write(time.strftime("%Y-%m-%d %H:%M:%S ") + message + "\n")
    except Exception:
        pass


_device = DISPLAY_DEVICEW()
_monitor = DISPLAY_DEVICEW()
_entry = PROCESSENTRY32W()
_mode_buffer = ctypes.create_string_buffer(0x200)


def attached_displays():
    """Return [(device_name, device_id)] for displays attached to the desktop."""
    result = []
    index = 0
    while index < 32:
        _device.cb = ctypes.sizeof(DISPLAY_DEVICEW)
        if not user32.EnumDisplayDevicesW(None, index, ctypes.byref(_device), 0):
            break
        name = _device.DeviceName
        if _device.StateFlags & 0x1:
            _monitor.cb = ctypes.sizeof(DISPLAY_DEVICEW)
            device_id = ""
            if user32.EnumDisplayDevicesW(name, 0, ctypes.byref(_monitor), 0):
                device_id = _monitor.DeviceID
            result.append((name, device_id))
        index += 1
    return result


def read_mode(device):
    """Return (width, height, x, y, raw_devmode) or None."""
    if not user32.EnumDisplaySettingsW(device, 0xFFFFFFFF, _mode_buffer):
        return None
    raw = bytes(_mode_buffer)
    width = struct.unpack_from("<I", raw, 0xAC)[0]
    height = struct.unpack_from("<I", raw, 0xB0)[0]
    x = struct.unpack_from("<i", raw, 0x4C)[0]
    y = struct.unpack_from("<i", raw, 0x50)[0]
    return width, height, x, y, raw


def watched_process_running():
    target = str(CONFIG["watch_process"]).lower()
    if not target:
        return False
    snapshot = kernel32.CreateToolhelp32Snapshot(0x2, 0)
    if snapshot in (0, -1, 0xFFFFFFFFFFFFFFFF):
        return False
    found = False
    try:
        _entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        more = kernel32.Process32FirstW(snapshot, ctypes.byref(_entry))
        while more:
            if _entry.szExeFile.lower() == target:
                found = True
                break
            more = kernel32.Process32NextW(snapshot, ctypes.byref(_entry))
    finally:
        kernel32.CloseHandle(snapshot)
    return found


def is_virtual(device_id):
    prefix = str(CONFIG["virtual_id_prefix"] or "").strip()
    return bool(prefix) and prefix.lower() in (device_id or "").lower()


def restore(device, raw_devmode):
    return user32.ChangeDisplaySettingsExW(device, raw_devmode, None, 0, None)


def run():
    log("guard started pid=%d" % os.getpid())
    baseline = {}
    watching = False
    previous = None
    tick = 0
    while True:
        try:
            tick += 1
            if tick % 250 == 0:
                rotate_log()
            if tick == 1 or tick % 3 == 0:
                watching = watched_process_running()
                if watching != previous:
                    log("watch %s" % ("detected" if watching else "exited"))
                    previous = watching
            displays = attached_displays()
            if not watching:
                alive = {name for name, _ in displays}
                for stale in [k for k in baseline if k not in alive]:
                    del baseline[stale]
                for name, device_id in displays:
                    mode = read_mode(name)
                    if mode:
                        baseline[name] = (mode[0], mode[1], mode[2], mode[3], mode[4], device_id)
            else:
                for name, device_id in displays:
                    if is_virtual(device_id):
                        continue
                    wanted = baseline.get(name)
                    if not wanted:
                        continue
                    current = read_mode(name)
                    if not current:
                        continue
                    if (current[0], current[1], current[2], current[3]) != wanted[:4]:
                        code = restore(name, wanted[4])
                        log(
                            "restore %s want=%dx%d@%d,%d current=%dx%d@%d,%d ret=%d"
                            % (name, wanted[0], wanted[1], wanted[2], wanted[3],
                               current[0], current[1], current[2], current[3], code)
                        )
            time.sleep(float(CONFIG["poll_seconds"]))
        except Exception as error:
            log("error %r" % (error,))
            time.sleep(1)


def list_displays():
    for name, device_id in attached_displays():
        mode = read_mode(name)
        if mode:
            print("%-14s %dx%d@%d,%d  %s" % (name, mode[0], mode[1], mode[2], mode[3], device_id))
        else:
            print("%-14s (no active mode)  %s" % (name, device_id))


def main():
    if "--list" in sys.argv:
        list_displays()
        return 0
    kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if kernel32.GetLastError() == 183:
        return 0
    try:
        run()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
