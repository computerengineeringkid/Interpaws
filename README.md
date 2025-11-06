# Interpaws

Last updated: 2025-11-06

## Overview

Interpaws is a full-stack veterinary clinic management application with a FastAPI backend, Next.js frontend, and PostgreSQL database. The project is containerized with Docker Compose for easy development and deployment.

## Tech Stack

### Backend

- Language: Python 3.10+
- Web framework: FastAPI
- ASGI server: Uvicorn
- ORM: SQLAlchemy
- Database driver: psycopg2-binary

### Frontend

- Framework: Next.js 16 (App Router)
- Language: JavaScript
- Styling: Tailwind CSS
- Runtime: Node.js 20

### Database

- PostgreSQL 15 (Alpine)

## Repository Structure

```
Interpaws/
├── backend/
│   ├── app/
│   │   ├── __init__.py      # Package initialization
│   │   ├── main.py          # FastAPI app entrypoint with startup handlers
│   │   ├── database.py      # Database configuration and session management
│   │   └── models.py        # SQLAlchemy data models (Clinic, Staff)
│   ├── Dockerfile           # Backend container definition
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── (admin)/     # Admin route group
│   │   │   ├── (client)/    # Client-facing route group
│   │   │   ├── layout.js    # Root layout
│   │   │   ├── page.js      # Home page
│   │   │   └── globals.css  # Global styles
│   │   └── components/      # Shared React components
│   ├── Dockerfile           # Frontend container definition
│   └── package.json         # Node.js dependencies
├── docker-compose.yml       # Multi-service orchestration
└── README.md                # This file
```

## Getting Started

### Prerequisites

- Docker Desktop installed and running
- Git (for cloning the repository)

### Quick Start with Docker (Recommended)

1. **Clone the repository and navigate to the project directory:**

```bash
git clone https://github.com/computerengineeringkid/Interpaws.git
cd Interpaws
```

2. **Start all services with Docker Compose:**

```bash
docker compose up -d --build
```

This will start three services:

- `db`: PostgreSQL database on port 5432 (internal)
- `backend`: FastAPI server on http://localhost:8000
- `frontend`: Next.js app on http://localhost:3000

3. **Access the application:**

- Backend API: http://localhost:8000
- API Documentation (Swagger): http://localhost:8000/docs
- API Documentation (ReDoc): http://localhost:8000/redoc
- Frontend App: http://localhost:3000

4. **View logs:**

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f db
```

5. **Stop services:**

```bash
docker compose down

# Stop and remove volumes (clears database)
docker compose down -v
```

### Local Development (Without Docker)

If you prefer to run services individually for development:

#### Backend Setup

1. **Create and activate a Python virtual environment:**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

3. **Set up PostgreSQL and update `DATABASE_URL`:**

Ensure PostgreSQL is running locally and update the connection string in `backend/app/database.py` or set the `DATABASE_URL` environment variable.

4. **Run the backend:**

```bash
uvicorn app.main:app --reload
```

#### Frontend Setup

1. **Install Node.js dependencies:**

```bash
cd frontend
npm install
```

2. **Run the development server:**

```bash
npm run dev
```

## Current API

The backend currently exposes the following endpoints:

- `GET /` → Returns a welcome message

Example response:

```json
{
  "message": "Welcome to the Interpaws API!"
}
```

### Database Models

- **Clinic**: `id`, `name`
- **Staff**: `id`, `name`, `role`

## Architecture Notes

### Backend

- **Database connection**: Uses environment variable `DATABASE_URL` with fallback to localhost
- **Startup handling**: Implements retry logic for database connections with healthcheck
- **Live reload**: Volume-mounted `backend/app` directory for hot-reloading during development

### Frontend

- **Route groups**: Uses Next.js route groups `(admin)` and `(client)` for organizing pages
- **Components**: Shared components stored in `src/components/`
- **Live reload**: Volume-mounted source with separate `node_modules` volume

### Docker Services

- **db**: Postgres with healthcheck, persistent volume for data
- **backend**: Waits for healthy database before starting
- **frontend**: Depends on backend service

## Development Notes

- Keep endpoints small and focused. Add Pydantic models for request/response validation as features grow.
- Prefer dependency injection (FastAPI Depends) for services like database sessions, auth, or external clients.
- Use Next.js App Router conventions for routing and layouts.
- Add tests as we go (pytest + httpx for backend, Jest/React Testing Library for frontend).
- All code changes auto-reload in Docker thanks to volume mounts.

## Project Roadmap

### Completed ✅

- [x] Backend structure with FastAPI and SQLAlchemy
- [x] Frontend structure with Next.js and Tailwind CSS
- [x] Docker Compose orchestration with healthchecks
- [x] PostgreSQL database integration
- [x] Basic data models (Clinic, Staff)
- [x] Development environment with live reload

### Next Steps

- [ ] Add environment-based settings (pydantic-settings, .env files)
- [ ] Implement authentication and authorization
- [ ] Add database migrations (Alembic)
- [ ] Create CRUD endpoints for clinics and staff
- [ ] Build admin and client UI components
- [ ] Add comprehensive error handling
- [ ] Implement logging and monitoring
- [ ] Add unit and integration tests
- [ ] Configure CI/CD pipeline
- [ ] Add health-check endpoints

## Troubleshooting

### Docker Issues

**Services won't start:**

```bash
# Check service status
docker compose ps

# View logs for errors
docker compose logs

# Restart services
docker compose restart
```

**Database connection errors:**

- Ensure the `db` service shows as "healthy": `docker compose ps`
- The backend has built-in retry logic and will wait for the database
- If issues persist, recreate volumes: `docker compose down -v && docker compose up -d --build`

**Port conflicts:**

- If ports 3000 or 8000 are already in use, stop conflicting services or modify ports in `docker-compose.yml`

**Build cache issues:**

```bash
# Force rebuild without cache
docker compose build --no-cache
docker compose up -d
```

### Local Development Issues

**Backend:**

- Ensure PostgreSQL is running and `DATABASE_URL` is set correctly
- Verify virtual environment is activated: `which python` should show `.venv/bin/python`
- Install dependencies: `pip install -r backend/requirements.txt`

**Frontend:**

- Clear Next.js cache: `rm -rf frontend/.next`
- Reinstall dependencies: `cd frontend && rm -rf node_modules && npm install`
- Check Node.js version: `node --version` (should be 20+)

**Database:**

- Verify PostgreSQL is running: `docker compose logs db`
- Manually access the database: `docker compose exec db psql -U user -d interpawsdb`

## Contributing

- Open an issue or PR with a brief description of changes.
- Keep changes scoped and include basic tests where possible.
- Follow the existing code style and project structure.
- Update documentation as needed.

## License

[Add your license information here]

---

**Happy coding! 🐾**
