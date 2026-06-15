# Technical Design Document — Atomic
**Version:** 0.1 (Draft — Sections 1–3)
**Author:** Maxwell Curtis
**Date:** June 13, 2026
**Status:** In Progress

---

## 1. Problem Statement

When it is time to study or work on personal projects, the desktop environment works against the user rather than for them. Distraction applications (Steam, Battle.net, etc.) are immediately accessible, while productive tools require deliberate effort to open. The result is that a single reflexive click ends a focus session before it begins.

Atomic solves this by actively managing the desktop environment during focus sessions. It does not block or restrict — it raises the activation energy of distraction just enough to interrupt the reflex, while making productive tools the default open state. The goal is habit shaping through environmental design, not enforcement.

---

## 2. System Context

### Environment
- **Host OS (V1):** Windows 10/11
- **Runtime:** Python 3.11+
- **Deployment:** Single-user desktop application, installed and run locally

### External Touchpoints
Atomic interacts with the following systems outside its own process:

| Touchpoint            | Interaction                                    | Notes                                                                 |
|-----------------------|------------------------------------------------|-----------------------------------------------------------------------|
| Windows Desktop       | Read/move shortcut files (.lnk)                | Requires elevated permissions                                         |
| Windows Taskbar       | Read/move pinned shortcut files                | Same permission scope as desktop                                      |
| Windows Registry      | Write startup entry on install                 | Used to launch Atomic on login                                        |
| Windows Power API     | Subscribe to sleep/wake events                 | Via `WM_POWERBROADCAST` hook                                          |
| File System           | Read/write config.json, hidden shortcut folder | `%APPDATA%\Atomic\` — conventional Windows per-user app data location |
| SQLite Database       | Read/write session and override logs           | `%APPDATA%\Atomic\atomic.db`                                          |
| Third-party Processes | Monitor running processes via `psutil`         | Detect blocked app launches                                           |
| User Applications     | Launch and position productive apps            | IDE, browser, etc.                                                    |
| Browser               | Open to configured URL on session start        | Via `webbrowser` module or direct launch                              |

### What Atomic Does Not Touch
- Network traffic or DNS (no browser redirect in V1)
- Other user accounts on the same machine
- Any cloud service or remote endpoint
- Application internals — Atomic only monitors process names, it does not inject into or modify other applications

---

## 3. Architecture Overview

### Design Philosophy
Atomic is organized as **vertical feature slices** rather than horizontal layers (UI / logic / data). Each feature owns its own logic, UI components, and data access. This keeps related code co-located, reduces context switching when working on a single feature, and makes the codebase navigable for a solo developer returning after time away.

Horizontal layering (separating all UI from all logic from all data) is a coordination tool optimized for teams with clear ownership boundaries. For a single developer, it introduces navigation overhead without the benefit. Feature slices are the right tradeoff here.

### Top-Level Component Map

```
atomic/
├── main.py                  # Entry point — bootstraps all components
├── config/                  # Configuration management
│   ├── config_manager.py    # Load, validate, save config.json
│   └── default_config.json  # Template for first-run generation
├── session/                 # Focus session lifecycle
│   ├── session_engine.py    # Start/stop sessions, schedule management
│   └── session_model.py     # Session data model
├── shortcuts/               # Shortcut hide/restore
│   └── shortcut_engine.py   # Locate, move, restore .lnk files
├── launcher/                # Productive app launching
│   ├── app_launcher.py      # Open apps, position windows
│   └── layout_manager.py    # Save and restore window layouts
├── friction/                # Distraction interception
│   ├── process_monitor.py   # Watch for blocked app launches (psutil)
│   └── friction_dialog.py   # PyQt6 popup — reason input + override log
├── logging/                 # Session and override logging
│   ├── db_manager.py        # SQLite read/write
│   └── schema.sql           # Database schema definition
├── tray/                    # System tray + lifecycle
│   ├── tray_app.py          # pystray icon and menu
│   └── power_monitor.py     # Windows API sleep/wake hooks
└── ui/                      # Shared UI components
    ├── settings_window.py   # PyQt6 settings/configuration UI
    └── log_viewer.py        # Override log display
```

### Data Storage Locations

All runtime data is stored outside the application install folder, following Windows conventions for per-user application data:

```
%APPDATA%\Atomic\
    ├── config.json           # User configuration
    ├── atomic.db             # SQLite session and override logs
    └── hidden_shortcuts\     # Shortcut files moved here during focus sessions
            └── Steam.lnk     # (example)
```

App code lives in its install location (`Program Files\Atomic\` or equivalent). Mixing app code and user data in the same folder is an antipattern on Windows — `%APPDATA%` is the conventional, correct location for per-user runtime files. In Python, this path is resolved at runtime via `os.environ.get('APPDATA')`.

### Component Responsibilities

| Component         | Owns                                          | Communicates With                                                  |
|-------------------|-----------------------------------------------|--------------------------------------------------------------------|
| `session_engine`  | Session lifecycle, scheduling, state          | `shortcut_engine`, `app_launcher`, `process_monitor`, `db_manager` |
| `shortcut_engine` | Hide/restore .lnk files, track original paths | `config_manager` (reads distraction list)                          |
| `app_launcher`    | Launch productive apps, position windows      | `config_manager` (reads productive list + layout)                  |
| `process_monitor` | Poll for blocked processes, trigger friction  | `session_engine` (checks if session active), `friction_dialog`     |
| `friction_dialog` | Display popup, capture reason, allow override | `db_manager` (writes override log)                                 |
| `tray_app`        | System tray icon, menu actions, startup       | `session_engine` (start/stop), `settings_window` (open)            |
| `power_monitor`   | Windows sleep/wake events                     | `session_engine` (pause/resume)                                    |
| `config_manager`  | Load, validate, write config.json             | All components (read); `settings_window` (write via UI)            |
| `db_manager`      | SQLite session and override log               | `session_engine`, `friction_dialog`, `log_viewer`                  |
| `settings_window` | Configuration UI                              | `config_manager` (write on save)                                   |

### Thread Model

Atomic runs two threads:

**Thread 1 — Session Engine (background)**
Owns the session lifecycle, schedule polling, process monitoring, and all OS interactions. Reads `config.json` on startup and whenever `watchdog` detects a file change. This thread never touches the UI directly.

**Thread 2 — UI Thread (PyQt6 + pystray)**
Owns all user-facing windows and the system tray icon. Writes to `config.json` when the user saves settings. Never directly calls session engine functions — config file is the communication boundary.

**Communication boundary:** `config.json` watched by `watchdog`. UI writes → file changes → session engine reloads. Simple, reliable, no shared state between threads.

---

## 4. Component Breakdown

### `config_manager`
**Responsibility:** Single source of truth for all application configuration. Loads `config.json` from `%APPDATA%\Atomic\` on startup, validates structure, and exposes read/write methods to all other components. Generates a default config file on first run if none exists.

**Key behaviors:**
- On load: validates all required keys are present; fills missing optional keys with defaults rather than erroring
- On save: writes atomically (write to temp file, rename) to prevent corruption if the app crashes mid-write
- Exposes the resolved `%APPDATA%\Atomic\` path via a single helper so no other component hardcodes it
- `watchdog` integration lives here — raises an internal event when the file changes on disk so the session engine can reload without polling

**Implementation note:** `os.environ.get('APPDATA')` resolves the base path at runtime. Never hardcode a username or drive letter.

---

### `session_engine`
**Responsibility:** Owns the full lifecycle of a focus session — scheduled and manual. Knows whether a session is currently active and coordinates all other components when state changes.

**Key behaviors:**
- On session start: calls `shortcut_engine.hide()`, then `app_launcher.launch()`
- On session end: calls `shortcut_engine.restore()`, writes session close to DB
- Schedule manager: runs a lightweight loop checking current time against schedule entries in config; fires session start/end at the correct times
- On config reload (via `watchdog` event): re-reads schedule without restarting the engine
- Exposes `start_session(type)` and `stop_session()` as the public interface — all callers (tray, schedule) go through these

**State machine:**

```
IDLE → ACTIVE (on start)
ACTIVE → PAUSED (on sleep)
PAUSED → ACTIVE (on wake, if session time still valid)
ACTIVE → IDLE (on stop or session end time reached)
PAUSED → IDLE (on stop while paused)
```

---

### `shortcut_engine`
**Responsibility:** Locates `.lnk` shortcut files for configured distraction apps and moves them to the hidden folder during a session. Restores them exactly on session end.

**Key behaviors:**
- On hide: records original path of each shortcut in `config.json` before moving; moves file to `%APPDATA%\Atomic\hidden_shortcuts\`
- On restore: reads recorded original paths, moves files back; clears recorded paths on success
- Handles edge cases: shortcut not found (log and skip), already hidden (skip), permission denied (log error, surface to user)
- Searches Desktop (`%USERPROFILE%\Desktop`) and Taskbar pinned shortcuts (`%APPDATA%\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar`)

**Implementation note:** UAC elevation will likely be required for taskbar shortcuts. Elevation strategy to be confirmed during M1 research spike and documented here when resolved.

---

### `app_launcher`
**Responsibility:** Opens configured productive apps when a session starts and positions them on screen according to the saved layout.

**Key behaviors:**
- Reads productive app list from config: each entry has an executable path, optional launch URL (for browser), and optional saved window position/size
- Before launching: checks if the process is already running; if so, brings it to the foreground rather than opening a second instance
- After launching: waits briefly for the window to appear, then applies saved position and size via PyQt6 window management
- "Save current layout" function: iterates over all running productive app windows, records their current position, size, and screen index to config

**Window position data shape (per app):**
```json
{
  "x": 0,
  "y": 0,
  "width": 1920,
  "height": 1080,
  "screen": 0
}
```

---

### `process_monitor`
**Responsibility:** Watches for blocked applications being launched while a session is active and triggers the friction dialog before the app fully opens.

**Key behaviors:**
- Runs a polling loop using `psutil.process_iter()` on a configurable interval
- Only active during a session — idles completely when no session is running
- On detection: immediately suspends the target process, triggers `friction_dialog`; resumes or terminates based on user response
- Polling interval is user-configurable in `config.json` with a recommended default; a separate spec-detection utility suggests an appropriate default on first run

**Implementation note:** Suspending a process before the friction dialog appears (`psutil.Process.suspend()`) is the cleanest way to prevent the app from fully loading before the user responds. This requires elevated permissions and will be validated during M4.

---

### `friction_dialog`
**Responsibility:** Presents a modal always-on-top popup when a blocked app is intercepted. Captures a reason from the user and either allows or cancels the override.

**Key behaviors:**
- Receives the blocked app name from `process_monitor`
- Displays app name, a short message, a required reason text input, and Confirm / Cancel buttons
- Confirm: logs the override to SQLite (timestamp, app name, session ID, reason), resumes the suspended process
- Cancel: terminates the suspended process cleanly
- Window is modal and always-on-top — cannot be dismissed without making a choice

---

### `db_manager`
**Responsibility:** All reads and writes to `atomic.db`. No other component touches SQLite directly.

**Key behaviors:**
- Initializes schema on first run if tables do not exist
- Exposes simple methods: `log_session_start()`, `log_session_end()`, `log_override()`, `get_overrides(limit, offset)`, `get_sessions(limit, offset)`
- All writes wrapped in transactions — partial writes do not corrupt the log

---

### `power_monitor`
**Responsibility:** Hooks into the Windows power event system to detect when the machine is going to sleep and when it wakes.

**Key behaviors:**
- Registers for `WM_POWERBROADCAST` messages via the Windows API
- On sleep signal: calls `session_engine.pause()`
- On wake signal: calls `session_engine.resume()`
- Runs on the session engine thread — no UI involvement

**Implementation note:** This requires a hidden Windows message window (`HWND`) to receive broadcast messages. This is a standard pattern but involves `ctypes` and Win32 API calls. Will be the most platform-specific code in the project — comment thoroughly.

---

### `tray_app`
**Responsibility:** Manages the system tray icon and menu. Acts as the primary user-facing control surface when no settings window is open.

**Key behaviors:**
- Creates tray icon on startup using `pystray`; app starts with no visible window
- Menu items: Start Session, Stop Session, Open Settings, View Log, Quit
- Start/Stop: calls `session_engine.start_session()` / `session_engine.stop_session()`
- Open Settings: instantiates and shows `settings_window`
- Quit: triggers graceful shutdown — ensures session is ended and shortcuts are restored before exit
- Registers app in Windows Registry for startup on login (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`)

---

### `settings_window`
**Responsibility:** PyQt6 window for configuring all aspects of the app. The only component that writes to `config.json` via the UI path.

**Tabs:**
- **Distraction Apps** — add/remove apps with shortcut path picker
- **Productive Apps** — add/remove apps with executable path, optional URL, optional saved window position; "Save Current Layout" button
- **Schedule** — add/edit/delete time blocks per day of week
- **Performance** — polling interval setting with spec-aware default suggestion

**Key behaviors:**
- Loads current config on open
- All changes held in memory until Save is clicked
- On save: writes updated config to disk; `watchdog` on the session engine thread picks up the change automatically
- "Open config file" button opens `config.json` in the system default text editor for power users

---

## 5. Data Shapes

### 5.1 `config.json`

Full structure with example values:

```json
{
  "system": {
    "polling_interval_ms": 500
  },
  "distraction_apps": [
    {
      "name": "Steam",
      "process_name": "steam.exe",
      "shortcuts": [
        {
          "original_path": "C:\\Users\\Max\\Desktop\\Steam.lnk",
          "hidden": false
        }
      ]
    },
    {
      "name": "Battle.net",
      "process_name": "Battle.net.exe",
      "shortcuts": [
        {
          "original_path": "C:\\Users\\Max\\Desktop\\Battle.net.lnk",
          "hidden": false
        }
      ]
    }
  ],
  "productive_apps": [
    {
      "name": "VS Code",
      "executable": "C:\\Users\\Max\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
      "url": null,
      "window": {
        "x": 0,
        "y": 0,
        "width": 1920,
        "height": 1080,
        "screen": 0
      }
    },
    {
      "name": "Chrome",
      "executable": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
      "url": "https://learn.something.com",
      "window": {
        "x": 1920,
        "y": 0,
        "width": 1920,
        "height": 1080,
        "screen": 1
      }
    }
  ],
  "schedule": [
    {
      "day": "monday",
      "start": "19:00",
      "end": "21:00"
    },
    {
      "day": "wednesday",
      "start": "19:00",
      "end": "21:00"
    }
  ],
  "startup": {
    "launch_on_login": true,
    "startup_method": "registry"
  }
}
```

---

### 5.2 SQLite Schema

**Table: `sessions`**
```sql
CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  TEXT NOT NULL,
    ended_at    TEXT,
    type        TEXT NOT NULL CHECK(type IN ('scheduled', 'manual')),
    status      TEXT NOT NULL CHECK(status IN ('active', 'completed', 'interrupted'))
);
```

**Table: `overrides`**
```sql
CREATE TABLE IF NOT EXISTS overrides (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER NOT NULL REFERENCES sessions(id),
    app_name    TEXT NOT NULL,
    reason      TEXT NOT NULL,
    occurred_at TEXT NOT NULL
);
```

**Notes:**
- All timestamps stored as ISO 8601 strings (`2026-06-13T19:00:00`) for human readability and portability
- `ended_at` is nullable — populated when session closes; NULL indicates an active or interrupted session
- `status = 'interrupted'` covers: app quit mid-session, system crash, or forced stop
- Foreign key enforcement enabled at connection time via `PRAGMA foreign_keys = ON`

---

## 6. Key Design Decisions

### 6.1 Feature Slices Over Horizontal Layers
**Decision:** Organize the codebase by feature (session, shortcuts, launcher, friction, etc.) rather than by layer (UI, logic, data).

**Rationale:** Horizontal layering is a coordination tool — it creates clear ownership boundaries between teams working on different concerns. For a solo developer, those same boundaries become navigation overhead. When returning to a feature after time away, everything needed is in one folder rather than scattered across three. Feature slices reduce context switching and make the codebase easier to hold in your head.

**Tradeoff:** Some components genuinely span features (`settings_window`, `log_viewer`, `db_manager`). These live in shared folders (`/ui`, `/logging`) rather than being forced into a single feature slice. This is an acceptable compromise — the rule is "co-locate what changes together," and these shared components change with the app as a whole, not with any one feature.

---

### 6.2 Config File as Thread Communication Boundary
**Decision:** The session engine thread and the UI thread do not share memory or call each other directly. All communication flows through `config.json`, watched by `watchdog`.

**Rationale:** Shared state between threads requires locks, and locks introduce subtle bugs that are hard to reproduce and harder to debug. For the communication pattern in Atomic — the UI occasionally updates config, the engine occasionally reloads it — a file-based boundary is simple, reliable, and introduces no meaningful latency. The slight delay between a user saving settings and the engine reloading them is imperceptible in practice.

**Tradeoff:** The engine does not instantly react to config changes — it reacts on the next `watchdog` event. This is acceptable for all current use cases. If a future feature requires immediate cross-thread signaling, a proper queue (e.g. Python `queue.Queue`) should be introduced at that point rather than prematurely.

---

### 6.3 Friction, Not Blocking
**Decision:** Atomic never prevents the user from accessing a distraction app. It intercepts, asks for a reason, logs the decision, and then allows access.

**Rationale:** Hard blocking creates adversarial UX and is trivially defeated (uninstall the app, kill the process, reboot). Friction works differently — it breaks the automatic reflex by inserting a moment of conscious decision. The log of reasons over time is itself a habit-shaping tool: seeing "I just wanted a break" written twelve times in a week is more motivating than any block screen.

**Tradeoff:** A determined user can always get through. This is by design, not a limitation.

---

### 6.4 Shortcuts Moved, Never Deleted
**Decision:** When hiding shortcuts, Atomic moves `.lnk` files to `%APPDATA%\Atomic\hidden_shortcuts\`. It never deletes them.

**Rationale:** Deletion is irreversible. If a restore fails for any reason — crash, permission error, corrupted config — the user loses their shortcut permanently. Moving preserves the file at all times. The original path is recorded in `config.json` before the move, so restore is always exact. Worst case: the user finds their shortcuts in the hidden folder and moves them back manually.

**Tradeoff:** Requires `%APPDATA%\Atomic\hidden_shortcuts\` to exist and be writable. This is guaranteed by the first-run setup in M0.

---

### 6.5 Windows API Power Hooks Over psutil for Sleep Detection
**Decision:** Sleep and wake events are detected via Windows `WM_POWERBROADCAST` API hooks, not `psutil`.

**Rationale:** When Windows suspends the machine, it freezes all threads — including any `psutil` polling loop. By the time the thread could check for a sleep event, the machine is already asleep and the check never runs. Windows power hooks fire *before* suspension and *after* wake at the OS level, giving Atomic precise lifecycle control. `psutil` remains the right tool for process monitoring (M4) where it operates on running processes rather than system state.

**Tradeoff:** Power hooks require `ctypes` and Win32 API calls — the most platform-specific code in the project. This is the primary reason V2 Linux support will need a separate sleep/wake implementation. Code should be thoroughly commented and isolated in `power_monitor.py` so the swap is clean.

---

### 6.6 Windows Registry for Startup, Task Scheduler as Fallback
**Decision:** Atomic registers for Windows startup via the Registry key `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`. Task Scheduler is used only if Registry permissions are insufficient.

**Rationale:** The `HKCU` Registry key is user-scoped and does not require admin rights — it is the lightest-touch, most conventional method for startup registration on Windows. Task Scheduler has more power (and can run with elevated permissions), but that power comes with more complexity and a higher risk of misconfiguration. Start simple, escalate only if needed.

**Tradeoff:** If the user's environment restricts `HKCU` writes (uncommon on personal machines), Task Scheduler becomes the fallback. The startup method used is recorded in `config.json` under `startup.startup_method` so the correct unregistration method is always known.

---

### 6.7 SQLite for Logs, JSON for Config
**Decision:** Session and override logs are stored in SQLite. Configuration is stored in JSON.

**Rationale:** Config is read frequently, written rarely, needs to be human-readable, and benefits from being directly editable by a power user. JSON is the right fit. Logs are append-heavy, grow over time, benefit from query ability (filter by date, session, app), and do not need to be human-editable. SQLite is the right fit. Using one tool for both would mean either a bloated JSON file or a non-editable config — neither is acceptable.

**Tradeoff:** Two storage formats means two access patterns to understand. The tradeoff is worth it because each format is genuinely better suited to its use case.

---

## 7. OS Integration Points

This section documents the Windows-specific integration points in Atomic — the places where the code reaches outside Python's standard library and into the operating system. These are the highest-risk areas for unexpected behavior and should be tested thoroughly and commented carefully.

---

### 7.1 Shortcut File Manipulation
**What:** Moving `.lnk` files to and from `%APPDATA%\Atomic\hidden_shortcuts\`.

**How:** Standard `shutil.move()` for the file operation. Shortcut locations resolved via known Windows paths:
- Desktop: `%USERPROFILE%\Desktop`
- Taskbar pins: `%APPDATA%\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar`

**Risk:** Taskbar shortcut manipulation may require elevated permissions. UAC elevation strategy to be confirmed during M1 research spike. If elevation is required, it will be requested once at session start rather than per-operation.

**Failure mode:** If a move fails, the shortcut stays in its original location (no partial state). Error is logged and surfaced to the user via tray notification.

---

### 7.2 Windows Power Event Hooks
**What:** Receiving `WM_POWERBROADCAST` messages to detect sleep and wake events.

**How:** A hidden `HWND` (Windows message window) is created via `ctypes` and the Win32 API. The message loop listens for `PBT_APMSUSPEND` (sleep) and `PBT_APMRESUMEAUTOMATIC` (wake) events and calls `session_engine.pause()` and `session_engine.resume()` respectively.

**Risk:** This is the most platform-specific code in the project. Requires careful `ctypes` usage and thorough testing across sleep/wake cycles. Must be isolated in `power_monitor.py` — no other component should contain Win32 calls.

**Failure mode:** If the hook fails to register, the app logs the error and continues without sleep/wake awareness. Sessions will not pause on sleep but will otherwise function normally. The user is notified via tray on startup if the hook could not be registered.

---

### 7.3 Process Monitoring
**What:** Detecting when a blocked application is launched during a session.

**How:** `psutil.process_iter(['name', 'pid'])` polled on a configurable interval. On detection of a matching process name, `psutil.Process(pid).suspend()` is called immediately to freeze the process before the friction dialog is shown.

**Risk:** There is an inherent race condition — a fast-launching app may become visible to the user for a brief moment before the poll catches it and the friction dialog appears. The polling interval is the primary lever for managing this tradeoff. `suspend()` requires elevated permissions.

**Failure mode:** If `suspend()` fails (permission denied), the friction dialog is still shown but the app is not frozen — the user may interact with it before responding to the popup. This is logged as a degraded-mode warning.

---

### 7.4 Window Positioning
**What:** Launching productive apps at configured screen positions and sizes.

**How:** PyQt6 window management used to locate and reposition application windows after launch. A brief wait after process start gives the window time to appear before positioning is applied.

**Risk:** Some applications (particularly Electron apps like VS Code) create their window asynchronously — the window handle may not be available immediately after the process starts. A retry loop with a timeout is needed.

**Failure mode:** If a window cannot be positioned within the timeout, the app launches at its default position and a warning is logged. Session continues normally.

---

### 7.5 Windows Registry Startup Entry
**What:** Writing a startup entry so Atomic launches automatically on Windows login.

**How:** Write to `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` using Python's `winreg` module. Value name: `Atomic`. Value data: full path to `main.py` (or packaged executable).

**Risk:** Low — `HKCU` is user-scoped and does not require admin rights on standard personal machines.

**Failure mode:** If the Registry write fails, Atomic falls back to Task Scheduler. If that also fails, the user is informed that auto-startup could not be configured and must be set up manually.

---

## 8. Error Handling

Atomic interacts with the OS in ways that can fail for reasons outside the app's control — permission changes, missing files, processes that exit unexpectedly. The guiding principle is: **fail gracefully, never silently, and never corrupt user data.**

### Guiding Principles
- **Log everything** — all errors written to a rotating log file at `%APPDATA%\Atomic\atomic.log`
- **Never delete** — shortcuts are moved, not deleted; the hidden folder is the worst-case recovery point
- **Surface selectively** — minor errors (shortcut not found, window positioning failed) are logged silently; errors that affect session integrity (restore failed, hook not registered) are surfaced via tray notification
- **Restore on exit** — graceful shutdown always attempts shortcut restore before closing, even if a session is mid-flight

---

### Error Catalog

| Scenario                                  | Severity | Behavior                                                                            |
|-------------------------------------------|----------|-------------------------------------------------------------------------------------|
| `config.json` missing on startup          | Low      | Generate default config, continue                                                   |
| `config.json` malformed / invalid JSON    | High     | Show error dialog, exit — do not proceed with corrupt config                        |
| Shortcut not found at hide time           | Low      | Log and skip — session continues without hiding that shortcut                       |
| Shortcut move fails (permission denied)   | Medium   | Log error, notify via tray, skip that shortcut                                      |
| Shortcut restore fails                    | High     | Log error, notify via tray, leave file in hidden folder with instructions           |
| Productive app executable not found       | Low      | Log and skip — session continues, other apps still launch                           |
| Window positioning timeout                | Low      | Log warning, app opens at default position                                          |
| Process suspend fails (permission denied) | Medium   | Show friction dialog anyway, log degraded mode warning                              |
| `atomic.db` missing                       | Low      | Recreate schema, continue — log history lost                                        |
| `atomic.db` write fails                   | Medium   | Log error, continue session — data loss for that entry only                         |
| Power hook registration fails             | Medium   | Log error, notify via tray on startup — session engine runs without sleep awareness |
| Registry write fails (startup)            | Low      | Attempt Task Scheduler fallback; notify user if both fail                           |
| App crash mid-session                     | High     | On next startup: detect interrupted session in DB, restore shortcuts, notify user   |

---

## 9. Open Questions

| #   | Question                                                                                                        | Owner | Notes                                                                                    |
|-----|-----------------------------------------------------------------------------------------------------------------|-------|------------------------------------------------------------------------------------------|
| 9.1 | What is the final app name?                                                                                     | Max   | Placeholder "Atomic" in use — pending input from naming contact                          |
| 9.2 | UAC elevation strategy for shortcut manipulation                                                                | Max   | To be researched and resolved during M1 spike; findings documented back into Section 7.1 |
| 9.3 | Window positioning retry logic — what is the right timeout and retry interval for async windows (e.g. VS Code)? | Max   | To be determined during M3 implementation; findings documented back into Section 7.4     |

---

## 10. Out of Scope

The following are explicitly not part of the V1 MVP. They are documented here to prevent scope creep and to make future version planning easier.

| Feature                            | Reason Deferred                                                                                       | Target Version |
|------------------------------------|-------------------------------------------------------------------------------------------------------|----------------|
| Hard blocking of applications      | Against core philosophy — friction only, never enforcement                                            | Never          |
| Log viewer and data export         | Basic "View Log" tray entry exists in V1 as a stub; full UI viewer and CSV/JSON export deferred       | V2             |
| Browser content / URL redirect     | Requires network-level or extension-level integration; meaningfully more complex than shortcut hiding | V2             |
| Linux support                      | Shortcut engine, power hooks, and process monitor all require platform-specific reimplementation      | V2             |
| iOS support                        | Platform restrictions make this category of app infeasible on iOS                                     | Never          |
| Android app                        | New native build — not a port; requires separate planning                                             | V3             |
| Cloud sync or multi-device support | No multi-device use case in V1; adds infrastructure complexity                                        | Post-V3        |
| Social / accountability features   | Stretch goal only; no concrete design yet                                                             | Post-V3        |
| Multi-user support (same machine)  | Single-user assumption baked into config and data model                                               | Post-V3        |
| Network-level DNS filtering        | Requires admin-level network config; out of character for a friction tool                             | Never          |

---

## 11. Future Considerations

These are not commitments — they are design decisions made now that leave doors open for later without overbuilding.

### 11.1 V2 — Linux Port
The codebase is structured to make the Linux port as clean as possible:
- All Windows-specific code is isolated in `power_monitor.py` and the UAC elevation logic in `shortcut_engine.py` — Linux equivalents slot in without touching other components
- `%APPDATA%` path resolution is handled in a single helper in `config_manager.py` — swap to `~/.config/atomic/` for Linux in one place
- `psutil` is already cross-platform for process monitoring — no changes needed there
- `watchdog` is also cross-platform — config file watching carries over unchanged

### 11.2 V2 — Log Viewer and Data Export
The groundwork for a log viewer is already in place — `log_viewer.py` exists in the component map and "View Log" is a tray menu item in V1. In V1 this is a basic read-only display. V2 should expand it into a proper UI feature:

- **Log viewer window:** Tabbed display showing session history and override log with filtering by date range, session type, and app name
- **Data export:** Export session and override data as CSV or JSON from within the UI — no need to open `atomic.db` directly with an external tool
- `db_manager` already exposes `get_sessions()` and `get_overrides()` with pagination — the viewer and export both build on these methods without schema changes

### 11.3 V2 — Browser Friction
Browser redirect during focus sessions will require one of two approaches — the right choice depends on research at V2 planning time:
- **Local proxy:** Route browser traffic through a local proxy that intercepts and redirects distraction URLs. More reliable, works across all browsers, higher implementation complexity.
- **Browser extension:** A companion extension that reads the active session state and redirects in-browser. Easier to build, but requires the user to install the extension and only works in supported browsers.

Both approaches lift cleanly on top of the existing session state model — the session engine already knows when a session is active; browser friction just needs to read that state.

### 11.3 V3 — Android App
The Android app is a new, independent build — not a port. A few things are worth keeping in mind during V1 and V2 that will make V3 easier:
- Keep the `config.json` schema stable and well-documented — if cloud sync is ever added, the Android app will need to read and write the same format
- The session model (start, end, type, status) is generic enough to carry over directly
- Override logging schema is also portable — the SQLite tables can be reproduced in Android's Room database with minimal changes

### 11.4 Config Schema Versioning
`version` was intentionally omitted from `config.json` in V1 — there is no migration logic and it would be noise. If the config schema changes between future versions in a breaking way, a `version` field should be added at that point and a migration utility written in `config_manager.py`. The atomic write pattern already in place (write to temp, rename) makes migration safe.

### 11.5 Packaging and Distribution
V1 runs as a Python script. At some point — likely before sharing with other users — packaging will be needed:
- **PyInstaller** is the most common option for Python desktop apps on Windows; bundles the interpreter and all dependencies into a single executable
- A proper installer (e.g. NSIS or Inno Setup) would handle `%APPDATA%` folder creation, Registry startup entry, and uninstallation cleanly
- This is not an MVP concern but is worth one planning session before V2