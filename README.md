# Atomic

A Windows desktop application that manages your environment during focus sessions — hiding distractions, opening productive tools, and making good habits the path of least resistance.

Built in Python. Inspired by *Atomic Habits* by James Clear.

---

## What It Does

When a focus session starts, Atomic:
- **Hides shortcuts** to distraction apps (Steam, Battle.net, etc.) from your desktop and taskbar
- **Opens your productive tools** (IDE, browser pointed at a learning resource) at their saved screen positions
- **Intercepts** any attempt to launch a blocked app and asks you for a reason before allowing it
- **Logs** every override with a timestamp and reason so you can see your habits honestly over time

When the session ends, everything is restored exactly as it was.

Atomic does not block or restrict. It raises the cost of distraction just enough to break the automatic reflex — you are always in control.

---

## Features

- Schedule-based focus sessions (configured per day of week)
- Manual session start/stop from the system tray
- Configurable distraction app list
- Configurable productive app list with saved window layouts
- Friction popup with required reason input and override logging
- SQLite-backed session and override history
- JSON config — editable via UI or directly in a text editor
- Runs quietly in the system tray; starts automatically on Windows login
- Sleep/wake aware — sessions pause on sleep and resume correctly on wake

---

## Tech Stack

| Concern | Tool |
|---|---|
| Language | Python 3.11+ |
| UI | PyQt6 |
| System tray | pystray |
| Config file watching | watchdog |
| Process monitoring | psutil |
| Sleep/wake detection | Windows API (`WM_POWERBROADCAST`) |
| Storage | SQLite + JSON |
| Tests | pytest |

---

## Project Structure

```
atomic/
├── main.py
├── config/
├── session/
├── shortcuts/
├── launcher/
├── friction/
├── logging/
├── tray/
├── ui/
└── tests/
    ├── unit/
    ├── integration/
    └── manual/
```

See the [Technical Design Document](docs/TDD.md) for full architecture details.

---

## Getting Started

### Prerequisites
- Windows 10 or 11
- Python 3.11+

### Installation

```bash
git clone https://github.com/maxwellcurtis/atomic.git
cd atomic
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

On first run, Atomic creates `%APPDATA%\Atomic\` with a default `config.json` and an empty database. Open the settings window from the system tray to configure your distraction apps, productive apps, and schedule.

---

## Configuration

All settings are configurable through the UI. For power users, `config.json` can be edited directly — click **Open Config File** in the settings window or navigate to `%APPDATA%\Atomic\config.json`.

See [docs/config-schema.md](docs/config-schema.md) for the full config structure.

---

## Running Tests

```bash
pytest tests/unit/         # Run after every coding session
pytest tests/integration/  # Run at the end of each milestone
```

Manual OS-level tests are documented in [tests/manual/manual_test_checklist.md](tests/manual/manual_test_checklist.md).

---

## Roadmap

| Version | Focus |
|---|---|
| V1 (current) | Windows MVP — core session, shortcut, friction, and logging features |
| V2 | Ubuntu Linux port, browser friction, log viewer and data export |
| V3 | Native Android app |

---

## Author

Maxwell Curtis
