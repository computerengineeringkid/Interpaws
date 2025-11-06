# Interpaws

Last updated: 2025-11-06

## Overview

Interpaws is a FastAPI-based backend service. Right now, it exposes a simple root endpoint and will grow to include core features for the project (routes, data models, auth, etc.).

## Tech Stack

- Language: Python (3.10+ recommended)
- Web framework: FastAPI
- ASGI server: Uvicorn

## Repository Structure

```
Interpaws/
├── backend/
│   └── venv/
│       └── main.py    # FastAPI app entrypoint (app object lives here)
└── README.md          # This file
```

Note: The app entrypoint currently lives under `backend/venv/`. Typically, application code is not stored in a folder named `venv` (which usually refers to a Python virtual environment). In a later cleanup, we can move it to something like `backend/app/main.py` and adjust the run command accordingly.

## Getting Started

### 1) Set up a Python environment

On macOS with zsh:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install fastapi uvicorn
```

If you already use a global environment management tool (Conda, pyenv, etc.), feel free to use that instead.

### 2) Run the development server

Using Uvicorn, pointing to the `main:app` module, and telling it where to find the file:

```bash
uvicorn --app-dir backend/venv main:app --reload
```

- App will start at: http://127.0.0.1:8000/
- Interactive API docs (Swagger UI): http://127.0.0.1:8000/docs
- ReDoc docs: http://127.0.0.1:8000/redoc

If/when we move the file to `backend/app/main.py`, the command would become:

```bash
uvicorn backend.app.main:app --reload
```

## Current API

- GET `/` → returns a JSON welcome message.

Example response:

```json
{ "message": "Welcome to the Interpaws API!" }
```

## Development Notes

- Keep endpoints small and focused. Add Pydantic models for request/response validation as features grow.
- Prefer dependency injection (FastAPI Depends) for services like database sessions, auth, or external clients.
- Add tests as we go (pytest + httpx recommended for FastAPI).

## Roadmap (draft)

- Organize source into `backend/app/` with routers, models, services, and config.
- Add a `requirements.txt` or `pyproject.toml` to lock dependencies.
- Introduce environment-based settings (pydantic-settings or similar).
- Add a health-check endpoint and basic status page.
- Configure CI for linting, typing, and tests.

## Troubleshooting

- If `uvicorn` can’t find `main:app`, ensure you used `--app-dir backend/venv` and that `main.py` contains `app = FastAPI()`.
- If you see module errors, verify your virtual environment is activated and dependencies are installed.

## Contributing

- Open an issue or PR with a brief description of changes.
- Keep changes scoped and include basic tests where possible.
