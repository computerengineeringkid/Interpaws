# Interpaws

An AI-powered veterinary practice management system that uses vector embeddings to intelligently match pet complaints to staff expertise, provides a conversational booking assistant, and automates wellness outreach.

## Features

- **AI Staff Matching** - Semantic similarity search matches pet complaints to staff skills
- **Chat Assistant** - ReAct-style agent for booking and queries with conversation memory
- **Dual Authentication** - Separate client and admin portals with JWT-based security
- **Full VPMS** - Staff, surgery, medication, and booking management
- **Wellness Outreach** - Automated identification of pets due for care with AI-generated emails

## Tech Stack

**Backend:** FastAPI, PostgreSQL + pgvector, SQLAlchemy, sentence-transformers, Ollama
**Frontend:** Next.js 15, React 19, Tailwind CSS, shadcn/ui
**Infrastructure:** Docker, Docker Compose

## Quick Start

```bash
# Clone and start
git clone https://github.com/computerengineeringkid/Interpaws.git
cd Interpaws
docker-compose up --build -d

# Create admin account
curl -X POST "http://localhost:8000/staff/" \
  -H "Content-Type: application/json" \
  -d '{"name":"Admin","email":"admin@interpaws.com","password":"admin123","role":"Veterinarian","skills_description":"General practice"}'
```

**Access:**
- Client Portal: http://localhost:3000
- Admin Dashboard: http://localhost:3000/admin/admin-login
- API Docs: http://localhost:8000/docs

## Documentation

| Document | Description |
|----------|-------------|
| [ONBOARDING.md](ONBOARDING.md) | Setup guide, development workflow, troubleshooting |
| [PROJECT.md](PROJECT.md) | Architecture, database schema, API reference |

## Project Structure

```
Interpaws/
├── backend/           # FastAPI application
│   ├── app/           # Source code
│   │   ├── main.py    # Endpoints
│   │   ├── models.py  # Database models
│   │   ├── agent/     # AI chat agent
│   │   └── ...
│   └── alembic/       # Migrations
├── frontend/          # Next.js application
│   └── src/app/       # Pages and components
├── docker-compose.yml
└── start.sh
```

## License

[MIT](LICENSE)
