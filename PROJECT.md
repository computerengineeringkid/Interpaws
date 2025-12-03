# Interpaws - Project Documentation

Technical documentation for the Interpaws Veterinary Practice Management System.

## Architecture Overview

```
┌─────────────────┐
│    Frontend     │ :3000
│    (Next.js)    │
└────────┬────────┘
         │ /api/* proxy
┌────────▼────────┐
│     Backend     │ :8000
│    (FastAPI)    │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌───▼───┐
│  DB   │ │Ollama │ :11434
│(PG+   │ │ (LLM) │
│vector)│ └───────┘
└───────┘
```

## Tech Stack

### Backend
- **FastAPI** - Python web framework
- **SQLAlchemy** - ORM
- **PostgreSQL 15** with **pgvector** - Vector-enabled database
- **Alembic** - Database migrations
- **sentence-transformers** - Text embeddings (all-MiniLM-L6-v2)
- **Ollama** - Local LLM for chat and email generation
- **python-jose** - JWT authentication
- **passlib/bcrypt** - Password hashing

### Frontend
- **Next.js 15** - React framework (App Router)
- **React 19** - UI library
- **Tailwind CSS 4** - Styling
- **shadcn/ui** - Component library
- **React Context** - State management

### Infrastructure
- **Docker & Docker Compose** - Containerization
- **pgvector/pgvector:pg15** - PostgreSQL with vector support

## Repository Structure

```
Interpaws/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, all endpoints
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── database.py          # DB connection
│   │   ├── auth.py              # JWT authentication
│   │   ├── ai_services.py       # Embeddings & LLM
│   │   ├── booking_logic.py     # Availability logic
│   │   ├── seed.py              # Database seeding
│   │   ├── wellness_outreach.py # Proactive outreach
│   │   └── agent/               # AI chat agent
│   │       ├── core.py          # ReAct agent
│   │       ├── enhanced_core.py # Intent-routed agent
│   │       ├── tools.py         # Agent tools
│   │       └── intent_router.py # Intent classification
│   ├── alembic/                 # Database migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js pages
│   │   │   ├── page.js          # Client home
│   │   │   ├── login/           # Client login
│   │   │   ├── register/        # Client registration
│   │   │   ├── my-bookings/     # Client bookings
│   │   │   ├── preferences/     # Client preferences
│   │   │   └── admin/           # Admin section
│   │   │       ├── admin-login/
│   │   │       ├── dashboard/
│   │   │       ├── staff/
│   │   │       ├── surgeries/
│   │   │       ├── medications/
│   │   │       └── bookings/
│   │   ├── components/          # Reusable components
│   │   └── context/             # Auth context
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── start.sh
├── README.md
├── ONBOARDING.md
└── PROJECT.md
```

## Database Schema

### Core Models

**Clinic**
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| name | String | Clinic name |

**Client**
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| name | String | Client name |
| email | String | Unique email |
| hashed_password | String | bcrypt hash |
| clinic_id | Integer | FK to Clinic |

**Pet**
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| name | String | Pet name |
| species | String | e.g., "Dog", "Cat" |
| breed | String | Breed |
| date_of_birth | Date | Pet DOB |
| client_id | Integer | FK to Client |

**Staff**
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| name | String | Staff name |
| email | String | Unique email |
| hashed_password | String | bcrypt hash |
| role | String | e.g., "Veterinarian" |
| skills_description | String | Text description |
| skills_vector | Vector(384) | Embedding of skills |

**Booking**
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| start_time | DateTime | Appointment start |
| end_time | DateTime | Appointment end |
| status | String | confirmed/cancelled/completed |
| complaint_reason | String | Pet complaint text |
| complaint_vector | Vector(384) | Embedding of complaint |
| client_id | Integer | FK to Client |
| pet_id | Integer | FK to Pet |
| staff_id | Integer | FK to Staff |

**Surgery**
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| surgery_type | String | Type of surgery |
| notes | Text | Surgery notes |
| start_time | DateTime | Scheduled start |
| end_time | DateTime | Scheduled end |
| status | String | scheduled/in_progress/completed/cancelled |
| pet_id | Integer | FK to Pet |
| staff_id | Integer | FK to Staff |

**Medication**
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| name | String | Medication name |
| description | Text | Description |
| stock_quantity | Integer | Current stock |
| unit | String | e.g., "tablets", "ml" |

**Preferences**
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| details | Text | Preference text |
| details_vector | Vector(384) | Embedding |
| client_id | Integer | FK to Client |

**AIFeedbackLog**
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| booking_id | Integer | FK to Booking |
| staff_id | Integer | FK to Staff |
| client_complaint_vector | Vector(384) | Complaint embedding |
| staff_skills_vector | Vector(384) | Staff skills embedding |

## API Reference

### Authentication

#### Register Client
```http
POST /clients/
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "securepass123"
}
```

#### Client Login
```http
POST /token
Content-Type: application/x-www-form-urlencoded

username=john@example.com&password=securepass123
```

Response:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

#### Staff Login
```http
POST /staff/login
Content-Type: application/x-www-form-urlencoded

username=admin@interpaws.com&password=admin123
```

#### Get Current Client
```http
GET /clients/me
Authorization: Bearer {token}
```

### Bookings

#### Create Booking
```http
POST /bookings/
Authorization: Bearer {token}
Content-Type: application/json

{
  "pet_id": 1,
  "staff_id": 1,
  "start_time": "2025-01-15T10:00:00",
  "end_time": "2025-01-15T10:30:00",
  "complaint_reason": "Annual checkup"
}
```

#### Get Client's Bookings
```http
GET /bookings/me
Authorization: Bearer {token}
```

#### Get Bookings by Date
```http
GET /bookings/{date}
Authorization: Bearer {token}
```

#### Update Booking (Admin)
```http
PUT /bookings/{id}
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "status": "completed"
}
```

#### Delete Booking (Admin)
```http
DELETE /bookings/{id}
Authorization: Bearer {admin_token}
```

### Staff Management (Admin)

#### List Staff
```http
GET /staff/
```

#### Create Staff
```http
POST /staff/
Content-Type: application/json

{
  "name": "Dr. Smith",
  "email": "smith@clinic.com",
  "password": "pass123",
  "role": "Veterinarian",
  "skills_description": "Surgery, orthopedics, emergency care"
}
```

#### Update Staff
```http
PUT /staff/{id}
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "skills_description": "Updated skills"
}
```

#### Delete Staff
```http
DELETE /staff/{id}
Authorization: Bearer {admin_token}
```

### Surgeries (Admin)

#### List Surgeries
```http
GET /surgeries/
Authorization: Bearer {admin_token}

# With filters
GET /surgeries/?staff_id=1&status=scheduled&date=2025-01-15
```

#### Create Surgery
```http
POST /surgeries/
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "pet_id": 1,
  "staff_id": 1,
  "surgery_type": "Spay",
  "notes": "Routine procedure",
  "start_time": "2025-01-15T09:00:00",
  "end_time": "2025-01-15T10:00:00",
  "status": "scheduled"
}
```

#### Update Surgery
```http
PUT /surgeries/{id}
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "status": "completed"
}
```

### Medications (Admin)

#### List Medications
```http
GET /medications/
Authorization: Bearer {admin_token}
```

#### Create Medication
```http
POST /medications/
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "name": "Amoxicillin",
  "description": "Broad-spectrum antibiotic",
  "stock_quantity": 100,
  "unit": "tablets"
}
```

#### Update Medication
```http
PUT /medications/{id}
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "stock_quantity": 150
}
```

### AI Features

#### Get Staff Recommendations
```http
POST /suggest_slots
Authorization: Bearer {token}
Content-Type: application/json

{
  "complaint": "My dog has been limping for two days",
  "date": "2025-01-15"
}
```

Response:
```json
{
  "recommendations": [
    {
      "staff_id": 1,
      "name": "Dr. Smith",
      "role": "Veterinarian",
      "skills": "Orthopedics, surgery",
      "similarity_score": 0.89,
      "available_slots": ["10:00", "14:00", "15:30"]
    }
  ]
}
```

#### Chat with AI Assistant
```http
POST /chat
Authorization: Bearer {token}
Content-Type: application/json

{
  "message": "I need to book an appointment for my cat",
  "session_id": "user-123"
}
```

#### Smart Chat (Intent-Aware)
```http
POST /smart-chat
Authorization: Bearer {token}
Content-Type: application/json

{
  "message": "What appointments do I have next week?",
  "session_id": "user-123"
}
```

#### Log AI Feedback
```http
POST /log-feedback/
Authorization: Bearer {token}
Content-Type: application/json

{
  "booking_id": 1,
  "staff_id": 1
}
```

### Preferences

#### Save Preferences
```http
POST /preferences/me
Authorization: Bearer {token}
Content-Type: application/json

{
  "details": "Prefers morning appointments, nervous around loud noises"
}
```

#### Get Preferences
```http
GET /preferences/me
Authorization: Bearer {token}
```

## AI System

### Vector Embeddings

The system uses **sentence-transformers** with the `all-MiniLM-L6-v2` model to generate 384-dimensional embeddings for:

- Staff skills descriptions
- Pet complaint reasons
- Client preferences

These vectors enable semantic similarity search via pgvector's cosine distance operator.

### Staff Matching Algorithm

1. Client submits a complaint (e.g., "My dog has been limping")
2. Complaint is converted to a 384-dim vector
3. Vector similarity search finds staff with matching skills
4. Results ranked by similarity score
5. Available time slots filtered for each matched staff

### Chat Agent

The chat system uses a **ReAct (Reasoning + Acting)** pattern:

1. User message received
2. Intent classification (booking, query, general)
3. Agent reasons about required actions
4. Tools executed (database lookups, availability checks)
5. LLM generates natural language response

**Available Agent Tools:**
- `get_available_slots` - Check staff availability
- `get_client_bookings` - Retrieve user's appointments
- `get_pet_info` - Look up pet details
- `search_staff` - Find staff by specialty

### Wellness Outreach

Proactive system that:

1. Identifies pets with no bookings in 12+ months
2. Matches available slots to client preferences using vector similarity
3. Generates personalized outreach emails via Ollama LLM

Run manually:
```bash
docker-compose exec backend python -m app.wellness_outreach
```

## Authentication System

### Dual-Role JWT

The system uses separate authentication paths:

- **Clients:** `POST /token` returns client JWT
- **Staff/Admin:** `POST /staff/login` returns admin JWT

Tokens include role claims checked by route guards.

### Password Security

- Passwords hashed with bcrypt (passlib)
- Minimum complexity not enforced (configure as needed)
- Tokens expire after 30 minutes (configurable)

### Route Protection

**Frontend:**
- `ProtectedRoute` - Client-only pages
- `AdminProtectedRoute` - Admin-only pages

**Backend:**
- `get_current_client` - Validates client token
- `get_current_staff` - Validates admin token

## Deployment

### Docker Compose (Development)

```bash
docker-compose up --build -d
```

### Production Considerations

1. **Environment Variables:**
   - Generate strong `SECRET_KEY`
   - Use external PostgreSQL
   - Configure proper `DATABASE_URL`

2. **Ollama:**
   - Can run on GPU-enabled host
   - Or use API service (OpenAI, Anthropic)

3. **HTTPS:**
   - Add reverse proxy (nginx, Traefik)
   - Configure SSL certificates

4. **Database:**
   - Enable backups
   - Configure connection pooling
   - Set up monitoring

## Testing

### Manual API Testing

Use the interactive docs at http://localhost:8000/docs

### E2E Testing Flow

1. **Client Flow:**
   - Register at /register
   - Login
   - Add pet
   - Book appointment with AI suggestions
   - View bookings
   - Use chat assistant

2. **Admin Flow:**
   - Login at /admin/admin-login
   - Manage staff (add, edit, delete)
   - Schedule surgeries
   - Manage medication inventory
   - View all bookings

### Database Testing

```bash
# Connect to database
docker-compose exec db psql -U postgres -d interpaws

# Check tables
\dt

# Query data
SELECT * FROM staff;
SELECT * FROM bookings WHERE status = 'confirmed';
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Follow existing code patterns
4. Test both client and admin flows
5. Submit a pull request

### Code Style

- **Backend:** PEP 8, type hints
- **Frontend:** ESLint, React best practices
- **Commits:** Descriptive messages
