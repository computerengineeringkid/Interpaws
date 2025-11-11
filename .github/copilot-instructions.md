# Copilot instructions for Interpaws

Purpose: Help AI coding agents work productively in this repo by capturing how the app is structured, how it runs, and project-specific patterns to follow.

## Big picture

- Full-stack VPMS: FastAPI backend + Next.js App Router frontend + Postgres (pgvector) + Ollama LLM.
- Two auth realms with separate tokens: clients and staff (admins). Do not mix them.
- AI is first-class: sentence-transformers for embeddings (384-dim); Ollama (model "llama3") for chat and natural language recommendations.

## Run/develop

- Preferred: use Docker.
  - Start: `./start.sh` (wait 1–2 min for healthchecks, migrations, builds).
  - Manual: `docker-compose up --build -d`; logs: `docker-compose logs -f`; stop: `docker-compose down`.
  - API docs live at http://localhost:8000/docs; app at http://localhost:3000.
- Create an admin user after first boot (required for admin endpoints): POST /staff/ with name/email/password (see QUICK_START.md).
- Frontend proxies backend: use relative URLs `/api/...` in the browser; Next.js rewrites them to `http://backend:8000` (see `frontend/next.config.mjs`).

## Backend (FastAPI)

- Single app module: `backend/app/main.py` hosts routes. Schemas in `schemas.py`, models in `models.py`, auth utilities in `auth.py`, embeddings & LLM in `ai_services.py`.
- DB: SQLAlchemy + Alembic migrations in `backend/alembic/versions`. Vector columns via `pgvector.sqlalchemy.Vector(384)`.
- Startup: creates `vector` extension and waits for DB; migrations run via compose command `alembic upgrade head`.
- Auth patterns:
  - Client login: `POST /token` -> JWT with `sub=email`, validated by `get_current_user`.
  - Admin login: `POST /staff/login` -> JWT validated by `get_current_admin_user`.
  - Protect admin routes with the admin dependency; client-only routes use the client dependency.
- AI patterns:
  - Embeddings: `get_embedding(text)` from `ai_services.py`; store in vector columns.
  - Similarity: use `model.vectorcol.l2_distance(embedding)` ordering in queries.
  - Chat/recs: `get_ollama_recommendation(prompt)` against model `llama3` (ensure model pulled in the Ollama service).

## Frontend (Next.js App Router)

- Auth lives in `src/context/AuthContext.js` with two flows: `login` (client) hits `/api/token`; `adminLogin` hits `/api/staff/login`. Tokens stored in localStorage with `userRole` = `client` or `admin`.
- Route guards: `ProtectedRoute` (client) and `AdminProtectedRoute` (admin). Admin pages sit under `src/app/admin/...` and use the admin guard in their layouts/pages.
- API usage: always call relative `/api/...` so rewrites route to backend; attach `Authorization: Bearer <token>` where required. Example components: `ClientBookingForm` calls `/api/suggest_slots`; `AIChat` calls `/api/chat`.

## Conventions to follow

- Keep models/schemas in their dedicated files; only import Pydantic types into `main.py` for request/response models.
- When adding vector-backed features: create a migration with `Vector(384)`, embed with `get_embedding()`, and query with `l2_distance` ordering.
- For new protected endpoints: decide client vs admin; wire the correct dependency (`get_current_user` vs `get_current_admin_user`).
- Prefer adding new endpoints to `main.py` grouped by feature with tags (e.g., "Surgeries", "Medications"). Mirror shapes in `schemas.py`.

## Integration examples

- Client self endpoints: `GET /clients/me`, `GET /bookings/me`, `POST /preferences/me` require client JWT.
- Admin CRUD: `/staff/*`, `/surgeries/*`, `/medications/*` require staff JWT; see `AdminNav` and admin pages for frontend usage.
- AI flows: `POST /suggest_slots` returns `{ generative_recommendation, suggested_staff[] }`; `POST /chat` returns `{ response }`. See `ClientBookingForm.js` and `AIChat.js` for request bodies.

## Pitfalls and gotchas

- Don’t call backend at absolute `http://localhost:8000` from the browser; use `/api/...` to work in Docker and dev.
- Tokens are not interchangeable: a client token will fail on admin routes and vice versa.
- Ollama model name in code is `llama3`; pull this model in the `ollama` container if responses fail on first run.
- Booking conflicts: availability is enforced by `check_availability` in `booking_logic.py` (overlap rule) when creating bookings.
