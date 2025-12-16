# Interpaws Demo Script

This guide walks you through demonstrating Interpaws' AI-powered veterinary practice management features. All AI is powered by Gemini 2.5 Flash for reliable, intelligent responses.

---

## Pre-Demo Setup

1. **Get your Gemini API key** (free): https://aistudio.google.com/apikey

2. **Create `.env` file** in the project root:
   ```
   GOOGLE_API_KEY=your-key-here
   ```

3. **Start the system**:
   ```bash
   ./start.sh
   ```
   Wait 1-2 minutes for services to initialize.

4. **Create test data** (if needed):
   - Register a client account at http://localhost:3000/register
   - Add a pet via the dashboard
   - Create an admin user: `POST /staff/` with name/email/password

5. **Open two browser tabs**:
   - Client view: http://localhost:3000
   - Admin view: http://localhost:3000/admin

---

## Demo Flow

### Part 1: Client AI Chat — Booking an Appointment

**Goal**: Show how clients can naturally describe their pet's issue and book appointments through conversation.

**Login as a client**, then open the AI Chat.

#### Recommended Demo Phrases:

1. **Start with the pet's issue**:
   > "My dog Max has been limping for the past two days"

   *Expected*: AI asks clarifying questions, identifies it's not an emergency, and offers to schedule.

2. **Provide time preference**:
   > "I prefer afternoons"

   *Expected*: AI shows available afternoon slots with the recommended veterinarian.

3. **Book a specific slot**:
   > "Let's do Tuesday at 2pm"

   *Expected*: AI confirms the booking with details.

#### Alternative Scenarios to Demo:

**Rescheduling**:
> "Can I reschedule my appointment to Thursday morning?"

**Emergency Detection**:
> "My cat is having seizures and can't stand up"

*Expected*: AI immediately flags as emergency and advises going to emergency clinic.

**General Advice**:
> "My puppy keeps scratching his ears, what should I do?"

*Expected*: AI provides helpful advice and offers to schedule if issue persists.

---

### Part 2: Staff AI Chat — Practice Management

**Goal**: Show how staff can query schedules, patient info, and inventory through natural language.

**Login as admin**, then navigate to the AI assistant in the admin panel.

#### Recommended Demo Phrases:

1. **Check today's schedule**:
   > "What appointments do I have today?"

   *Expected*: Shows list of today's patients with times and reasons.

2. **Look up a specific day**:
   > "Check my schedule for Tuesday the 17th"

   *Expected*: Shows appointments for that date.

3. **Patient lookup**:
   > "Tell me about Max"

   *Expected*: Shows pet info including owner, species, breed, age.

4. **Inventory check**:
   > "How's our medication inventory?"

   *Expected*: Shows inventory summary with low stock and out of stock alerts.

---

### Part 3: Smart Features to Highlight

#### Client Pattern Learning
The system learns from booking history:
- Preferred days (e.g., "This client usually books on Tuesdays")
- Preferred times (morning/afternoon/evening)
- These preferences influence slot suggestions

#### Staff Matching
When clients describe symptoms, the AI:
- Uses semantic similarity to match with the best-qualified staff
- Considers specializations (surgery, dermatology, etc.)
- Explains why a staff member was recommended

#### Service Type Inference
The system automatically categorizes appointments:
- "limping" → Exam/Consultation
- "vaccinations" → Vaccination appointment
- "dental cleaning" → Dental procedure
- This affects appointment duration and staff assignment

---

## Troubleshooting

**AI returns "GOOGLE_API_KEY not configured"**:
- Ensure `.env` file exists with valid key
- Restart with `docker-compose down && docker-compose up --build`

**AI seems slow**:
- First request may take 2-3 seconds as Gemini warms up
- Subsequent requests are faster

**Booking fails**:
- Ensure test client has pets registered
- Check that staff members exist in the database

---

## Demo Tips

1. **Start fresh**: Clear conversation history between demos
2. **Use natural language**: The AI handles casual phrasing well
3. **Show the error handling**: Try edge cases like unavailable times
4. **Highlight the data**: Point out how the AI uses real database info
5. **Contrast with competitors**: Emphasize the conversational, AI-first approach

---

## Quick Reference — Best Demo Phrases

| Feature | Say This |
|---------|----------|
| Book appointment | "My dog Bella has been vomiting since yesterday" |
| Time preference | "I prefer mornings" or "Weekends work best" |
| Confirm booking | "Book the 10am slot" |
| Reschedule | "Can we move it to Thursday afternoon?" |
| Cancel | "I need to cancel my appointment" |
| Emergency | "My cat ate something poisonous" |
| Staff schedule | "What's on my schedule today?" |
| Patient lookup | "Show me info about Luna" |
| Inventory | "Check medication stock levels" |
