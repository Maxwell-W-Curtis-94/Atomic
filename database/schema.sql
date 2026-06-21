CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  TEXT NOT NULL,
    ended_at    TEXT,
    type        TEXT NOT NULL CHECK(type IN ('scheduled', 'manual')),
    status      TEXT NOT NULL CHECK(status IN ('active', 'completed', 'interrupted'))
);
