# Display Layout Guard

Keeps your monitor layout stable while third-party desktop suites are running.

Desktop management suites (PC Manager style applications) reconfigure displays when they
start a multi-screen session: they change a monitor's resolution or move it to another
position in the virtual desktop. The result is that your external monitor ends up at the
resolution the suite picked, and your carefully arranged layout is gone.

This tool records the layout you configured while no session is active, and restores it
whenever a watched suite changes it.

## What it does

- Learns the layout of every physical display while the watched process is not running.
- Freezes that snapshot as the desired baseline once the watched process appears.
- Re-checks every 400 ms and writes back any physical display whose resolution or position changed.
- Ignores virtual/indirect displays, so screen-sharing and extended-screen sessions keep working.
- Logs every restore with wanted value, actual value and return code.

## What it does not do

- It does not modify any application, driver or system file.
- It does not require administrator rights.
- It does not hook or intercept APIs. It observes and rewrites display settings through documented Win32 calls.

## Works well with PC Manager style suites

Specifically useful when a desktop suite offers an extended-screen or second-screen feature
and you also have a physical external monitor attached: the suite tends to normalise both
displays to the resolution of the remote device. The guard keeps the external monitor at
the resolution and position you chose, while leaving the session itself untouched.

See [docs/desktop-suite-integration.md](docs/desktop-suite-integration.md) for the two settings
that matter: the watched process name and the virtual display prefix.

## Requirements

- Windows 10 or 11
- Python 3.9+ (CPython, 64-bit)

## Install

```bat
src\install.cmd
```

Copies the guard into `%LOCALAPPDATA%\DisplayLayoutGuard`, registers a per-user autostart
entry under `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, and starts it immediately.
No administrator rights and no Startup-folder write are required.

## Uninstall

```bat
src\uninstall.cmd
```

## Configuration

`%LOCALAPPDATA%\DisplayLayoutGuard\config.json` is created on first run:

```json
{
  "watch_process": "example-suite.exe",
  "virtual_id_prefix": "",
  "poll_seconds": 0.4,
  "log_max_bytes": 2097152
}
```

| Key | Meaning |
| --- | --- |
| `watch_process` | executable name whose lifetime defines the guard window |
| `virtual_id_prefix` | DeviceID prefix of displays that must never be guarded; empty means every attached display counts as physical |
| `poll_seconds` | polling interval |
| `log_max_bytes` | log rotation threshold |

## Logs

`%LOCALAPPDATA%\DisplayLayoutGuard\display_guard.log`, rotated to `.1` when it exceeds the limit.

## How it works

See [docs/display-lock.md](docs/display-lock.md).

## Scope

Use it on machines you own or administer. See [docs/scope.md](docs/scope.md).

## License

MIT
