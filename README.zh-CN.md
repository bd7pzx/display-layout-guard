# Display Layout Guard（显示器布局守护）

在桌面管理套件运行时，保持你的显示器布局不被改动。

电脑管家类的桌面套件在开启多屏协同、扩展屏会话时，会重新配置显示器：把某块屏改成远端设备的分辨率，
或者把它挪到虚拟桌面的另一个位置。结果就是外接显示器被设成套件选定的分辨率，你原本排好的布局消失。

本工具在**没有会话时**记录你设定的布局，在受监视进程启动后把它冻结为基准，一旦被改动就写回。

## 它做什么

- 受监视进程不在运行时，持续记录每块物理显示器的分辨率与位置。
- 受监视进程出现时，把当时的布局冻结为期望基准。
- 每 400 毫秒复核一次，发现物理显示器的分辨率或位置变化就写回。
- 按 DeviceID 前缀排除虚拟显示器，保证扩展屏/投屏会话本身不受影响。
- 每次恢复都记日志，包含期望值、实际值和返回码。

## 它不做什么

- 不修改任何应用程序、驱动或系统文件。
- 不需要管理员权限。
- 不做 API Hook 或注入，只通过公开的 Win32 接口读取和写回显示设置。

## 与电脑管家类套件配合

典型场景：套件提供扩展屏/第二屏功能，同时你接着一台物理外接显示器。套件启动会话时会把两块屏都归一化到远端设备的分辨率。
本工具让外接显示器保持你设定的分辨率和位置，会话本身照常工作。

需要填的只有两项，见 [docs/desktop-suite-integration.md](docs/desktop-suite-integration.md)：受监视进程名、虚拟屏 DeviceID 前缀。

## 环境要求

- Windows 10 / 11
- Python 3.9+（CPython，64 位）

## 安装

```bat
src\install.cmd
```

安装脚本会把守护复制到 `%LOCALAPPDATA%\DisplayLayoutGuard`，在
`HKCU\Software\Microsoft\Windows\CurrentVersion\Run` 写入当前用户自启项，并立即启动。
无需管理员权限，也不依赖启动文件夹写入权限。

## 卸载

```bat
src\uninstall.cmd
```

加 `-Purge` 连同配置和日志一起删除。

## 配置

首次运行会在 `%LOCALAPPDATA%\DisplayLayoutGuard\config.json` 生成配置：

```json
{
  "watch_process": "example-suite.exe",
  "virtual_id_prefix": "",
  "poll_seconds": 0.4,
  "log_max_bytes": 2097152
}
```

| 键 | 含义 |
| --- | --- |
| `watch_process` | 定义守护窗口的进程名，只有会话期间才存在的那个组件 |
| `virtual_id_prefix` | 虚拟显示器 DeviceID 前缀，命中则不参与守护；为空表示所有已连接显示器都按物理屏处理 |
| `poll_seconds` | 轮询间隔 |
| `log_max_bytes` | 日志轮转阈值 |

## 查看显示器信息

```powershell
python src\display_guard.py --list
```

输出每块屏的设备名、当前分辨率与位置、显示器 DeviceID，用来填上面两个配置。

## 日志

`%LOCALAPPDATA%\DisplayLayoutGuard\display_guard.log`，超过阈值轮转为 `.1`。

守护期间典型记录：

```
2026-01-01 12:00:00 watch detected
2026-01-01 12:00:03 restore \\.\DISPLAY2 want=2560x1440@1920,0 current=1920x1200@1920,0 ret=0
```

`ret=0` 表示驱动接受了写回；非 0 是 `ChangeDisplaySettingsExW` 的返回码，先记录再改动。

## 工作原理

见 [docs/display-lock.md](docs/display-lock.md)。

## 适用范围

仅用于你拥有或负责管理的机器。见 [docs/scope.md](docs/scope.md)。

## 许可证

MIT
