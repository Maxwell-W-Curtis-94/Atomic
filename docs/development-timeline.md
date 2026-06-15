# Development Timeline — Atomic
**Version:** 0.1 (Draft)
**Author:** Maxwell Curtis
**Date:** June 14, 2026
**Status:** In Progress

---

## Summary

| Milestone                    | Start        | End          | Duration              |
|------------------------------|--------------|--------------|-----------------------|
| M0 — Project Scaffolding     | June 14      | June 30      | ~2 weeks (soft start) |
| M1 — Shortcut Engine         | July 1       | July 14      | 2 weeks               |
| M2 — Session Engine          | July 15      | July 28      | 2 weeks               |
| M3 — App Launcher            | July 29      | August 4     | 1 week                |
| M4 — Friction & Logging      | August 5     | August 18    | 2 weeks               |
| M5 — Configuration UI        | August 19    | September 1  | 2 weeks               |
| M6 — System Tray & Lifecycle | September 2  | September 15 | 2 weeks               |
| M7 — Polish & Testing        | September 16 | September 30 | 2 weeks               |

**Target MVP completion: September 30, 2026**

---

## M0 — Project Scaffolding
**Dates:** June 14 – June 30
**Duration:** ~2 weeks (soft start alongside planning)
**Depends on:** Nothing — this is the foundation

### Goals
Get the project into a state where M1 can begin immediately on July 1st with no setup overhead.

### Key tasks
- Initialize Git repo with correct folder structure (per TDD component map)
- Set up virtual environment and `requirements.txt`
- Write first-run logic: create `%APPDATA%\Atomic\` folder, generate default `config.json`, initialize `atomic.db` with schema
- Confirm `main.py` runs without errors
- Commit README stub

### Risk
Low. This milestone has no OS-level unknowns and no dependencies. If it runs long it does not affect the July 1st kickoff — M1 just starts with more scaffolding already done.

---

## M1 — Shortcut Engine
**Dates:** July 1 – July 14
**Duration:** 2 weeks
**Depends on:** M0 complete

### Goals
Prove the core capability of the app — hide and restore a shortcut cleanly on Windows. Everything downstream depends on this working reliably.

### Key tasks
- Research and resolve UAC elevation strategy (document findings back into TDD Section 7.1)
- Build shortcut locate, hide, and restore functions
- Write manual test script for Steam shortcut hide/restore cycle
- Handle edge cases: not found, already hidden, permission denied

### Risk
**Highest risk milestone in the project.** Windows shortcut and taskbar manipulation has the most OS-level unknowns. Budget the first few days purely for the research spike — do not start writing production code until the elevation strategy is confirmed. If this milestone runs over, pull time from the M3 buffer (M3 is only 1 week and has lower risk).

---

## M2 — Session Engine
**Dates:** July 15 – July 28
**Duration:** 2 weeks
**Depends on:** M1 complete (shortcut engine must be functional to integrate)

### Goals
The app understands what a focus session is, can start and stop one on a schedule or manually, and correctly integrates the shortcut engine.

### Key tasks
- Build session model and state machine (IDLE → ACTIVE → PAUSED → IDLE)
- Build schedule manager — reads config, fires sessions at correct times
- Integrate shortcut engine: hide on start, restore on end
- Add sleep/wake awareness via Windows power event hooks (first implementation of `power_monitor.py`)
- Write sessions to SQLite on start and close

### Risk
Medium. The state machine logic is straightforward but sleep/wake behavior is easy to get subtly wrong. Test sleep mid-session explicitly before marking this milestone done — don't leave it for M7.

---

## M3 — App Launcher
**Dates:** July 29 – August 4
**Duration:** 1 week
**Depends on:** M2 complete (session engine must be running to trigger launcher)

### Goals
Starting a session automatically opens productive tools at their saved screen positions.

### Key tasks
- Build launcher module: read productive app list from config, open each on session start
- Handle "already running" case: bring to foreground rather than open second instance
- Implement window positioning via PyQt6
- Build "Save current layout" function

### Risk
Low — medium. Window positioning is the one unknown here. Timebox it to a single session: if PyQt6 window management works cleanly, ship it. If not, launch apps without positioning and revisit in M7 polish. Do not let window positioning block this milestone.

---

## M4 — Friction & Logging
**Dates:** August 5 – August 18
**Duration:** 2 weeks
**Depends on:** M2 complete (process monitor only runs during active sessions)

### Goals
Blocked apps trigger a friction popup during sessions. Overrides are logged to SQLite with a reason and timestamp.

### Key tasks
- Build process monitor using `psutil` with configurable polling interval
- Build friction dialog (PyQt6): modal, always-on-top, requires reason before confirming
- Implement `psutil.Process.suspend()` on detection, resume or terminate on dialog response
- Log overrides to SQLite
- Build basic log viewer (simple window or CLI read of override history)

### Risk
Medium. The race condition between app launch and poll detection is a known tradeoff — test at multiple polling intervals and document the recommended default. `suspend()` permission requirements need confirming early in the milestone.

---

## M5 — Configuration UI
**Dates:** August 19 – September 1
**Duration:** 2 weeks
**Depends on:** M3 and M4 complete (UI must cover all features built so far)

### Goals
A new user can configure all aspects of the app through a UI without touching a JSON file.

### Key tasks
- Build settings window in PyQt6 with four tabs: Distraction Apps, Productive Apps, Schedule, Performance
- Implement shortcut path picker and executable path picker
- Implement schedule builder (add/edit/delete time blocks per day)
- Write config changes back to `config.json` on save
- Add "Open config file" button for power users

### Risk
Low. This is pure PyQt6 UI work with no new OS-level integration. The main risk is scope creep — keep the UI functional and clean rather than polished. Polish is M7's job.

---

## M6 — System Tray & Lifecycle
**Dates:** September 2 – September 15
**Duration:** 2 weeks
**Depends on:** All prior milestones complete

### Goals
The app lives in the system tray, starts with Windows, and the full session lifecycle is accessible from the tray menu without opening any window.

### Key tasks
- Integrate `pystray`: tray icon, menu (Start, Stop, Settings, Log, Quit)
- App starts minimized to tray with no visible window
- Register startup entry in Windows Registry (`HKCU\...\Run`); Task Scheduler fallback if needed
- Implement graceful shutdown: restore shortcuts and end session before exit
- Wire up `watchdog` config file watching on session engine thread
- Validate sleep/wake behavior end-to-end with full app running

### Risk
Medium. Thread coordination between `pystray` and PyQt6 is the primary risk. Test the full lifecycle — start, sleep, wake, stop, quit — before marking done. This is also the milestone where the two-thread architecture gets stress tested for the first time as a complete system.

---

## M7 — Polish & Testing
**Dates:** September 16 – September 30
**Duration:** 2 weeks
**Depends on:** M6 complete — full app functional

### Goals
The app is stable, tested, and presentable as a portfolio piece. README is good enough to hand to a stranger.

### Key tasks
- Write unit tests: session engine, shortcut engine, config loader, override logger
- Manual test checklist: full session lifecycle (scheduled and manual)
- Edge case testing: crash mid-session, missing shortcut, malformed config, sleep mid-session
- Resolve any known rough edges from prior milestones (window positioning if deferred from M3)
- Update README: description, setup instructions, screenshots
- Review code for consistency; comment all OS-interaction code thoroughly

### Risk
Low — but do not skip it. A portfolio project without tests and a clean README is worth significantly less than one with both. This milestone is what turns a working app into a credible piece of work.

---

## Dependencies Map

```
M0 → M1 → M2 → M3 → M5
               ↓         ↑
               M4 ────────
                    M5 → M6 → M7
```

M3 and M4 both depend on M2 and feed into M5. M6 requires everything before it. M7 closes the project.

---

## Buffer and Risk Notes

**M1 is the highest risk milestone** — if it runs over, pull time from M3 (the shortest milestone with the lowest risk). Do not pull from M2 or M4.

**Life happens** — at 4–6 hours/week, one disrupted week (travel, illness, heavy work sprint) can shift a milestone by a week. The timeline has no explicit buffer weeks built in. If a milestone slips, adjust the dates forward rather than compressing the next milestone.

**Do not compress M7** — testing and documentation are the first things to get cut when a project runs late. Protect this milestone. A working app with no tests or README is not a portfolio piece.

---

## Revision History

| Version | Date          | Notes         |
|---------|---------------|---------------|
| 0.1     | June 14, 2026 | Initial draft |