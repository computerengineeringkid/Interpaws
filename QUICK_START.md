# 🚀 Quick Start Guide - Interpaws VPMS

## Prerequisites

- Docker Desktop installed and running
- Terminal/Command Line access

## Start the Application

### Option 1: Using the startup script (Recommended)

```bash
cd /Users/amaribullard/Documents/GitHub/Interpaws
./start.sh
```

### Option 2: Manual start

```bash
cd /Users/amaribullard/Documents/GitHub/Interpaws
docker-compose up --build -d
```

## Wait for Services

The application takes ~1-2 minutes to fully start:

- Database initialization
- Backend migration application
- Frontend build
- Ollama AI model loading

## Create Your First Admin Account

```bash
curl -X POST "http://localhost:8000/staff/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dr. Admin",
    "email": "admin@interpaws.com",
    "password": "admin123",
    "role": "Veterinarian",
    "skills_description": "General veterinary practice and emergency care"
  }'
```

## Access the Application

### 👤 Client Portal

1. **Open:** http://localhost:3000
2. **Register:** Create a client account
3. **Features:**
   - Book appointments
   - Get AI staff suggestions
   - Chat with AI assistant
   - View your bookings
   - Set preferences

### 👨‍⚕️ Admin Dashboard

1. **Open:** http://localhost:3000/admin/admin-login
2. **Login:**
   - Email: admin@interpaws.com
   - Password: admin123
3. **Features:**
   - Manage staff members
   - Schedule surgeries
   - Track medication inventory
   - Manage bookings

## 5-Minute Test Flow

### Client Test (2 minutes)

```
1. Go to http://localhost:3000/login
2. Register new account
3. Fill in booking form with complaint
4. Click "Get AI Suggestions"
5. See recommended staff
6. Navigate to "My Bookings"
```

### Admin Test (3 minutes)

```
1. Go to http://localhost:3000/admin/admin-login
2. Login with admin credentials
3. Click "Staff" → Create new staff member
4. Click "Medications" → Add new medication
5. Click "Surgeries" → Schedule a surgery
6. Click "Dashboard" → View bookings
```

## Troubleshooting

### Services not starting?

```bash
# Check Docker is running
docker ps

# View logs
docker-compose logs -f

# Restart services
docker-compose down
docker-compose up -d
```

### Can't access frontend?

```bash
# Check frontend is running
curl http://localhost:3000

# Rebuild if needed
docker-compose up --build frontend
```

### Can't access backend?

```bash
# Check backend is running
curl http://localhost:8000

# View backend logs
docker-compose logs backend

# Rebuild if needed
docker-compose up --build backend
```

### Database issues?

```bash
# Reset database
docker-compose down -v
docker-compose up -d

# Re-create admin account (see above)
```

## Stop the Application

```bash
docker-compose down
```

## Full Testing

For comprehensive end-to-end testing, see:

- **E2E_TESTING_GUIDE.md** - Complete testing procedures
- **DAYS_12-14_SUMMARY.md** - Implementation details

## API Documentation

Once running, visit:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Need Help?

1. Check `E2E_TESTING_GUIDE.md` for common issues
2. View logs: `docker-compose logs -f`
3. Check `SETUP_GUIDE.md` for detailed setup
4. Review `DAYS_12-14_SUMMARY.md` for architecture

---

**That's it!** You're ready to use Interpaws VPMS 🐾
