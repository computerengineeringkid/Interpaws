# Changelog

All notable changes to the Interpaws VPMS project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-11-13

### Added - Sprint 7: Proactive Client Wellness Outreach

#### Core Features

- **Wellness Outreach System** - Automated proactive client engagement system
  - Identifies pets with no bookings in 12+ months
  - Intelligently matches available slots with client preferences using vector similarity
  - Generates personalized outreach emails using Ollama LLM
  - Supports manual execution, cron scheduling, and continuous service modes

#### New Files

- `backend/app/wellness_outreach.py` - Core wellness outreach implementation (420 lines)
- `backend/app/wellness_scheduler.py` - Continuous scheduler service (95 lines)
- `backend/app/test_wellness_outreach.py` - Comprehensive test suite (530 lines)
- `run_wellness_outreach.sh` - Convenience runner script for manual execution
- `WELLNESS_OUTREACH_GUIDE.md` - Complete documentation (350+ lines)
- `WELLNESS_OUTREACH_QUICKREF.md` - Quick reference guide
- `SPRINT_7_SUMMARY.md` - Detailed implementation summary
- `docker-compose.wellness.example.yml` - Docker service configuration examples

#### Dependencies

- Added `schedule` library to `backend/requirements.txt` for cron-like scheduling

#### Documentation

- Updated `README.md` with wellness outreach features and quick start
- Added comprehensive guides for setup, testing, and customization
- Included troubleshooting and future enhancement documentation

#### Testing

- 5 comprehensive test cases covering all functionality
- Automated test data creation and cleanup
- End-to-end workflow validation
- Edge case handling verification

### Technical Details

#### Functions Implemented

- `get_target_pets()` - Database query for at-risk pets
- `find_open_slots()` - Availability search with business hour constraints
- `match_slot_to_preference()` - Vector similarity-based slot matching
- `generate_outreach_email()` - LLM-powered email generation with fallback
- `process_outreach()` - Main orchestration workflow
- Async scheduler service with error handling and logging

#### Integration

- Reuses existing database models (Client, Pet, Booking, Preferences, Staff)
- Leverages existing AI services (embeddings, LLM)
- Utilizes existing booking availability logic
- No breaking changes to existing endpoints or schema

#### Output

- Dual output: console (formatted) and log file (`backend/outreach_log.txt`)
- Detailed run statistics and error tracking
- Structured email format for easy review

### Deployment Options

1. **Manual Execution**

   ```bash
   ./run_wellness_outreach.sh
   docker-compose exec backend python -m app.wellness_outreach
   ```

2. **Scheduled Execution**

   - Docker cron service (example provided)
   - Host crontab
   - Python scheduler (continuous service)

3. **Testing**
   ```bash
   docker-compose exec backend python -m app.test_wellness_outreach
   ```

### Configuration

Customizable parameters:

- `LOOKBACK_MONTHS` - Pet eligibility window (default: 12 months)
- `LOOKAHEAD_DAYS` - Slot search window (default: 7 days)
- `SLOT_DURATION_HOURS` - Appointment length (default: 1 hour)
- `BUSINESS_START_HOUR` - Clinic opening (default: 9 AM)
- `BUSINESS_END_HOUR` - Last slot time (default: 5 PM)

### Performance & Quality

- Efficient database queries with proper filtering
- Per-pet error isolation (one failure doesn't stop batch)
- Graceful degradation (LLM failure → template fallback)
- Comprehensive error logging
- Proper database session management
- Type hints and docstrings throughout
- Follows existing project conventions

---

## [1.0.0] - 2024-12-XX

### Added - Initial Release

#### Core Features

- Dual-role authentication system (Client & Admin/Staff)
- AI-powered staff matching using vector embeddings
- Intelligent chat assistant for client queries
- Complete CRUD operations for staff, surgeries, and medications
- Booking management with availability checking
- Client preferences system for personalized care

#### Backend

- FastAPI application with comprehensive endpoints
- PostgreSQL database with pgvector extension
- SQLAlchemy ORM with Alembic migrations
- JWT authentication with bcrypt password hashing
- sentence-transformers for embeddings (384-dim vectors)
- Ollama integration for LLM chat (llama3 model)

#### Frontend

- Next.js 15 App Router architecture
- Client portal with booking and preferences
- Admin dashboard with staff/surgery/medication management
- Real-time filters and calendar views
- shadcn/ui component library
- Tailwind CSS styling
- Dual authentication context

#### Infrastructure

- Docker containerization
- Docker Compose orchestration
- Automated startup script (`start.sh`)
- Database migrations on container start
- Health checks and service dependencies

#### Documentation

- Quick Start Guide
- E2E Testing Guide
- Setup Guide
- Admin Access documentation
- Implementation summaries
- API documentation via FastAPI docs

#### API Endpoints

- Authentication: `/token`, `/staff/login`, `/clients/`, `/staff/`
- Bookings: CRUD + availability + date filtering
- Staff: CRUD + skill embeddings
- Surgeries: CRUD + filtering by date/staff/pet
- Medications: CRUD + inventory tracking
- AI: `/suggest_slots`, `/chat`, `/preferences/me`

#### Testing

- Seed scripts for sample data
- Admin creation utilities
- Manual testing guides
- E2E test procedures

---

## Release Notes

### [1.1.0] Summary

Sprint 7 adds a powerful proactive wellness outreach system that helps clinics re-engage with clients whose pets haven't been seen in over a year. The system intelligently matches available appointments with client preferences and generates warm, personalized emails using AI. This feature runs independently as a scheduled job and requires no changes to the existing application.

### [1.0.0] Summary

Initial production-ready release of Interpaws VPMS with full client and admin functionality, AI-powered features, and comprehensive documentation.

---

**Semantic Versioning Guide:**

- **Major (X.0.0):** Breaking changes, major architecture updates
- **Minor (1.X.0):** New features, backward-compatible additions
- **Patch (1.1.X):** Bug fixes, minor improvements

---

**Next Planned Features:**

- Email delivery integration (SendGrid/Mailgun/SES)
- Client opt-out preferences
- Multi-language support
- Advanced analytics and reporting
- Mobile app development
