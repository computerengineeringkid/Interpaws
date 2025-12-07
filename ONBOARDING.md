# Interpaws - Onboarding Guide

Get up and running with Interpaws in minutes.

## Prerequisites

- **Docker Desktop** - [Download here](https://www.docker.com/products/docker-desktop/)
- **Git** - For cloning the repository
- **Ollama** (optional) - For local AI features, or use the containerized version

## Quick Start

### 1. Clone and Start

```bash
git clone https://github.com/computerengineeringkid/Interpaws.git
cd Interpaws
./start.sh
```

Or manually with Docker Compose:

```bash
docker-compose up --build -d
```

### 2. Wait for Services

The first startup takes a few minutes to:
- Build containers
- Initialize the PostgreSQL database with pgvector
- Run database migrations
- Start the AI embedding service

Check status:

```bash
docker-compose ps
```

All services should show "healthy" or "running".

### 3. Create an Admin Account

```bash
curl -X POST "http://localhost:8000/staff/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dr. Admin",
    "email": "admin@interpaws.com",
    "password": "admin123",
    "role": "Veterinarian",
    "skills_description": "General practice, surgery, diagnostics"
  }'
```

### 4. Access the Application

| Portal | URL |
|--------|-----|
| Client Portal | http://localhost:3000 |
| Admin Login | http://localhost:3000/admin/admin-login |
| Admin Dashboard | http://localhost:3000/admin/dashboard |
| API Documentation | http://localhost:8000/docs |

## Test Accounts

After seeding (if enabled), you can use:

**Client:**
- Register a new account at http://localhost:3000/register

**Admin:**
- Email: `admin@interpaws.com`
- Password: `admin123` (from the curl command above)

## Common Docker Commands

```bash
# Start services
docker-compose up -d

# Start with rebuild
docker-compose up --build -d

# View logs (all services)
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db

# Stop services
docker-compose down

# Stop and remove volumes (reset database)
docker-compose down -v

# Restart a specific service
docker-compose restart backend
```

## Development Setup

### Backend Development

The backend auto-reloads when you change Python files (volume-mounted).

```bash
# Access backend container shell
docker-compose exec backend bash

# Run database seed manually
docker-compose exec backend python -m app.seed

# Check database
docker-compose exec db psql -U postgres -d interpaws
```

### Frontend Development

The frontend also supports hot-reload via Next.js.

```bash
# Access frontend container
docker-compose exec frontend sh

# Or run locally (outside Docker)
cd frontend
npm install
npm run dev
```

### Database Access

```bash
# Connect to PostgreSQL
docker-compose exec db psql -U postgres -d interpaws

# Common queries
\dt                          # List tables
SELECT * FROM staff;         # View staff
SELECT * FROM clients;       # View clients
SELECT * FROM bookings;      # View bookings
\q                           # Exit
```

## Verifying the Setup

### 1. Health Check

```bash
curl http://localhost:8000/
# Should return: {"status":"healthy","message":"Interpaws API is running"}
```

### 2. Register a Client

```bash
curl -X POST http://localhost:8000/clients/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com","password":"testpass123"}'
```

### 3. Login

```bash
curl -X POST http://localhost:8000/token \
  -d "username=test@example.com&password=testpass123"
```

### 4. Test AI Features

```bash
# Get AI staff recommendations
curl -X POST http://localhost:8000/suggest_slots \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"complaint":"My dog has been limping","date":"2025-01-15"}'
```

## Troubleshooting

### Services Won't Start

```bash
# Check what's running
docker ps -a

# Check logs for errors
docker-compose logs

# Rebuild everything
docker-compose down -v
docker-compose up --build -d
```

### Database Connection Errors

```bash
# Ensure DB is healthy
docker-compose ps db

# Reset database
docker-compose down -v
docker-compose up -d
```

### Port Conflicts

If ports 3000 or 8000 are in use:

```bash
# Find what's using a port
lsof -i :3000
lsof -i :8000

# Kill the process or modify docker-compose.yml ports
```

### Frontend Not Loading

```bash
# Clear and rebuild frontend
docker-compose down
docker volume rm interpaws_frontend_node_modules 2>/dev/null
docker-compose up --build frontend
```

### AI/Chat Not Working

```bash
# Check Ollama status
docker-compose logs ollama

# The first run may need to pull the model
docker-compose exec ollama ollama pull llama3
```

### Can't Login

1. Clear browser localStorage (DevTools > Application > Clear site data)
2. Verify credentials with API directly
3. Check backend logs: `docker-compose logs backend`

## Environment Variables

The application uses these environment variables (set in `docker-compose.yml`):

| Variable | Service | Description |
|----------|---------|-------------|
| `DATABASE_URL` | backend | PostgreSQL connection string |
| `SECRET_KEY` | backend | JWT signing key |
| `OLLAMA_HOST` | backend | Ollama API endpoint |
| `NEXT_PUBLIC_API_URL` | frontend | Backend API URL |

## Next Steps

Once setup is complete:

1. **Explore the Client Portal** - Register, add pets, book appointments
2. **Set Up the Admin Dashboard** - Add staff, medications, schedule surgeries
3. **Test AI Features** - Try the chat assistant and staff recommendations
4. **Read the [Project Documentation](PROJECT.md)** - Understand the architecture and API

## Getting Help

- **API Documentation:** http://localhost:8000/docs (interactive Swagger UI)
- **GitHub Issues:** Report bugs or request features
- **Project Documentation:** See [PROJECT.md](PROJECT.md) for technical details
