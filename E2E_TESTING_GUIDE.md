# E2E Testing Guide - Days 12-14

## Prerequisites

1. **Start the application:**

```bash
cd /Users/amaribullard/Documents/GitHub/Interpaws
docker-compose up --build
```

2. **Wait for services to be ready:**
   - Backend: http://localhost:8000
   - Frontend: http://localhost:3000
   - Database migrations should auto-apply

## Client Workflow Testing

### Test 1: Client Registration

1. Navigate to http://localhost:3000/login
2. Click "Sign Up" or navigate to registration
3. Fill in:
   - Name: "Test Client"
   - Email: "client@test.com"
   - Password: "password123"
4. ✅ Should redirect to home page after successful registration
5. ✅ Should see "Client Portal" page

### Test 2: Client Login

1. If logged out, navigate to http://localhost:3000/login
2. Enter credentials:
   - Email: "client@test.com"
   - Password: "password123"
3. ✅ Should redirect to home page
4. ✅ Token should be stored in localStorage

### Test 3: View Bookings

1. Navigate to http://localhost:3000/my-bookings
2. ✅ Should see "My Bookings" page
3. ✅ Should display empty state if no bookings
4. ✅ Should show logout button

### Test 4: Add Preferences

1. Navigate to http://localhost:3000/preferences
2. Enter preference text:
   - "My dog prefers female veterinarians and is afraid of loud noises."
3. Click "Save Preference"
4. ✅ Should show success message
5. ✅ Preference should appear in list below
6. ✅ Should show loading spinner during save

### Test 5: AI Suggestion Feature

1. Navigate to http://localhost:3000/
2. Fill in booking form:
   - Pet Name: "Max"
   - Service: "Wellness Check"
   - Complaint: "My dog has been limping on his front left paw for 2 days"
3. Click "Get AI Suggestions"
4. ✅ Should show loading indicator
5. ✅ Should display AI recommendation text
6. ✅ Should show suggested staff members
7. ✅ Should show error message if API fails

### Test 6: AI Chat Feature

1. On the same page, with complaint filled in
2. In the AI Chat section, type: "What should I do before the appointment?"
3. Click "Send"
4. ✅ Should show user message
5. ✅ Should show AI response
6. ✅ Should show loading state while waiting
7. ✅ Should warn if no complaint text provided

## Admin Workflow Testing

### Test 1: Admin Login

1. Navigate to http://localhost:3000/admin/login
2. First, create an admin account via backend:

```bash
curl -X POST "http://localhost:8000/staff/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dr. Admin",
    "email": "admin@interpaws.com",
    "password": "admin123",
    "role": "Veterinarian",
    "skills_description": "General practice and emergency care"
  }'
```

3. Enter admin credentials:
   - Email: "admin@interpaws.com"
   - Password: "admin123"
4. ✅ Should redirect to /admin dashboard
5. ✅ Should see admin navigation bar
6. ✅ Token should be stored with role='admin'

### Test 2: Staff CRUD Operations

1. Navigate to http://localhost:3000/admin/staff
2. **Create Staff:**

   - Fill in form with:
     - Name: "Dr. Sarah"
     - Email: "sarah@interpaws.com"
     - Password: "pass123"
     - Role: "Veterinarian"
     - Skills: "Orthopedic surgery specialist"
   - Click "Create Staff"
   - ✅ Should appear in staff list
   - ✅ Form should clear after creation

3. **Edit Staff:**

   - Click "Edit" on a staff member
   - Change name to "Dr. Sarah Johnson"
   - Click "Update Staff"
   - ✅ Should update in the list
   - ✅ Form should reset

4. **Delete Staff:**
   - Click "Delete" on a staff member
   - Confirm deletion
   - ✅ Should remove from list
   - ✅ Should show confirmation dialog

### Test 3: Surgery CRUD Operations

1. Navigate to http://localhost:3000/admin/surgeries
2. **Create Surgery:**

   - Fill in form:
     - Pet ID: 1
     - Staff ID: 1
     - Surgery Type: "Spay"
     - Start Time: Future date/time
     - End Time: Future date/time (after start)
     - Status: "Scheduled"
     - Notes: "Routine spay procedure"
   - Click "Create Surgery"
   - ✅ Should appear in surgeries list

3. **Filter Surgeries:**

   - Enter date filter
   - ✅ Should filter results
   - Enter staff ID filter
   - ✅ Should filter by staff
   - Click "Clear Filters"
   - ✅ Should show all results

4. **Edit Surgery:**

   - Click "Edit" on a surgery
   - Change status to "In-Progress"
   - Click "Update Surgery"
   - ✅ Should update in list

5. **Delete Surgery:**
   - Click "Delete" on a surgery
   - Confirm
   - ✅ Should remove from list

### Test 4: Medication CRUD Operations

1. Navigate to http://localhost:3000/admin/medications
2. **Add Medication:**

   - Fill in form:
     - Name: "Amoxicillin"
     - Description: "Broad-spectrum antibiotic"
     - Stock Quantity: 100
     - Unit: "tablets"
   - Click "Add Medication"
   - ✅ Should appear in inventory list

3. **Low Stock Warning:**

   - Add medication with stock < 10
   - ✅ Should display in red

4. **Edit Medication:**

   - Click "Edit" on a medication
   - Change stock quantity to 75
   - Click "Update Medication"
   - ✅ Should update in list

5. **Delete Medication:**
   - Click "Delete" on a medication
   - Confirm
   - ✅ Should remove from inventory

### Test 5: Booking Management (Admin Dashboard)

1. Navigate to http://localhost:3000/admin
2. ✅ Should see calendar and booking list
3. Select a date with bookings
4. **Update Booking Status:**
   - Change status dropdown
   - ✅ Should update immediately
5. **Delete Booking:**
   - Click "Delete" button
   - Confirm
   - ✅ Should remove from list
6. ✅ Should use admin auth token for all operations

## Security Testing

### Test 1: Role Separation

1. **Try to access admin pages as client:**

   - Login as client
   - Navigate to http://localhost:3000/admin
   - ✅ Should redirect to /admin/login

2. **Try to access client pages as admin:**
   - Login as admin
   - Navigate to http://localhost:3000/my-bookings
   - ✅ Should redirect to /login (client login)

### Test 2: Protected Routes

1. **Without login:**

   - Navigate to http://localhost:3000/my-bookings
   - ✅ Should redirect to /login
   - Navigate to http://localhost:3000/admin
   - ✅ Should redirect to /admin/login

2. **Token expiration:**
   - Clear localStorage
   - Try to access protected route
   - ✅ Should redirect to login

## Bug Checklist

### Client Side

- [ ] Registration works and auto-logs in
- [ ] Login redirects to correct page
- [ ] Logout clears all state
- [ ] Bookings page loads data
- [ ] Preferences can be added and viewed
- [ ] AI suggestions work
- [ ] AI chat works with context
- [ ] Error messages display properly
- [ ] Loading states show correctly

### Admin Side

- [ ] Admin login works
- [ ] Admin navigation visible
- [ ] Staff CRUD all operations work
- [ ] Surgery CRUD all operations work
- [ ] Surgery filters work
- [ ] Medication CRUD all operations work
- [ ] Low stock indicator works
- [ ] Booking management works
- [ ] Auth token sent with all requests
- [ ] Error handling works

### General

- [ ] No console errors
- [ ] API calls use correct endpoints
- [ ] Forms validate properly
- [ ] Confirmation dialogs work
- [ ] Navigation between pages works
- [ ] Responsive design works

## Common Issues & Solutions

### Issue: API calls fail

- **Solution:** Check docker-compose is running
- **Solution:** Verify backend is on port 8000
- **Solution:** Check browser console for CORS errors

### Issue: Auth token not sent

- **Solution:** Check token in localStorage
- **Solution:** Verify useAuth() hook is called
- **Solution:** Check Authorization header in Network tab

### Issue: Redirect loops

- **Solution:** Clear localStorage
- **Solution:** Check userRole is set correctly
- **Solution:** Verify isAdmin vs isAuthenticated logic

### Issue: Form doesn't submit

- **Solution:** Check for validation errors
- **Solution:** Verify all required fields filled
- **Solution:** Check Network tab for request/response

## Performance Checklist

- [ ] Loading spinners appear quickly
- [ ] API responses < 2 seconds
- [ ] No unnecessary re-renders
- [ ] Forms clear after submission
- [ ] Lists update after CRUD operations

## Final Verification

- [ ] Both client and admin flows work end-to-end
- [ ] All CRUD operations complete successfully
- [ ] Auth is properly separated
- [ ] No data leaks between roles
- [ ] All error states handled gracefully
- [ ] All success states show feedback

---

**Status:** Ready for comprehensive testing
**Date:** November 10, 2025
