# AGENTS.md

Operational contract for automated agents working in this repository.

## Layout

```
src/display_guard.py             guard implementation, stdlib only
src/install.ps1                  idempotent installer
src/uninstall.ps1                idempotent remover
docs/display-lock.md             how the guard observes and restores layouts
docs/desktop-suite-integration.md  configuring watched process and virtual display prefix
docs/scope.md                    allowed use
```

## Conventions

- Python standard library only. Do not add dependencies.
- Never write outside `%LOCALAPPDATA%\DisplayLayoutGuard` and the current user's Startup folder.
- Every script must be idempotent: running it twice must not create duplicates or errors.
- Log lines are one event per line, prefixed with a timestamp.
- Keep all repository text free of vendor names, product names, file hashes and memory offsets.
- This project adapts to desktop suites by observing display settings, never by modifying their files.

## Commands

```bat
:: install or repair
powershell -NoProfile -ExecutionPolicy Bypass -File src\install.ps1

:: verify
powershell -NoProfile -ExecutionPolicy Bypass -File src\install.ps1 -Verify

:: remove
powershell -NoProfile -ExecutionPolicy Bypass -File src\uninstall.ps1
```

## Verification checklist

1. `Get-Process pythonw` shows exactly one guard process.
2. `%LOCALAPPDATA%\DisplayLayoutGuard\display_guard.log` contains a `guard started` line.
3. Starting the watched process writes `watch detected`, exiting writes `watch exited`.
4. Changing a display's resolution while the watched process runs produces a `restore` line and the layout returns.
5. Running the installer twice leaves one launcher and one process.

## Failure handling

- Guard refuses to start: another instance holds the single-instance mutex; terminate the stale process.
- No `restore` line appears: the changed display was classified as virtual. Adjust `virtual_id_prefix` in `config.json`.
- Restore returns a non-zero code: the driver rejected the mode; capture the code from the log before changing anything.

## Prohibited

- Do not add binaries, installers or vendor payloads.
- Do not add instructions for modifying third-party software files.
- Do not weaken the single-instance, logging or rollback behaviour.
