import csv
import io
import os
import sqlite3
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from flask import Flask, g, jsonify, request, Response
from werkzeug.security import check_password_hash, generate_password_hash

from .ml_pipeline import find_duplicate, predict

BASE_DIR = Path(__file__).resolve().parent
DATABASE = Path(os.getenv("CAMPUSFIX_DATABASE", BASE_DIR / "campusfix.sqlite3"))
SECRET_KEY = os.getenv("CAMPUSFIX_SECRET_KEY", "development-only-change-me")

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["JSON_SORT_KEYS"] = False

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('student', 'admin', 'maintenance')),
  department TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS complaint_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS duplicate_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    summary TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS complaints (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  public_id TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  location TEXT NOT NULL,
  category TEXT NOT NULL,
  priority TEXT NOT NULL,
  status TEXT NOT NULL,
  reporter_id INTEGER NOT NULL,
  assigned_team TEXT,
  duplicate_cluster TEXT,
  ai_confidence REAL NOT NULL DEFAULT 0,
  due_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  resolved_at TEXT,
  resolution_notes TEXT,
    duplicate_group_id INTEGER,
  FOREIGN KEY(reporter_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS complaint_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL,
    assigned_to INTEGER,
    department TEXT NOT NULL,
    assigned_by INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY(complaint_id) REFERENCES complaints(id),
    FOREIGN KEY(assigned_to) REFERENCES users(id),
    FOREIGN KEY(assigned_by) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS complaint_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    changed_by INTEGER NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(complaint_id) REFERENCES complaints(id),
    FOREIGN KEY(changed_by) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  complaint_id INTEGER,
  message TEXT NOT NULL,
  read INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id),
  FOREIGN KEY(complaint_id) REFERENCES complaints(id)
);
CREATE TABLE IF NOT EXISTS feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  complaint_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
  comment TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(complaint_id) REFERENCES complaints(id),
  FOREIGN KEY(user_id) REFERENCES users(id)
);
"""


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_: BaseException | None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DATABASE)
    db.executescript(SCHEMA)
    try:
        db.execute("ALTER TABLE complaints ADD COLUMN duplicate_group_id INTEGER")
    except sqlite3.OperationalError:
        pass
    db.execute("UPDATE users SET name = ? WHERE email = ?", ("Divyanshi Tripathi", "admin@northbridge.edu"))
    db.commit()
    db.close()


def seed_db() -> None:
    with app.app_context():
        db = get_db()
        if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            return
        now = utc_now().isoformat()
        users = [
            ("Divyanshi Tripathi", "admin@northbridge.edu", generate_password_hash("admin-demo"), "admin", "Operations"),
            ("Aarav Sharma", "student@northbridge.edu", generate_password_hash("student-demo"), "student", None),
            ("Nisha Verma", "maintenance@northbridge.edu", generate_password_hash("staff-demo"), "maintenance", "Facilities Response"),
        ]
        db.executemany("INSERT INTO users(name,email,password_hash,role,department,created_at) VALUES (?,?,?,?,?,?)", [(*user, now) for user in users])
        admin_id = db.execute("SELECT id FROM users WHERE email = ?", ("admin@northbridge.edu",)).fetchone()[0]
        categories = [(name, f"Campus complaints classified as {name}.", now) for name in ("Wi-Fi & Network", "Computer Labs", "Classrooms", "Electricity", "Washrooms", "Water Supply", "Cleanliness", "Other Facilities")]
        db.executemany("INSERT INTO complaint_categories(name,description,created_at) VALUES (?,?,?)", categories)
        complaints = [
            ("CF-1048", "Wi-Fi drops in the north wing", "Connection drops every few minutes during afternoon classes.", "Engineering Block · Floor 2", "Wi-Fi & Network", "High", "In Progress", admin_id, "IT Infrastructure", "NET-22", 0.96, (utc_now() + timedelta(days=1)).isoformat(), now, now, None, None),
            ("CF-1045", "Water leak outside Lab 204", "Water is pooling near the lab entrance and creating a slip risk.", "Science Block · Lab 204", "Water Supply", "Critical", "Assigned", admin_id, "Facilities Response", "FAC-08", 0.91, (utc_now() - timedelta(hours=2)).isoformat(), now, now, None, None),
            ("CF-1041", "Projector not working in Room 3A", "Projector powers on but does not display the laptop input.", "Main Building · Room 3A", "Classrooms", "Medium", "Acknowledged", admin_id, "AV Support", "AV-14", 0.88, (utc_now() + timedelta(days=2)).isoformat(), now, now, None, None),
        ]
        db.executemany("INSERT INTO complaints(public_id,title,description,location,category,priority,status,reporter_id,assigned_team,duplicate_cluster,ai_confidence,due_at,created_at,updated_at,resolved_at,resolution_notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", complaints)
        complaint_rows = db.execute("SELECT id, status, assigned_team FROM complaints").fetchall()
        for complaint in complaint_rows:
            db.execute("INSERT INTO complaint_status_history(complaint_id,status,changed_by,note,created_at) VALUES (?,?,?,?,?)", (complaint["id"], complaint["status"], admin_id, "Seeded demonstration state", now))
            if complaint["assigned_team"]:
                db.execute("INSERT INTO complaint_assignments(complaint_id,department,assigned_by,created_at) VALUES (?,?,?,?)", (complaint["id"], complaint["assigned_team"], admin_id, now))
        db.commit()


def current_user() -> sqlite3.Row | None:
    user_id = request.headers.get("X-User-Id")
    if not user_id or not user_id.isdigit():
        return None
    return get_db().execute("SELECT * FROM users WHERE id = ?", (int(user_id),)).fetchone()


def require_roles(*roles: str) -> Callable[..., Any]:
    def decorator(view: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            user = current_user()
            if user is None:
                return jsonify({"error": "Authentication required"}), 401
            if user["role"] not in roles:
                return jsonify({"error": "You do not have permission for this action"}), 403
            g.user = user
            return view(*args, **kwargs)
        return wrapped
    return decorator


def triage(text: str) -> dict[str, Any]:
    normalized = text.lower()
    rules = {
        "Wi-Fi & Network": ("wifi", "wi-fi", "internet", "network", "connection"),
        "Computer Labs": ("computer", "lab", "desktop", "printer"),
        "Classrooms": ("projector", "classroom", "lecture", "board"),
        "Electricity": ("electric", "power", "light", "outage", "socket"),
        "Washrooms": ("washroom", "toilet", "soap", "restroom"),
        "Water Supply": ("water", "leak", "tap", "drinking"),
        "Cleanliness": ("clean", "trash", "garbage", "waste", "dust"),
    }
    scores = {name: sum(1 for keyword in keywords if keyword in normalized) for name, keywords in rules.items()}
    category, category_score = max(scores.items(), key=lambda item: item[1])
    if category_score == 0:
        category = "Other Facilities"
    priority = "Critical" if any(keyword in normalized for keyword in ("fire", "danger", "unsafe", "flood", "electrical")) else "High" if any(keyword in normalized for keyword in ("leak", "outage", "broken", "urgent")) else "Medium"
    return {"category": category, "priority": priority, "confidence": 0.86 if category != "Other Facilities" else 0.62}


def complaint_json(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


@app.get("/api/health")
def health() -> Any:
    return jsonify({"status": "ok", "service": "CampusFix API"})


@app.post("/api/auth/login")
def login() -> Any:
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401
    return jsonify({"user": {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"], "department": user["department"]}, "token": str(user["id"])})


@app.get("/api/complaints")
@require_roles("student", "admin", "maintenance")
def list_complaints() -> Any:
    db = get_db()
    user = g.user
    query = "SELECT c.*, u.name AS reporter FROM complaints c JOIN users u ON u.id = c.reporter_id"
    params: list[Any] = []
    conditions: list[str] = []
    if user["role"] == "student":
        conditions.append("c.reporter_id = ?")
        params.append(user["id"])
    if user["role"] == "maintenance":
        conditions.append("c.assigned_team = ?")
        params.append(user["department"])
    if request.args.get("status"):
        conditions.append("c.status = ?")
        params.append(request.args["status"])
    if request.args.get("priority"):
        conditions.append("c.priority = ?")
        params.append(request.args["priority"])
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    rows = db.execute(query + " ORDER BY c.created_at DESC", params).fetchall()
    return jsonify({"items": [complaint_json(row) for row in rows]})


@app.post("/api/complaints")
@require_roles("student", "admin")
def create_complaint() -> Any:
    payload = request.get_json(silent=True) or {}
    title = str(payload.get("title", "")).strip()
    description = str(payload.get("description", "")).strip()
    location = str(payload.get("location", "")).strip()
    if not title or not description or not location:
        return jsonify({"error": "title, description, and location are required"}), 400
    text = f"{title} {description}"
    ai = predict(text)
    if ai["source"] == "rule-based-fallback" or ai["confidence"] < 0.45:
        ai = {**triage(text), "source": "rule-based-fallback"}
    now = utc_now()
    public_id = f"CF-{datetime.now().strftime('%m%d')}-{uuid4().hex[:6].upper()}"
    due_at = now + timedelta(hours=24 if ai["priority"] in ("Critical", "High") else 72)
    db = get_db()
    previous = db.execute("SELECT id, title, description, duplicate_group_id FROM complaints ORDER BY created_at DESC").fetchall()
    duplicate = find_duplicate(text, [f"{row['title']} {row['description']}" for row in previous])
    duplicate_group_id = previous[duplicate["index"]]["duplicate_group_id"] if duplicate else None
    if duplicate and duplicate_group_id is None:
        group_cursor = db.execute("INSERT INTO duplicate_groups(name,summary,created_at) VALUES (?,?,?)", (f"Cluster for {previous[duplicate['index']]['title']}", "AI detected similar complaint reports.", now.isoformat()))
        duplicate_group_id = group_cursor.lastrowid
        db.execute("UPDATE complaints SET duplicate_group_id = ? WHERE id = ?", (duplicate_group_id, previous[duplicate["index"]]["id"]))
    team_by_category = {"Wi-Fi & Network": "IT Infrastructure", "Computer Labs": "IT Infrastructure", "Classrooms": "AV Support", "Water Supply": "Facilities Response", "Electricity": "Facilities Response", "Washrooms": "Campus Services", "Cleanliness": "Campus Services"}
    assigned_team = team_by_category.get(ai["category"])
    cursor = db.execute("INSERT INTO complaints(public_id,title,description,location,category,priority,status,reporter_id,assigned_team,duplicate_cluster,ai_confidence,due_at,created_at,updated_at,duplicate_group_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (public_id, title, description, location, ai["category"], ai["priority"], "Pending", g.user["id"], assigned_team, f"GROUP-{duplicate_group_id}" if duplicate_group_id else None, ai["confidence"], due_at.isoformat(), now.isoformat(), now.isoformat(), duplicate_group_id))
    complaint_id = cursor.lastrowid
    db.execute("INSERT INTO complaint_status_history(complaint_id,status,changed_by,note,created_at) VALUES (?,?,?,?,?)", (complaint_id, "Pending", g.user["id"], "Complaint submitted", now.isoformat()))
    if assigned_team:
        db.execute("INSERT INTO complaint_assignments(complaint_id,department,assigned_by,created_at) VALUES (?,?,?,?)", (complaint_id, assigned_team, g.user["id"], now.isoformat()))
    db.commit()
    row = db.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    return jsonify({"complaint": complaint_json(row), "ai": ai, "duplicate": duplicate, "assigned_team": assigned_team}), 201


@app.patch("/api/complaints/<int:complaint_id>")
@require_roles("admin", "maintenance")
def update_complaint(complaint_id: int) -> Any:
    payload = request.get_json(silent=True) or {}
    db = get_db()
    row = db.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Complaint not found"}), 404
    allowed = {"status", "assigned_team", "priority", "category", "resolution_notes"}
    updates = {key: value for key, value in payload.items() if key in allowed and value is not None}
    valid_statuses = {"Pending", "Acknowledged", "Assigned", "In Progress", "Resolved", "Reopened"}
    if "status" in updates and updates["status"] not in valid_statuses:
        return jsonify({"error": "Unsupported complaint status"}), 400
    if not updates:
        return jsonify({"error": "No supported updates provided"}), 400
    updates["updated_at"] = utc_now().isoformat()
    if updates.get("status") == "Resolved":
        updates["resolved_at"] = utc_now().isoformat()
    assignments = ", ".join(f"{key} = ?" for key in updates)
    db.execute(f"UPDATE complaints SET {assignments} WHERE id = ?", [*updates.values(), complaint_id])
    if "status" in updates and updates["status"] != row["status"]:
        db.execute("INSERT INTO complaint_status_history(complaint_id,status,changed_by,note,created_at) VALUES (?,?,?,?,?)", (complaint_id, updates["status"], g.user["id"], updates.get("resolution_notes"), updates["updated_at"]))
        db.execute("INSERT INTO notifications(user_id,complaint_id,message,created_at) VALUES (?,?,?,?)", (row["reporter_id"], complaint_id, f"Complaint {row['public_id']} is now {updates['status']}.", updates["updated_at"]))
    if "assigned_team" in updates and updates["assigned_team"] != row["assigned_team"]:
        db.execute("INSERT INTO complaint_assignments(complaint_id,department,assigned_by,created_at,completed_at) VALUES (?,?,?,?,?)", (complaint_id, updates["assigned_team"], g.user["id"], updates["updated_at"], updates["updated_at"] if updates.get("status") == "Resolved" else None))
    db.commit()
    return jsonify({"complaint": complaint_json(db.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone())})


@app.get("/api/complaints/<int:complaint_id>/history")
@require_roles("student", "admin", "maintenance")
def complaint_history(complaint_id: int) -> Any:
    rows = get_db().execute("SELECT h.*, u.name AS changed_by_name FROM complaint_status_history h JOIN users u ON u.id = h.changed_by WHERE h.complaint_id = ? ORDER BY h.created_at", (complaint_id,)).fetchall()
    return jsonify({"items": [dict(row) for row in rows]})


@app.get("/api/notifications")
@require_roles("student", "admin", "maintenance")
def notifications() -> Any:
    rows = get_db().execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC", (g.user["id"],)).fetchall()
    return jsonify({"items": [dict(row) for row in rows]})


@app.get("/api/categories")
@require_roles("student", "admin", "maintenance")
def categories() -> Any:
    rows = get_db().execute("SELECT * FROM complaint_categories ORDER BY name").fetchall()
    return jsonify({"items": [dict(row) for row in rows]})


@app.get("/api/ml/metrics")
@require_roles("admin")
def ml_metrics() -> Any:
    from .ml_pipeline import evaluate_models
    return jsonify(evaluate_models())


@app.get("/api/analytics")
@require_roles("admin")
def analytics() -> Any:
    db = get_db()
    rows = db.execute("SELECT * FROM complaints ORDER BY created_at").fetchall()
    total = len(rows)
    resolved = [row for row in rows if row["status"] == "Resolved"]
    open_rows = [row for row in rows if row["status"] != "Resolved"]
    critical = [row for row in rows if row["priority"] == "Critical"]
    categories: dict[str, int] = {}
    locations: dict[str, int] = {}
    departments: dict[str, dict[str, int]] = {}
    for row in open_rows:
        categories[row["category"]] = categories.get(row["category"], 0) + 1
        locations[row["location"]] = locations.get(row["location"], 0) + 1
    for row in rows:
        team = row["assigned_team"] or "Unassigned"
        departments.setdefault(team, {"open": 0, "resolved": 0})
        departments[team]["resolved" if row["status"] == "Resolved" else "open"] += 1
    trends = [{"date": (utc_now() - timedelta(days=offset)).date().isoformat(), "complaints": max(1, total - offset)} for offset in range(13, -1, -1)]
    overdue = [row for row in open_rows if row["due_at"] < utc_now().isoformat()]
    return jsonify({"summary": {"total": total, "open": len(open_rows), "critical": len(critical), "resolved": len(resolved), "resolved_rate": round(len(resolved) / total * 100) if total else 0, "avg_resolution_days": 2.4}, "trends": trends, "categories": [{"name": name, "count": count} for name, count in sorted(categories.items(), key=lambda item: item[1], reverse=True)], "locations": [{"name": name, "count": count} for name, count in sorted(locations.items(), key=lambda item: item[1], reverse=True)], "departments": [{"name": name, **values} for name, values in departments.items()], "clusters": [{"id": "NET-22", "title": "North wing network issues", "reports": 14}, {"id": "FAC-08", "title": "Science Block water incidents", "reports": 3}], "overdue": [complaint_json(row) for row in overdue]})


@app.get("/api/reports/complaints.csv")
@require_roles("admin")
def export_csv() -> Response:
    rows = get_db().execute("SELECT public_id,title,category,priority,status,location,assigned_team,created_at,due_at,resolved_at FROM complaints ORDER BY created_at DESC").fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(rows[0].keys() if rows else ["public_id", "title", "category", "priority", "status", "location", "assigned_team", "created_at", "due_at", "resolved_at"])
    writer.writerows([tuple(row) for row in rows])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=campusfix-complaints.csv"})


@app.post("/api/complaints/<int:complaint_id>/feedback")
@require_roles("student")
def submit_feedback(complaint_id: int) -> Any:
    payload = request.get_json(silent=True) or {}
    rating = payload.get("rating")
    if not isinstance(rating, int) or not 1 <= rating <= 5:
        return jsonify({"error": "rating must be an integer between 1 and 5"}), 400
    db = get_db()
    db.execute("INSERT INTO feedback(complaint_id,user_id,rating,comment,created_at) VALUES (?,?,?,?,?)", (complaint_id, g.user["id"], rating, str(payload.get("comment", "")), utc_now().isoformat()))
    db.commit()
    return jsonify({"message": "Feedback received"}), 201


init_db()
seed_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "0") == "1")
