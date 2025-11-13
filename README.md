# Interpaws - Veterinary Practice Management System

**Last updated:** November 10, 2025  
**Status:** ✅ Feature Complete - Ready for Production Testing

## 🎯 Overview

Interpaws is a comprehensive, AI-powered veterinary practice management system (VPMS) featuring:

- **Dual-role authentication** (Client & Admin/Staff)
- **AI-powered staff matching** using vector embeddings
- **Intelligent chat assistant** for client queries
- **Complete CRUD operations** for staff, surgeries, and medications
- **Booking management** with availability checking
- **Client preferences** system for personalized care

## 📚 Quick Links

- **[Quick Start Guide](QUICK_START.md)** - Get up and running in 5 minutes
- **[E2E Testing Guide](E2E_TESTING_GUIDE.md)** - Comprehensive testing procedures
- **[Setup Guide](SETUP_GUIDE.md)** - Detailed setup instructions
- **[Days 12-14 Summary](DAYS_12-14_SUMMARY.md)** - Latest implementation details
- **[API Documentation](http://localhost:8000/docs)** - Interactive API docs (when running)

## 🏗️ Tech Stack

### Backend

- **Framework:** FastAPI (Python 3.10+)
- **Server:** Uvicorn (ASGI)
- **Database:** PostgreSQL 15 with pgvector extension
- **ORM:** SQLAlchemy
- **Migrations:** Alembic
- **Authentication:** JWT (python-jose)
- **Password Hashing:** bcrypt (passlib)
- **AI/ML:**
  - sentence-transformers (embeddings)
  - Ollama (LLM for chat)

### Frontend

- **Framework:** Next.js 15 (App Router)
- **Language:** JavaScript/React
- **Styling:** Tailwind CSS
- **UI Components:** shadcn/ui
- **State Management:** React Context API
- **Runtime:** Node.js 20

### Infrastructure

- **Containerization:** Docker & Docker Compose
- **Database:** PostgreSQL with pgvector
- **AI Service:** Ollama (containerized)
- **Reverse Proxy:** Next.js rewrites for API

## 📁 Repository Structure

```
Interpaws/
├── backend/
│   ├── alembic/                    # Database migrations
│   │   └── versions/
│   │       ├── 001_initial_migration.py
│   │       ├── 002_add_ai_feedback_log.py
│   │       └── 003_add_staff_auth_surgery_medication.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI app with all endpoints
│   │   ├── database.py            # DB configuration & session
│   │   ├── models.py              # SQLAlchemy models
│   │   ├── schemas.py             # Pydantic schemas
│   │   ├── auth.py                # Authentication logic
│   │   ├── ai_services.py         # AI/ML integration
│   │   ├── booking_logic.py       # Business logic
│   │   └── seed.py                # Database seeding
│   ├── Dockerfile
│   ├── requirements.txt
│   └── alembic.ini
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── admin/            # Admin pages
│   │   │   │   ├── layout.js            # Admin layout with nav
│   │   │   │   ├── admin-login/page.js  # Admin login
│   │   │   │   ├── dashboard/page.js    # Dashboard
│   │   │   │   ├── staff/page.js # Staff management
│   │   │   │   ├── surgeries/page.js # Surgery management
│   │   │   │   └── medications/page.js # Medication inventory
│   │   │   ├── (client)/         # Client pages
│   │   │   │   ├── my-bookings/page.js
│   │   │   │   └── preferences/page.js
│   │   │   ├── login/page.js     # Client login
│   │   │   ├── layout.js         # Root layout
│   │   │   ├── page.js           # Client portal home
│   │   │   └── globals.css
│   │   ├── components/
│   │   │   ├── AdminNav.js       # Admin navigation
│   │   │   ├── AdminProtectedRoute.js
│   │   │   ├── ProtectedRoute.js
│   │   │   ├── AdminBookingList.js
│   │   │   ├── AdminCalendar.js
│   │   │   ├── ClientBookingForm.js
│   │   │   ├── AIChat.js
│   │   │   └── ui/               # shadcn/ui components
│   │   └── context/
│   │       └── AuthContext.js    # Dual-role auth
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.mjs
│   └── tailwind.config.js
├── docker-compose.yml
├── start.sh                       # Startup script
├── QUICK_START.md
├── E2E_TESTING_GUIDE.md
├── SETUP_GUIDE.md
├── DAYS_12-14_SUMMARY.md
└── README.md
```

## 🚀 Getting Started

### Quick Start (5 Minutes)

1. **Ensure Docker Desktop is running**

2. **Clone and start:**

```bash
git clone https://github.com/computerengineeringkid/Interpaws.git
cd Interpaws
./start.sh
```

3. **Create admin account:**

```bash
curl -X POST "http://localhost:8000/staff/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dr. Admin",
    "email": "admin@interpaws.com",
    "password": "admin123",
    "role": "Veterinarian",
    "skills_description": "General practice"
  }'
```

4. **Access the application:**
   - **Client Portal:** http://localhost:3000

- **Admin Login:** http://localhost:3000/admin/admin-login
- **Admin Dashboard:** http://localhost:3000/admin/dashboard
- **API Docs:** http://localhost:8000/docs

For detailed setup instructions, see [QUICK_START.md](QUICK_START.md)

### Manual Docker Commands

```bash
# Start services
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Reset database
docker-compose down -v
docker-compose up -d
```

## 🎨 Features

### Client Portal

- ✅ **User Registration & Authentication** - Secure JWT-based auth
- ✅ **AI-Powered Staff Matching** - Vector similarity search for best staff fit
- ✅ **Intelligent Chat Assistant** - Context-aware AI chat about pet care
- ✅ **Booking Management** - View and manage appointments
- ✅ **Preferences System** - Store pet preferences for personalized care
- ✅ **AI Recommendations** - Get staff suggestions based on pet complaints

### Admin Dashboard

- ✅ **Staff Management** - Full CRUD operations with skill embedding
- ✅ **Surgery Scheduling** - Plan and track surgical procedures
- ✅ **Medication Inventory** - Track stock levels with low-stock warnings
- ✅ **Booking Management** - Update status and manage all bookings
- ✅ **Role-Based Access** - Secure admin-only routes
- ✅ **Real-time Filters** - Filter surgeries by date, staff, pet

### AI & Intelligence

- ✅ **Vector Embeddings** - semantic matching of complaints to staff skills
- ✅ **LLM Integration** - Ollama for natural language responses
- ✅ **Smart Recommendations** - AI-suggested staff based on pet needs
- ✅ **Feedback Loop** - Track successful matches for model improvement
- ✅ **Wellness Outreach** - Proactive client engagement with AI-generated emails

### Security & Auth

- ✅ **Dual-Role System** - Separate client and admin authentication
- ✅ **JWT Tokens** - Secure token-based auth
- ✅ **Password Hashing** - bcrypt encryption
- ✅ **Route Protection** - Role-based access control
- ✅ **Session Management** - Persistent localStorage with auto-logout

## 📡 API Endpoints

### Authentication

- `POST /clients/` - Register new client
- `POST /token` - Client login
- `POST /staff/` - Create staff member
- `POST /staff/login` - Admin login
- `GET /clients/me` - Get current client

### Bookings

- `POST /bookings/` - Create booking
- `GET /bookings/{date}` - Get bookings for date
- `GET /bookings/me` - Get client's bookings
- `PUT /bookings/{id}` - Update booking (admin)
- `DELETE /bookings/{id}` - Delete booking (admin)

### Staff Management (Admin)

- `GET /staff/` - List all staff
- `POST /staff/` - Create staff
- `PUT /staff/{id}` - Update staff
- `DELETE /staff/{id}` - Delete staff

### Surgery Management (Admin)

- `GET /surgeries/` - List surgeries (with filters)
- `POST /surgeries/` - Create surgery
- `GET /surgeries/{id}` - Get surgery
- `PUT /surgeries/{id}` - Update surgery
- `DELETE /surgeries/{id}` - Delete surgery

### Medication Management (Admin)

- `GET /medications/` - List inventory
- `POST /medications/` - Add medication
- `GET /medications/{id}` - Get medication
- `PUT /medications/{id}` - Update medication
- `DELETE /medications/{id}` - Delete medication

### AI Features

- `POST /suggest_slots` - Get AI staff recommendations
- `POST /chat` - AI chat assistant
- `POST /log-feedback/` - Log successful matches

### Preferences

- `POST /preferences/me` - Create preference
- `GET /preferences/me` - Get client preferences

**Full API Documentation:** http://localhost:8000/docs (when running)

## 💾 Database Models

### Core Models

- **Clinic** - `id`, `name`
- **Client** - `id`, `name`, `email`, `hashed_password`, `clinic_id`
- **Pet** - `id`, `name`, `species`, `breed`, `client_id`
- **Booking** - `id`, `start_time`, `end_time`, `status`, `client_id`, `pet_id`, `staff_id`, `complaint_reason`, `complaint_vector`

### Staff & Medical

- **Staff** - `id`, `name`, `email`, `hashed_password`, `role`, `skills_description`, `skills_vector`
- **Surgery** - `id`, `pet_id`, `staff_id`, `surgery_type`, `notes`, `start_time`, `end_time`, `status`
- **Medication** - `id`, `name`, `description`, `stock_quantity`, `unit`

### AI & Preferences

- **Preferences** - `id`, `details`, `client_id`, `details_vector`
- **AIFeedbackLog** - `id`, `booking_id`, `staff_id`, `client_complaint_vector`, `staff_skills_vector`

### Migrations

All migrations are in `backend/alembic/versions/`:

- `001_initial_migration.py` - Initial schema
- `002_add_ai_feedback_log.py` - AI feedback tracking
- `003_add_staff_auth_surgery_medication.py` - Staff auth + VPMS features

Migrations auto-apply on container startup.

## 🏛️ Architecture

### Backend Architecture

- **Database Connection:** Environment-based `DATABASE_URL` with retry logic
- **Startup:** Healthcheck-based startup with automatic migrations
- **Authentication:** JWT-based dual-role system (client & admin)
- **AI Pipeline:**
  - Complaint text → sentence-transformer → vector embedding
  - Vector similarity search for staff matching
  - Ollama LLM for natural language responses
- **Live Reload:** Volume-mounted for development

### Frontend Architecture

- **Route Groups:**
  - `(admin)` - Admin dashboard, staff, surgeries, medications
  - `(client)` - Bookings, preferences
- **Authentication:** Context-based with localStorage persistence
- **Protected Routes:** Role-based route guards
- **API Proxy:** Next.js rewrites `/api/*` to backend
- **UI Framework:** shadcn/ui + Tailwind CSS
- **State:** React Context API for auth, local state for data

### Docker Services

```
┌─────────────┐
│   Frontend  │ :3000
│  (Next.js)  │
└──────┬──────┘
       │
┌──────▼──────┐
│   Backend   │ :8000
│  (FastAPI)  │
└──────┬──────┘
       │
┌──────▼──────┐     ┌──────────┐
│  Database   │     │  Ollama  │ :11434
│ (Postgres)  │     │   (AI)   │
└─────────────┘     └──────────┘
```

## 🧪 Testing

### E2E Testing

See [E2E_TESTING_GUIDE.md](E2E_TESTING_GUIDE.md) for comprehensive testing procedures.

**Quick Test:**

```bash
# Start the application
./start.sh

# Create admin account (see Quick Start above)

# Test client flow
1. Register at http://localhost:3000/login
2. Get AI suggestions
3. View bookings
4. Add preferences

# Test admin flow
1. Login at http://localhost:3000/admin/admin-login
2. Create staff member
3. Add medication
4. Schedule surgery
```

### Manual API Testing

```bash
# Health check
curl http://localhost:8000/

# Create client
curl -X POST http://localhost:8000/clients/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"test@test.com","password":"pass123"}'

# Login
curl -X POST http://localhost:8000/token \
  -d "username=test@test.com&password=pass123"
```

See [TESTING_GUIDE.md](TESTING_GUIDE.md) for more examples.

## 🎯 Project Status

### ✅ Completed Features

- [x] Full authentication system (client & admin)
- [x] JWT-based security with role separation
- [x] Database migrations with Alembic
- [x] Staff management (CRUD with AI embeddings)
- [x] Surgery scheduling and tracking
- [x] Medication inventory management
- [x] Booking system with availability checking
- [x] Client preferences with vector embeddings
- [x] AI-powered staff recommendations
- [x] Intelligent chat assistant
- [x] Admin dashboard with all VPMS features
- [x] Client portal with booking and preferences
- [x] Comprehensive error handling
- [x] Loading states and UX polish
- [x] Protected routes and security

### 🚀 Ready for Production Testing

All core features implemented per project masterplan.

### 📋 Future Enhancements

- [ ] Unit and integration tests (pytest, Jest)
- [ ] CI/CD pipeline
- [ ] Email notifications
- [ ] SMS reminders
- [ ] Payment integration
- [ ] Multi-clinic support
- [ ] Advanced analytics

## 🐛 Troubleshooting

### Common Issues

**Docker not running:**

```bash
# Start Docker Desktop first, then:
docker ps
```

**Services won't start:**

```bash
# Check logs
docker-compose logs -f

# Rebuild
docker-compose down
docker-compose up --build -d
```

**Database connection errors:**

```bash
# Check DB health
docker-compose ps

# Reset database
docker-compose down -v
docker-compose up -d
```

**Port conflicts (3000 or 8000):**

- Stop conflicting services
- Or modify ports in `docker-compose.yml`

**Frontend won't load:**

```bash
# Clear cache and rebuild
docker-compose down
docker volume rm interpaws_frontend_node_modules
docker-compose up --build frontend
```

**AI features not working:**

```bash
# Check Ollama is running
docker-compose logs ollama

# May need to pull model on first run
docker-compose exec ollama ollama pull llama2
```

**Can't login:**

- Clear browser localStorage
- Check credentials
- View backend logs for errors

For more troubleshooting, see [E2E_TESTING_GUIDE.md](E2E_TESTING_GUIDE.md#common-issues--solutions)

---

## � Wellness Outreach System

The Wellness Outreach System (Sprint 7) proactively identifies pets due for care and generates personalized AI-powered outreach emails.

### Features

- **Automated Pet Detection** - Finds pets with no bookings in 12+ months
- **Smart Scheduling** - Matches available slots with client preferences using vector similarity
- **AI Email Generation** - Creates personalized, warm outreach emails via Ollama LLM
- **Flexible Execution** - Run manually, as a cron job, or as a continuous scheduler

### Quick Usage

**Manual run:**

```bash
./run_wellness_outreach.sh
```

**From Docker:**

```bash
docker-compose exec backend python -m app.wellness_outreach
```

**Run tests:**

```bash
docker-compose exec backend python -m app.test_wellness_outreach
```

**As a scheduler (continuous service):**

```bash
docker-compose exec backend python -m app.wellness_scheduler
```

### Output

Generates personalized emails like:

```
TO: john@example.com (John Doe)
RE: Wellness Check for Max
SUGGESTED SLOT: Monday, November 18 at 10:00 AM

Dear John Doe,

We hope this message finds you and Max doing well! It's been a while
since Max's last visit, and we wanted to reach out...
```

Emails are logged to `backend/outreach_log.txt` for review.

### Documentation

See **[WELLNESS_OUTREACH_GUIDE.md](WELLNESS_OUTREACH_GUIDE.md)** for:

- Architecture details
- Configuration options
- Scheduling setup (cron/Docker)
- Testing procedures
- Customization guide

---

## �👥 Contributing

We welcome contributions to InterPaws! Here's how to get started:

### How to Contribute

1. **Open an Issue** - Discuss the change before starting work
2. **Fork the Repository** - Create your own copy
3. **Create a Branch** - `git checkout -b feature/your-feature-name`
4. **Make Changes** - Follow code style and add tests
5. **Update Documentation** - Keep README and guides current
6. **Submit a Pull Request** - Reference the issue number

### Development Guidelines

- Follow existing code patterns (FastAPI, Next.js App Router)
- Add comprehensive error handling
- Include loading states in UI components
- Test both client and admin flows
- Update TypeScript/JSDoc comments
- Run migrations for database changes

### Code Style

- **Backend:** PEP 8, type hints, docstrings
- **Frontend:** ESLint config, React best practices
- **Commits:** Descriptive messages with context

---

## 📄 License

[Add your license information here - MIT, Apache 2.0, etc.]

---

## 📞 Support & Documentation

**Documentation:**

- 🚀 [Quick Start Guide](QUICK_START.md) - Get running in 5 minutes
- 🧪 [E2E Testing Guide](E2E_TESTING_GUIDE.md) - Comprehensive testing procedures
- 🔧 [Setup Guide](SETUP_GUIDE.md) - Detailed setup instructions
- 📋 [Latest Updates](DAYS_12-14_SUMMARY.md) - Recent feature additions
- 💌 [Wellness Outreach Guide](WELLNESS_OUTREACH_GUIDE.md) - Proactive client engagement system

**API Reference:**

- Interactive Docs: http://localhost:8000/docs
- OpenAPI Spec: http://localhost:8000/openapi.json

**Support Channels:**

- GitHub Issues: Bug reports and feature requests
- GitHub Discussions: Questions and community help

---

<div align="center">

### Built with ❤️ for better veterinary care 🐾

**Status:** ✅ Feature Complete - Ready for Production Testing  
**Version:** 1.0.0  
**Last Updated:** December 2024

</div>
