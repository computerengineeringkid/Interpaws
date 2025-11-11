# Admin Access Instructions

## Admin Login Credentials

**URL:** http://localhost:3000/admin/admin-login

**Email:** admin@interpaws.com  
**Password:** admin123

## Features Available

### Staff Management (`/admin/staff`)

- View all staff members
- Create new staff accounts with email/password
- Edit existing staff (name, role, skills)
- Delete staff members
- Each staff member requires:
  - Name (required)
  - Email (required, unique)
  - Password (required for new accounts)
  - Role (required) - e.g., "Veterinarian", "Technician", "Administrator"
  - Skills Description (optional) - detailed description of expertise

### Surgeries Management (`/admin/surgeries`)

- Manage surgery records
- Track surgical procedures

### Medications Management (`/admin/medications`)

- Manage medication inventory
- Track prescriptions

## Important Notes

1. **Creating Staff Accounts**: You can now create new staff accounts through the admin interface. These staff members will be able to:

   - Login at `/admin/admin-login`
   - Access all admin features
   - Manage bookings, surgeries, and medications

2. **Password Security**: Passwords are hashed using bcrypt before storage

3. **Navigation**: Use the top navigation bar to switch between different admin sections

## Troubleshooting

If you encounter any issues:

1. Make sure all Docker containers are running: `docker compose ps`
2. Check backend logs: `docker compose logs backend`
3. Check frontend logs: `docker compose logs frontend`
4. Verify you're using the correct login URL: `/admin/admin-login` (not `/login`)

## Next Steps

1. Login with the admin credentials
2. Navigate to Staff Management
3. Create staff accounts as needed
4. Test the surgeries and medications management features
