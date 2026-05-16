# my-crosshair

A lightweight, always-on-top gaming crosshair overlay for Windows. The window is centered on screen, click-through, and configurable via JSON.

## Requirements

- Windows 10/11
- Python 3.10+ (stdlib only — no pip packages required)

## Quick start

```powershell
# Recommended on Windows (no PowerShell script policy required)
.\run.bat

# Or run Python directly
python -m src.overlay
```

If `.\run.ps1` fails with *running scripts is disabled*, use `run.bat` above, or run once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### Stop the overlay

| Method | How |
|--------|-----|
| **Hotkey** | **Ctrl+Shift+X** (works even while gaming — global hotkey) |
| **Terminal** | Focus the terminal where you started it, then **Ctrl+C** |
| **Task Manager** | End the `python` process if the above are unavailable |

## Configuration

Edit `config/default.json`:

| Key | Description | Default |
|-----|-------------|---------|
| `style` | `cross`, `dot`, or `circle` | `cross` |
| `color` | Hex color | `#00ff00` |
| `size` | Half-size of overlay canvas (px) | `24` |
| `thickness` | Line width (px) | `2` |
| `gap` | Center gap for cross style (px) | `6` |
| `dot` | Show center dot on cross style | `true` |
| `opacity` | Window opacity `0.0`–`1.0` | `0.9` |
| `follow_mouse` | Move crosshair with cursor | `true` |
| `poll_ms` | Cursor poll interval in ms (`1`–`16`, lower = snappier) | `8` |

For personal settings without committing them, copy to `config/local.json` (gitignored).

## Git

```powershell
git status
git pull
git push
```

## License

MIT — see [LICENSE](LICENSE).
