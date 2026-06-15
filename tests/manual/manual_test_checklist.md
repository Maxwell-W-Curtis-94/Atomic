Manual Test Checklist

These tests require a real Windows environment and cannot be automated. Run the full checklist before closing M7.

markdown## Manual Test Checklist — Atomic MVP

### Shortcut Engine
- [ ] Steam shortcut disappears from desktop when session starts
- [ ] Steam shortcut disappears from taskbar when session starts
- [ ] Steam shortcut reappears in original desktop location when session ends
- [ ] Steam shortcut reappears in original taskbar location when session ends
- [ ] Shortcut is present in %APPDATA%\Atomic\hidden_shortcuts\ during session
- [ ] Shortcut is NOT present in hidden folder after session ends

### Session Engine — Scheduled
- [ ] Session starts automatically at configured scheduled time
- [ ] Session ends automatically at configured end time
- [ ] No session starts outside configured schedule

### Session Engine — Manual
- [ ] Session starts immediately on "Start Session" from tray menu
- [ ] Session stops immediately on "Stop Session" from tray menu

### Sleep / Wake
- [ ] Putting PC to sleep during a session does not crash the app
- [ ] Waking PC resumes session correctly if still within scheduled window
- [ ] Waking PC after session window has passed ends session cleanly

### App Launcher
- [ ] VS Code opens at saved screen position on session start
- [ ] Browser opens at saved URL and screen position on session start
- [ ] If VS Code already open, it is brought to foreground (no second instance)
- [ ] "Save Current Layout" correctly records current window positions to config

### Friction & Logging
- [ ] Launching Steam during active session triggers friction popup
- [ ] Friction popup is modal and always on top
- [ ] Confirming with a reason allows Steam to open
- [ ] Cancelling closes the popup and Steam does not open
- [ ] Override appears in log viewer with correct timestamp, app name, and reason

### System Tray
- [ ] App starts with no visible window — only tray icon present
- [ ] All tray menu items work correctly
- [ ] App launches automatically on Windows login
- [ ] Quitting app mid-session restores all shortcuts before closing

### Configuration UI
- [ ] Adding a distraction app via UI persists to config.json on save
- [ ] Adding a productive app via UI persists to config.json on save
- [ ] Adding a schedule block via UI persists to config.json on save
- [ ] Session engine picks up config changes without restarting the app
- [ ] "Open config file" button opens config.json in default text editor

### Edge Cases
- [ ] App starts cleanly with a missing config.json (generates default)
- [ ] App shows error and exits cleanly with a malformed config.json
- [ ] App starts cleanly with a missing atomic.db (recreates schema)
- [ ] Shortcut listed in config but not found on disk — session starts, warning shown
- [ ] App crash during active session: on restart, shortcuts res