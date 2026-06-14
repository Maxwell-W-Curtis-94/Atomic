# Feature Roadmap — Atomic
**Version:** 1.0
**Author:** Maxwell Curtis
**Date:** June 12, 2026
**Scope:** MVP — Windows V1 only
**Velocity assumption:** 4–6 hours/week, milestones sized at ~2 weeks each

---

## Milestone Overview

| #  | Milestone               | Est. Duration | Cumulative |
|----|-------------------------|---------------|------------|
| M0 | Project Scaffolding     | 1 week        | Week 1     |
| M1 | Shortcut Engine         | 2 weeks       | Week 3     |
| M2 | Session Engine          | 2 weeks       | Week 5     |
| M3 | App Launcher            | 1 week        | Week 6     |
| M4 | Friction & Logging      | 2 weeks       | Week 8     |
| M5 | Configuration UI        | 2 weeks       | Week 10    |
| M6 | System Tray & Lifecycle | 2 weeks       | Week 12    |
| M7 | Polish & Testing        | 2 weeks       | Week 14    |

**Estimated MVP completion: ~14 weeks from start**

---

## M0 — Project Scaffolding
**Duration:** 1 week
**Goal:** The project exists, runs, and is set up to be built correctly from day one.

### Deliverables
- Repo initialized with folder structure and `.gitignore`
- Virtual environment + `requirements.txt` (PyQt6, pystray, watchdog, initial deps)
- Placeholder `main.py` entry point that launches without errors
- SQLite database initialized on first run with schema for sessions and override logs
- Default `config.json` generated on first run with empty distraction/productive app lists
- README stub committed

### Definition of Done
Running `python main.py` starts the app without errors and creates the expected config and database files.

---

## M1 — Shortcut Engine
**Duration:** 2 weeks
**Goal:** The app can hide and restore desktop/taskbar shortcuts on Windows. This is the core platform-specific capability everything else depends on.

### Deliverables
- Module that locates shortcuts by app name on the Desktop and Taskbar
- Hide function: moves shortcuts to a designated hidden folder (`atomic/hidden_shortcuts/`)
- Restore function: moves shortcuts back to their original recorded locations
- Handles edge cases: shortcut not found, already hidden, permission denied
- Manual test script to verify hide/restore on a real shortcut (e.g. Steam)
- Research spike documented: UAC/admin elevation approach decided and noted

### Definition of Done
Running a test script hides a Steam shortcut from the desktop and taskbar, then restores it cleanly with no data loss.

### Notes
- **Primary strategy:** Move shortcuts to a hidden folder — safe, reversible, no rebuild needed
- **Alternative explored during spike:** Windows virtual desktop automation (more complex, lower priority)
- Shortcuts are **moved, never deleted** — original path recorded in config before move so restore is exact
- UAC elevation will likely be required; approach confirmed during research spike
- This milestone has the most OS-level unknowns — budget extra time

---

## M2 — Session Engine
**Duration:** 2 weeks
**Goal:** The app understands what a "focus session" is and can start/stop one on a schedule or on demand.

### Deliverables
- Session model: start time, end time, status (active/inactive), session type (scheduled/manual)
- Schedule manager: reads schedule from `config.json`, triggers sessions at defined times
- Manual trigger: start/stop a session programmatically (no UI yet — tested via script)
- Session written to SQLite on start and closed on end
- Shortcut Engine integrated: session start hides distractions, session end restores them
- Sleep/wake awareness: session scheduling only runs while PC is active; session behavior paused while system is asleep

### Definition of Done
A scheduled session starts automatically at a configured time, hides shortcuts, and restores them when the session ends. A manual trigger does the same on demand. A sleeping PC does not trigger or advance sessions.

### Notes
- **Sleep detection: Windows API power event hooks** — confirmed over `psutil` because Windows suspends all threads on sleep, meaning `psutil` would never fire; power hooks fire before suspension and after wake, giving precise lifecycle control
- Session state must handle the case where the PC sleeps mid-session gracefully (pause, not terminate)

---

## M3 — App Launcher
**Duration:** 1 week
**Goal:** When a focus session starts, the app automatically opens the user's configured productive tools in the right positions.

### Deliverables
- Launcher module: reads productive app list from `config.json`
- Opens each app in the list on session start (IDE, browser with target URL, etc.)
- Handles edge cases: app not found, already running (bring to focus), launch failure logged
- Browser launch supports a configurable URL (opens directly to a configured learning site)
- Window positioning: launches apps at X/Y coordinates and screen index stored in `config.json`
- "Save current layout" feature: records position and size of all running productive apps into config — user arranges windows manually, hits save, layout reproduced on every session start

### Definition of Done
Starting a focus session hides distractions, opens VS Code and a browser at a configured URL, and places them at their saved screen positions automatically.

### Notes
- **Window positioning: PyQt6** — keeps dependencies minimal, uses what's already in the stack
- "Save current layout" is the primary UX for setting positions — no manual coordinate entry required
- "Already running" case: bring existing window to focus rather than launching a second instance

---

## M4 — Friction & Logging
**Duration:** 2 weeks
**Goal:** When a user tries to open a blocked app during a focus session, they are stopped with a popup, asked for a reason, and the override is logged.

### Deliverables
- Process monitor: watches for blocked apps being launched during a session using `psutil`
- Adaptive polling interval: configurable by the user, with sensible defaults based on system specs
- Friction popup (PyQt6): modal dialog with app name, reason text input, and confirm button
- Override logged to SQLite: timestamp, app name, session ID, reason entered
- App allowed to open only after reason is submitted
- Log viewer: basic read of override history (CLI or simple window)

### Definition of Done
Launching Steam during an active session triggers the friction popup. Entering a reason and confirming allows Steam to open. The override appears in the SQLite database with correct metadata. Polling interval is configurable in `config.json`.

### Notes
- Polling interval is a real engineering tradeoff — too fast burns CPU, too slow lets the app open before the popup appears
- User-configurable with spec-aware defaults is the right long-term solution
- Popup must be modal and always-on-top to be effective

---

## M5 — Configuration UI
**Duration:** 2 weeks
**Goal:** The user can configure the app through a proper UI rather than editing JSON files manually.

### Deliverables
- Settings window (PyQt6): tabbed layout with sections for:
  - Distraction apps (add/remove with shortcut path picker)
  - Productive apps (add/remove with path, optional URL, optional window position)
  - Schedule (add/edit/delete time blocks per day of week)
  - Performance (polling interval configuration)
- Changes written back to `config.json` on save
- Config validated on load — invalid entries flagged gracefully
- "Open config file" button for power users who prefer editing JSON directly

### Definition of Done
A new user can configure their distraction apps, productive apps, weekly schedule, and polling settings entirely through the UI without touching a JSON file.

---

## M6 — System Tray & Lifecycle
**Duration:** 2 weeks
**Goal:** The app lives in the system tray, starts with Windows, handles sleep/wake events, and exposes all core controls from the tray icon.

### Deliverables
- pystray integration: app icon in system tray on launch
- Tray menu: Start Session, Stop Session, Open Settings, View Log, Quit
- App starts minimized to tray (no window on launch)
- Windows startup registration via Registry (escalate to Task Scheduler only if Registry lacks required permissions)
- Graceful shutdown: session restored and shortcuts returned if app is quit mid-session
- Sleep/wake lifecycle hooks: Windows API power event hooks — fires before suspension and after wake for precise session pause/resume
- Thread architecture: pystray and PyQt6 on separate threads; communicate via `config.json` watched by `watchdog` — UI config changes detected reactively by session engine

### Definition of Done
The app starts on login, lives in the tray, correctly pauses and resumes around system sleep, and the full session lifecycle can be triggered from the tray menu without opening the settings window.

### Notes
- Thread separation (pystray / PyQt6) keeps UI responsive and session engine stable
- `watchdog` handles config file change detection — chosen over manual polling for its built-in reliability and cross-platform foundations (useful at V2)
- Test sleep/wake behavior explicitly — easy to get subtly wrong

---

## M7 — Polish & Testing
**Duration:** 2 weeks
**Goal:** The app is stable, tested, and presentable as a portfolio piece.

### Deliverables
- Unit tests for: Session Engine, Shortcut Engine, Config loader, Override logger
- Manual test checklist covering full session lifecycle (scheduled + manual)
- Edge case testing: app crash mid-session, shortcuts missing, config malformed, sleep mid-session
- README updated: project description, setup instructions, screenshots
- Code reviewed for consistency, comments added to complex OS-interaction code
- At least one known bug or rough edge resolved from prior milestones

### Definition of Done
The app completes a full focus session lifecycle without errors. Tests pass. README is good enough to hand to a stranger.

---

## Post-MVP Roadmap (High Level)

### V2 — Linux + Browser Friction
- Ubuntu port: adapt shortcut engine and process monitor to Linux equivalents; portable to other common distros
- Browser friction: redirect distraction URLs during focus sessions, lifted on override or session end
- Estimated start: after V1 is stable and in personal use for 2–4 weeks

### V3 — Android
- New native Android app, same feature set
- Built independently — not a port of the Python desktop app
- Stack TBD at V2 completion

---

## Stack Summary

| Concern              | Tool                    | Rationale                                      |
|----------------------|-------------------------|------------------------------------------------|
| UI                   | PyQt6                   | Industry standard, portfolio credibility       |
| System tray          | pystray                 | Lightweight, purpose-built                     |
| Config watching      | watchdog                | Reactive, reliable, cross-platform foundations |
| Process monitoring   | psutil                  | Cross-platform, well-documented                |
| Sleep/wake detection | Windows API power hooks | Only reliable option given thread suspension   |
| Window positioning   | PyQt6                   | Already in stack, no extra dependency          |
| Data storage         | SQLite + JSON           | JSON for config/runtime, SQLite for logs       |

---

## Open Questions
- [ ] What is the final app name? (Placeholder: "Atomic")