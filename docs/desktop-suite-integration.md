# Integrating with desktop management suites

Desktop management suites provide an extended-screen feature that turns a tablet or a
second device into an extra display. When such a session starts, the suite often
normalises every attached display to the resolution of the remote device, and repositions
them. A physical external monitor is caught by that normalisation.

The guard does not change the suite or its files. It only enforces the layout you chose.

## Two settings

`%LOCALAPPDATA%\DisplayLayoutGuard\config.json`

```json
{
  "watch_process": "example-suite.exe",
  "virtual_id_prefix": "VIRTUAL-MONITOR-PREFIX",
  "poll_seconds": 0.4,
  "log_max_bytes": 2097152
}
```

### watch_process

The executable that exists only while the extended-screen session is active. It defines the
guard window: while it runs, the baseline is frozen. Use the process name of the suite's
screen component, not the main UI process, otherwise the baseline freezes whenever the UI is
open.

### virtual_id_prefix

The suite's virtual display reports a `DeviceID` starting with a vendor-specific prefix.
That display must be excluded, otherwise the guard reverts the session's own resolution.

To find it, list attached displays and look at each monitor's `DeviceID`:

```powershell
python src\display_guard.py --list
```

or, without running the guard, inspect the same data with any display enumeration tool and
copy the prefix of the virtual adapter's monitor entry.

## Recommended operating order

1. End any extended-screen session and wait for the watched process to exit.
2. Arrange displays the way you want them (resolution and position).
3. Wait about one second; the guard records the new baseline.
4. Start the session. The external monitor may flicker once, then returns to your layout.

Changing the layout while a session is running will be reverted, by design.

## Verifying

```powershell
Get-Content "$env:LOCALAPPDATA\DisplayLayoutGuard\display_guard.log" -Tail 20
```

Expected while a session is active:

```
2026-01-01 12:00:00 watch detected
2026-01-01 12:00:03 restore \\.\DISPLAY2 want=2560x1440@1920,0 current=1920x1200@1920,0 ret=0
```

`ret=0` means the driver accepted the restore. A non-zero `ret` is the Win32 result of
`ChangeDisplaySettingsExW` and should be recorded before changing anything.
