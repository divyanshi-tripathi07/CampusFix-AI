-- Canonical schema reference. Runtime initialization is idempotent in backend/app.py.
CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL, department TEXT, created_at TEXT NOT NULL);
CREATE TABLE complaint_categories (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, description TEXT, created_at TEXT NOT NULL);
CREATE TABLE complaints (id INTEGER PRIMARY KEY, public_id TEXT UNIQUE NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL, location TEXT NOT NULL, category_id INTEGER, priority TEXT NOT NULL, status TEXT NOT NULL, reporter_id INTEGER NOT NULL, duplicate_group_id INTEGER, ai_confidence REAL NOT NULL, due_at TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, resolved_at TEXT, resolution_notes TEXT);
CREATE TABLE complaint_assignments (id INTEGER PRIMARY KEY, complaint_id INTEGER NOT NULL, assigned_to INTEGER, department TEXT NOT NULL, assigned_by INTEGER NOT NULL, created_at TEXT NOT NULL, completed_at TEXT);
CREATE TABLE duplicate_groups (id INTEGER PRIMARY KEY, name TEXT NOT NULL, summary TEXT, created_at TEXT NOT NULL);
CREATE TABLE complaint_status_history (id INTEGER PRIMARY KEY, complaint_id INTEGER NOT NULL, status TEXT NOT NULL, changed_by INTEGER NOT NULL, note TEXT, created_at TEXT NOT NULL);
CREATE TABLE notifications (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, complaint_id INTEGER, message TEXT NOT NULL, read INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE resolution_feedback (id INTEGER PRIMARY KEY, complaint_id INTEGER NOT NULL, user_id INTEGER NOT NULL, rating INTEGER NOT NULL, comment TEXT, created_at TEXT NOT NULL);
