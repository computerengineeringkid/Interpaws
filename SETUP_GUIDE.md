# Client Portal Full Flow - Setup Guide

## Overview

This implementation adds JWT-based authentication to the Interpaws project, enabling secure client login, booking management, and preferences storage.

## Backend Changes

### 1. Database Model Updates

- **`backend/app/models.py`**: Added `hashed_password` column to the `Client` model

### 2. Schema Updates

- **`backend/app/schemas.py`**: Added:
  - `ClientBase`, `ClientCreate`, `Client` schemas for client registration
  - `Token` and `TokenData` schemas for JWT authentication
  - `PreferencesBase`, `PreferencesCreate`, `Preferences` schemas for user preferences

### 3. Authentication Module

- **`backend/app/auth.py`**: New file containing:
  - Password hashing utilities (`get_password_hash`, `verify_password`)
  - JWT token creation (`create_access_token`)
  - User authentication (`authenticate_client`, `get_current_user`)

### 4. API Endpoints

- **`backend/app/main.py`**: Added endpoints:
  - `POST /clients/` - Register a new client
  - `POST /token` - Login and get JWT token
  - `GET /clients/me` - Get current authenticated client
  - `GET /bookings/me` - Get bookings for authenticated client
  - `POST /preferences/me` - Save client preferences with AI embedding
  - `GET /preferences/me` - Retrieve client preferences

### 5. Dependencies

- **`backend/requirements.txt`**: Added:
  - `python-jose[cryptography]` - JWT token handling
  - `passlib[bcrypt]` - Password hashing
  - `python-multipart` - Form data parsing

## Frontend Changes

### 1. Authentication Context

- **`frontend/src/context/AuthContext.js`**: React Context for global auth state
  - Stores JWT token and user data in localStorage
  - Provides `login`, `register`, and `logout` functions
  - Auto-redirects on authentication failures

### 2. Providers Component

- **`frontend/src/components/Providers.js`**: Client-side wrapper for AuthProvider
- **`frontend/src/app/layout.js`**: Updated to use Providers component

### 3. Login/Register Page

- **`frontend/src/app/login/page.js`**: Dual-purpose authentication page
  - Toggle between login and registration
  - Uses ShadCN components (Card, Input, Button, Label)
  - Form validation and error handling

### 4. My Bookings Page

- **`frontend/src/app/(client)/my-bookings/page.js`**: Protected route
  - Displays all bookings for authenticated user
  - Uses ShadCN Table components
  - Auto-redirects to login if not authenticated

### 5. Preferences Page

- **`frontend/src/app/(client)/preferences/page.js`**: Protected route
  - Form to add new preferences (saved with AI embeddings)
  - Displays all saved preferences
  - Uses ShadCN Textarea and Card components

### 6. Utility Components

- **`frontend/src/components/ProtectedRoute.js`**: Reusable protected route wrapper

## Installation & Setup

### Backend Setup

1. **Navigate to backend directory:**

   ```bash
   cd backend
   ```

2. **Install new dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables (optional but recommended for production):**

   ```bash
   export SECRET_KEY="your-secure-random-secret-key-here"
   ```

4. **Database migration:**
   Since we added a new column (`hashed_password`) to the `Client` model, you have two options:

   **Option A: Drop and recreate (DEV ONLY - loses all data):**

   ```bash
   # The application will automatically create tables on startup
   # If you need to reset, connect to PostgreSQL and drop tables manually
   ```

   **Option B: Add column manually (preserves data):**

   ```sql
   -- Connect to your database and run:
   ALTER TABLE clients ADD COLUMN hashed_password VARCHAR;
   ```

5. **Start the backend:**

   ```bash
   # If using Docker Compose from root:
   cd ..
   docker-compose up --build

   # Or run locally:
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. **Navigate to frontend directory:**

   ```bash
   cd frontend
   ```

2. **Install dependencies (if not already done):**

   ```bash
   npm install
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```

## Testing the Application

### 1. Register a New Client

- Navigate to `http://localhost:3000/login`
- Click "Create Account"
- Fill in name, email, and password
- Submit to register

### 2. Login

- Use your email and password
- On success, you'll be redirected to `/my-bookings`

### 3. View Bookings

- Go to `http://localhost:3000/my-bookings`
- See all your bookings (will be empty initially)

### 4. Add Preferences

- Click "My Preferences" button or navigate to `/preferences`
- Enter preference details (e.g., "My dog needs morning appointments")
- Click "Save Preference"
- The preference will be stored with an AI embedding for future matching

### 5. API Testing with curl

**Register:**

```bash
curl -X POST http://localhost:8000/clients/ \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "email": "john@example.com", "password": "secure123"}'
```

**Login:**

```bash
curl -X POST http://localhost:8000/token \
  -F "username=john@example.com" \
  -F "password=secure123"
```

**Get Current User:**

```bash
TOKEN="your-jwt-token-here"
curl -X GET http://localhost:8000/clients/me \
  -H "Authorization: Bearer $TOKEN"
```

**Get My Bookings:**

```bash
curl -X GET http://localhost:8000/bookings/me \
  -H "Authorization: Bearer $TOKEN"
```

**Add Preference:**

```bash
curl -X POST http://localhost:8000/preferences/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"details": "My cat prefers afternoon appointments"}'
```

## Security Notes

1. **Secret Key**: The default secret key in `auth.py` should be changed in production:

   ```bash
   export SECRET_KEY=$(openssl rand -hex 32)
   ```

2. **CORS**: You may need to add CORS middleware if frontend/backend are on different domains

3. **Token Expiration**: Tokens expire after 30 minutes by default (configurable in `auth.py`)

4. **HTTPS**: In production, always use HTTPS for API calls

## Architecture Notes

### Authentication Flow

1. User submits email/password to `/token`
2. Backend validates credentials and returns JWT
3. Frontend stores JWT in localStorage
4. Protected routes include JWT in Authorization header
5. Backend validates JWT and extracts user info
6. Endpoint executes with authenticated user context

### AI Integration

- Preferences are stored with vector embeddings using the sentence-transformer model
- This allows for semantic matching in future AI-powered features
- Embeddings are generated using the existing `get_embedding()` function

## File Structure

```
backend/
  app/
    auth.py                 # New - Authentication logic
    models.py              # Modified - Added hashed_password
    schemas.py             # Modified - Added auth schemas
    main.py                # Modified - Added auth endpoints
    requirements.txt       # Modified - Added auth dependencies

frontend/
  src/
    app/
      layout.js            # Modified - Added Providers
      login/
        page.js            # New - Login/Register page
      (client)/
        my-bookings/
          page.js          # New - Bookings page
        preferences/
          page.js          # New - Preferences page
    components/
      Providers.js         # New - Client-side provider wrapper
      ProtectedRoute.js    # New - Protected route wrapper
    context/
      AuthContext.js       # New - Authentication context
```

## Next Steps

- Add password reset functionality
- Implement refresh tokens for extended sessions
- Add email verification for new accounts
- Enhance preferences UI with categories
- Add booking creation from the client portal
- Implement profile editing (name, email change)
- Add pet management (add/edit/delete pets)

## Troubleshooting

**Issue: "Could not validate credentials"**

- Check that token is being sent in Authorization header
- Verify token hasn't expired
- Ensure SECRET_KEY matches between token creation and validation

**Issue: "Email already registered"**

- Email is unique constraint
- Use different email or implement password reset

**Issue: CORS errors**

- Add CORS middleware to FastAPI if needed
- Check that API URL in frontend matches backend

**Issue: Import errors for jose/passlib**

- Run `pip install -r requirements.txt` in backend directory
- Restart the backend server
