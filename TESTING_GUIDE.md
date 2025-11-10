# Quick Testing Guide - Admin VPMS

## Prerequisites
```bash
cd /Users/amaribullard/Documents/GitHub/Interpaws
docker-compose up --build
```

## 1. Create Admin Account

```bash
curl -X POST "http://localhost:8000/staff/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dr. Sarah Johnson",
    "email": "sarah@interpaws.com",
    "password": "admin123",
    "role": "Veterinarian",
    "skills_description": "Expert in orthopedic surgery and trauma care"
  }'
```

## 2. Login as Admin

```bash
curl -X POST "http://localhost:8000/staff/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=sarah@interpaws.com&password=admin123"
```

**Response:** Save the `access_token` for subsequent requests

## 3. Test Staff Management

### List All Staff (Protected)
```bash
curl -X GET "http://localhost:8000/staff/" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Update Staff
```bash
curl -X PUT "http://localhost:8000/staff/1" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "skills_description": "Expert in orthopedic surgery, trauma care, and dental procedures"
  }'
```

### Delete Staff
```bash
curl -X DELETE "http://localhost:8000/staff/2" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 4. Test Surgery Management

### Create Surgery
```bash
curl -X POST "http://localhost:8000/surgeries/" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "pet_id": 1,
    "staff_id": 1,
    "surgery_type": "Spay",
    "start_time": "2025-11-15T09:00:00",
    "end_time": "2025-11-15T10:00:00",
    "status": "Scheduled",
    "notes": "Routine spay procedure"
  }'
```

### List Surgeries (with filters)
```bash
# All surgeries
curl -X GET "http://localhost:8000/surgeries/" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Filter by staff
curl -X GET "http://localhost:8000/surgeries/?staff_id=1" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Filter by date
curl -X GET "http://localhost:8000/surgeries/?date=2025-11-15" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Update Surgery
```bash
curl -X PUT "http://localhost:8000/surgeries/1" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "In-Progress"
  }'
```

### Delete Surgery
```bash
curl -X DELETE "http://localhost:8000/surgeries/1" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 5. Test Medication Management

### Add Medication
```bash
curl -X POST "http://localhost:8000/medications/" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Amoxicillin",
    "description": "Broad-spectrum antibiotic",
    "stock_quantity": 100,
    "unit": "tablets"
  }'
```

### List All Medications
```bash
curl -X GET "http://localhost:8000/medications/" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Update Medication Stock
```bash
curl -X PUT "http://localhost:8000/medications/1" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "stock_quantity": 75
  }'
```

### Delete Medication
```bash
curl -X DELETE "http://localhost:8000/medications/1" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 6. Test Protected Booking Endpoints

### Update Booking (Admin Only)
```bash
curl -X PUT "http://localhost:8000/bookings/1" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "completed"
  }'
```

### Delete Booking (Admin Only)
```bash
curl -X DELETE "http://localhost:8000/bookings/1" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Testing Authentication Security

### Test Unauthorized Access (Should Fail)
```bash
# Try to access admin endpoint without token
curl -X GET "http://localhost:8000/staff/"
# Expected: 401 Unauthorized

# Try with invalid token
curl -X GET "http://localhost:8000/staff/" \
  -H "Authorization: Bearer invalid_token"
# Expected: 401 Unauthorized

# Try with client token instead of admin token
# (First create a client and login, then use that token)
curl -X GET "http://localhost:8000/staff/" \
  -H "Authorization: Bearer CLIENT_TOKEN_HERE"
# Expected: 401 Unauthorized (client tokens don't work for admin endpoints)
```

## API Documentation

Once the server is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Environment Variables

Make sure these are set in your `.env` file or docker-compose.yml:
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT secret key (change in production!)

## Common Issues

1. **401 Unauthorized**: Token expired or invalid - login again
2. **400 Email already registered**: Email must be unique for staff
3. **404 Not Found**: Resource doesn't exist - check IDs
4. **Connection Refused**: Database not running - check docker-compose

## Notes

- All timestamps should be in ISO 8601 format: `YYYY-MM-DDTHH:MM:SS`
- Tokens expire after 30 minutes (default)
- Skills embeddings are automatically generated/updated
- All admin endpoints require valid staff JWT token
