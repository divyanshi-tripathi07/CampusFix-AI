# CampusFix AI

CampusFix AI is a production-style React + Vite prototype for intelligent campus complaint operations. It includes a student reporting flow, AI-assisted category and priority signals, duplicate issue clustering, assignment recommendations, lifecycle tracking, notifications, and resolution feedback.

The repository also includes a Flask + SQLite API under `backend/` with hashed-password login, student/admin/maintenance authorization, complaint lifecycle endpoints, rule-based AI triage fallback, analytics aggregation, SLA overdue detection, CSV export, and pytest coverage.

## Run locally

```bash
npm install
npm run dev
```

Then open the local URL shown by Vite. Build verification:

```bash
npm run build
```

## Run the API

```bash
python -m pip install -r backend/requirements.txt
python -m backend.app
```

Demo accounts are seeded on first start: `admin@northbridge.edu` / `admin-demo`, `student@northbridge.edu` / `student-demo`, and `maintenance@northbridge.edu` / `staff-demo`. The API currently uses an `X-User-Id` header after login while the frontend authentication contract is being connected; replace this with short-lived signed tokens before production deployment.

Run backend tests with `python -m pytest backend/test_app.py -q`. Docker Compose starts the API with a persistent SQLite volume: `docker compose up --build`.

## Architecture and workflow

The React/Vite client is the presentation layer. Flask exposes protected REST endpoints over the typed domain model. SQLite is accessed through a small database gateway in `backend/app.py`; the schema is additive and can later move to PostgreSQL with the same relational boundaries. The ML module is isolated so the classifier can be replaced by a trained service without changing the complaint API.

1. A student logs in and submits a validated title, description, and location.
2. The ML pipeline runs TF-IDF + logistic regression. If dependencies or confidence are unavailable, the explainable keyword fallback is used.
3. Cosine similarity compares the new report with existing reports; related reports receive a duplicate group.
4. Category and priority recommend a department, create an assignment row, and set the SLA due time.
5. Admin or maintenance staff update status and notes. Every transition is recorded in status history and notifies the reporter.
6. Admin analytics aggregate complaints, categories, locations, department load, duplicate groups, and overdue SLA records.

## Project structure

```text
backend/
	app.py             Flask API, auth guards, schema initialization, seed data
	ml_pipeline.py     Labeled dataset, TF-IDF models, metrics, duplicate similarity
	ml_train.py        Reproducible training/evaluation command
	schema.sql         Canonical relational schema reference
	test_app.py        Authentication and workflow tests
src/
	main.tsx           App shell, complaint queue, student report flow
	AnalyticsView.tsx  Admin KPI, Chart.js, filtering, SLA and export view
	styles.css         Responsive visual system
Dockerfile           Containerized API
docker-compose.yml   API plus persistent SQLite volume
.github/workflows/ci.yml  Backend pytest and frontend build CI
```

## Database model

The initialized database contains `users`, `complaint_categories`, `complaints`, `complaint_assignments`, `duplicate_groups`, `complaint_status_history`, `notifications`, and `feedback` (resolution feedback). Complaints belong to users, assignments and status history belong to complaints, duplicate groups can contain many complaints, and notifications/feedback link users to complaint events. All operational tables carry UTC ISO timestamps; role and feedback rating constraints are enforced in SQLite and request validation.

Initialization is idempotent: `init_db()` executes `CREATE TABLE IF NOT EXISTS` and applies the additive `duplicate_group_id` migration for older local databases. For a fresh database, set `CAMPUSFIX_DATABASE` and start the API. For a production migration, replace this initializer with Alembic revisions and run them during deployment.

## ML evaluation

Run `python -m backend.ml_train` to train the labeled starter dataset and print the held-out category accuracy, training example count, and priority label count. The current compact demonstration dataset reports the measured baseline; it is intentionally small and should be replaced with reviewed campus history before operational use. The API exposes the same metrics at `GET /api/ml/metrics` for admins.

## Future enhancements and interview discussion points

- Replace development `X-User-Id` identity headers with short-lived JWT or secure server sessions, refresh-token rotation, CSRF protection, rate limiting, and audit logging.
- Add Alembic migrations, PostgreSQL, object storage for images, and background jobs for notifications and model retraining.
- Grow the labeled dataset, add cross-validation and macro F1/precision/recall, calibrate confidence, and compare linear models with sentence embeddings.
- Add pagination, full-text search, geospatial campus maps, accessibility review, and Playwright workflow coverage.
- Add administrator prediction overrides as an explicit audit table and connect the React analytics view to `/api/analytics` instead of its demonstration dataset.

The current app uses local mock data and browser state so the interaction model can be evaluated without a backend. The next production step would be connecting the typed domain model to authentication, storage, an embedding/classification service, and a notification provider.
