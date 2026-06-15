# Testing Plan — Atomic
**Version:** 1.0
**Author:** Maxwell Curtis
**Date:** June 14, 2026,
**Status:** Approved

---

## Philosophy

Atomic interacts heavily with the OS — file system, process table, Windows APIs, the Registry. Most of what can go wrong happens at those boundaries, not in pure logic. The testing strategy reflects this:

- **Unit tests** cover pure logic that can run without OS interaction (state machines, config parsing, data validation, DB operations)
- **Integration tests** cover the boundaries where components hand off to each other
- **Manual tests** cover OS-level behavior that cannot be reliably faked in a test environment (shortcut file manipulation, sleep/wake hooks, window positioning)

The goal is not 100% coverage — it is targeted confidence in the parts most likely to break in production.

---

## Framework & Tools

| Tool                            | Purpose                                                    |
|---------------------------------|------------------------------------------------------------|
| `pytest`                        | Primary test runner and assertion library                  |
| `pytest-mock` / `unittest.mock` | Mocking OS calls, file system, psutil, Win32 API           |
| `tmp_path` (pytest fixture)     | Temporary directories for config and shortcut file tests   |
| Manual test checklist           | OS-level behaviors that require a real Windows environment |

---

## Test Structure

```
atomic/
└── tests/
    ├── unit/
    │   ├── test_config_manager.py
    │   ├── test_session_engine.py
    │   ├── test_shortcut_engine.py
    │   ├── test_db_manager.py
    │   └── test_process_monitor.py
    ├── integration/
    │   ├── test_session_shortcut_integration.py
    │   ├── test_session_launcher_integration.py
    │   └── test_friction_logging_integration.py
    └── manual/
        └── manual_test_checklist.md
```

---

## Unit Tests

### `test_config_manager.py`

| Test                                              | Description                                                                                                     |
|---------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|
| `test_default_config_created_on_first_run`        | If no `config.json` exists, one is generated with correct default structure                                     |
| `test_config_loads_valid_file`                    | A valid `config.json` loads without error and returns correct values                                            |
| `test_config_rejects_invalid_json`                | A malformed JSON file raises a handled error, not an unhandled exception                                        |
| `test_missing_optional_keys_filled_with_defaults` | Config with missing optional keys loads cleanly with defaults applied                                           |
| `test_missing_required_keys_raises_error`         | Config missing required keys raises a clear, descriptive error                                                  |
| `test_atomic_write`                               | Saving config writes to a temp file first, then renames — original not corrupted on simulated mid-write failure |
| `test_appdata_path_resolved_at_runtime`           | Base path uses `%APPDATA%` env var, not a hardcoded string                                                      |

---

### `test_session_engine.py`

| Test                                             | Description                                                                               |
|--------------------------------------------------|-------------------------------------------------------------------------------------------|
| `test_initial_state_is_idle`                     | Session engine starts in IDLE state                                                       |
| `test_start_session_transitions_to_active`       | `start_session()` moves state from IDLE to ACTIVE                                         |
| `test_stop_session_transitions_to_idle`          | `stop_session()` moves state from ACTIVE to IDLE                                          |
| `test_pause_transitions_to_paused`               | `pause()` moves state from ACTIVE to PAUSED                                               |
| `test_resume_transitions_to_active`              | `resume()` moves state from PAUSED to ACTIVE                                              |
| `test_stop_while_paused_transitions_to_idle`     | `stop_session()` from PAUSED state moves to IDLE                                          |
| `test_schedule_triggers_session_at_correct_time` | Schedule manager fires `start_session()` at configured time (mocked clock)                |
| `test_schedule_does_not_fire_outside_window`     | No session started outside scheduled time window                                          |
| `test_config_reload_updates_schedule`            | Changing schedule in config and triggering reload updates active schedule without restart |
| `test_session_written_to_db_on_start`            | `start_session()` writes a session record to SQLite with correct type and status          |
| `test_session_closed_in_db_on_stop`              | `stop_session()` updates session record with `ended_at` and `status = completed`          |
| `test_interrupted_session_flagged_in_db`         | Session left open (simulated crash) has `status = interrupted` on next startup check      |

---

### `test_shortcut_engine.py`

| Test                                            | Description                                                                  |
|-------------------------------------------------|------------------------------------------------------------------------------|
| `test_hide_moves_file_to_hidden_folder`         | Shortcut file is moved from source to `hidden_shortcuts/` (using `tmp_path`) |
| `test_hide_records_original_path_in_config`     | Original path written to config before file is moved                         |
| `test_restore_moves_file_back_to_original`      | File moved back from `hidden_shortcuts/` to recorded original path           |
| `test_restore_clears_recorded_path`             | After restore, original path entry cleared from config                       |
| `test_hide_skips_missing_shortcut`              | If shortcut file not found, logs and skips — no error raised                 |
| `test_hide_skips_already_hidden_shortcut`       | If shortcut already in hidden folder, skips without error                    |
| `test_restore_leaves_file_in_hidden_on_failure` | If restore fails, file stays in hidden folder — not deleted                  |

---

### `test_db_manager.py`

| Test                                      | Description                                                                       |
|-------------------------------------------|-----------------------------------------------------------------------------------|
| `test_schema_created_on_first_run`        | `sessions` and `overrides` tables created if `atomic.db` does not exist           |
| `test_log_session_start_inserts_record`   | `log_session_start()` inserts row with correct type, status, and timestamp        |
| `test_log_session_end_updates_record`     | `log_session_end()` updates `ended_at` and `status` on correct session ID         |
| `test_log_override_inserts_record`        | `log_override()` inserts row with correct session ID, app name, reason, timestamp |
| `test_get_overrides_returns_correct_rows` | `get_overrides()` returns correct rows with pagination                            |
| `test_get_sessions_returns_correct_rows`  | `get_sessions()` returns correct rows with pagination                             |
| `test_foreign_key_enforcement`            | Inserting override with invalid session ID raises integrity error                 |
| `test_write_wrapped_in_transaction`       | Simulated mid-write failure does not leave partial data in DB                     |

---

### `test_process_monitor.py`

| Test                                     | Description                                                             |
|------------------------------------------|-------------------------------------------------------------------------|
| `test_monitor_inactive_outside_session`  | Process monitor does not poll when session state is IDLE                |
| `test_monitor_active_during_session`     | Process monitor polls when session state is ACTIVE                      |
| `test_blocked_app_detected_by_name`      | Process matching a blocked app name triggers friction callback          |
| `test_non_blocked_app_ignored`           | Process not in blocked list does not trigger friction callback          |
| `test_polling_interval_read_from_config` | Monitor uses polling interval from `config.json`, not a hardcoded value |

---

## Integration Tests

### `test_session_shortcut_integration.py`

| Test                                     | Description                                                                                                                  |
|------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| `test_session_start_hides_shortcuts`     | Starting a session via `session_engine` triggers `shortcut_engine.hide()` for all configured distraction apps                |
| `test_session_end_restores_shortcuts`    | Ending a session triggers `shortcut_engine.restore()` for all hidden shortcuts                                               |
| `test_crash_recovery_restores_shortcuts` | Simulated interrupted session: on next startup, shortcuts in hidden folder are restored and session marked interrupted in DB |

---

### `test_session_launcher_integration.py`

| Test                                             | Description                                                                                               |
|--------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| `test_session_start_launches_productive_apps`    | Starting a session triggers `app_launcher` to open all configured productive apps (mocked subprocess)     |
| `test_already_running_app_brought_to_foreground` | If productive app is already running, launcher brings it to focus rather than launching a second instance |

---

### `test_friction_logging_integration.py`

| Test                                          | Description                                                                       |
|-----------------------------------------------|-----------------------------------------------------------------------------------|
| `test_override_confirmed_resumes_process`     | Confirming friction dialog resumes the suspended process and logs override to DB  |
| `test_override_cancelled_terminates_process`  | Cancelling friction dialog terminates the suspended process, no DB entry written  |
| `test_override_log_contains_correct_metadata` | Override entry in DB contains correct session ID, app name, reason, and timestamp |

---

## Manual Test Checklist

These tests require a real Windows environment and cannot be automated. Run the full checklist before closing M7.

```markdown
## Manual Test Checklist — Atomic MVP

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
- [ ] App crash during active session: on restart, shortcuts restored and interrupted session flagged
```

---

## When to Run Tests

| Test Type         | When                                                              |
|-------------------|-------------------------------------------------------------------|
| Unit tests        | Run after every coding session — `pytest tests/unit/`             |
| Integration tests | Run at the end of each milestone before marking done              |
| Manual checklist  | Run once at end of M7 — full pass required before MVP is complete |

---

## Revision History

| Version | Date          | Notes         |
|---------|---------------|---------------|
| 0.1     | June 14, 2026 | Initial draft |