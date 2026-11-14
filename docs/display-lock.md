# How the guard works

## Model

Windows exposes the current display configuration through a small set of documented calls:

| Call | Purpose |
| --- | --- |
| `EnumDisplayDevicesW(NULL, i, ...)` | enumerate adapters attached to the desktop |
| `EnumDisplayDevicesW(adapter, 0, ...)` | read the monitor attached to an adapter, including its `DeviceID` |
| `EnumDisplaySettingsW(device, ENUM_CURRENT_SETTINGS, ...)` | read the active `DEVMODEW` for that device |
| `ChangeDisplaySettingsExW(device, devmode, NULL, 0, NULL)` | apply a `DEVMODEW` to one device |

The guard keeps the `DEVMODEW` blob of every physical display, because that blob carries both
the resolution (`dmPelsWidth`, `dmPelsHeight`) and the position (`dmPosition`) inside the
virtual desktop.

## State machine

```
watched process absent  -> learning
    every tick: overwrite baseline[name] with the current mode

watched process present -> guarding
    every tick: compare current mode with baseline
    on mismatch: ChangeDisplaySettingsExW(name, baseline blob)
```

Baselines are dropped for displays that disappear, so re-plugging a monitor does not
resurrect a stale entry.

## Why virtual displays are excluded

Screen-sharing and remote-desktop stacks create indirect displays. Those are part of the
session and are expected to change resolution while the session runs. Guarding them would
fight the session itself.

Classification is by `DeviceID` prefix, configured with `virtual_id_prefix`. Empty means
nothing is excluded, which is the safe default when you do not use such a stack.

## Timing

Default polling is 400 ms. A change is reverted within one or two ticks, which is visible
as a brief flicker when a suite reconfigures the layout on connect. Raising
`poll_seconds` reduces CPU proportionally and lengthens the flicker.

## Known limits

- A suite that re-applies its topology on a timer will cause repeated reverts. The log makes
  this obvious: consecutive `restore` lines for the same device.
- Some drivers reject a `DEVMODEW` that was captured before a topology change; the restore
  returns a non-zero code and the log records it.
- The guard restores mode and position, not DPI scaling or HDR state.

## Cost

Measured steady state: about 15 MB working set, 8 MB private, roughly 105 handles, one
thread, and around 1.2% of one core at the default 400 ms polling interval.
