# Wellness Outreach System - Documentation

## Overview

The Wellness Outreach System is a proactive client engagement feature that automatically identifies pets due for care and generates personalized outreach emails. This is Sprint 7 from the Interpaws Master Plan.

## Features

- **Automated Pet Identification**: Finds pets with no future bookings and no visits in the last 12 months
- **Smart Slot Matching**: Uses vector similarity to match appointment slots with client preferences
- **AI-Powered Emails**: Generates warm, personalized outreach emails using Ollama LLM
- **Flexible Scheduling**: Searches for available slots across all staff members for the next 7 days

## Architecture

### File Location

```
backend/app/wellness_outreach.py
```

### Dependencies

- `app.database` - Database session management
- `app.models` - SQLAlchemy models (Client, Pet, Booking, Preferences, Staff)
- `app.ai_services` - Embedding generation and LLM integration
- `app.booking_logic` - Availability checking

## Configuration

Default settings (modify in `wellness_outreach.py`):

```python
LOOKBACK_MONTHS = 12          # Pets with no visits in last 12 months
LOOKAHEAD_DAYS = 7            # Search for slots in next 7 days
SLOT_DURATION_HOURS = 1       # Wellness check duration
BUSINESS_START_HOUR = 9       # 9 AM
BUSINESS_END_HOUR = 17        # 5 PM (last slot at 4 PM)
OUTREACH_LOG_FILE = "outreach_log.txt"
```

## How It Works

### 1. Pet Identification (`get_target_pets`)

Queries the database to find pets that meet these criteria:

- **No future bookings** scheduled
- **AND** either:
  - No booking history, OR
  - Last booking was > 12 months ago

### 2. Slot Discovery (`find_open_slots`)

- Searches the next 7 days (excluding weekends)
- Checks hourly slots from 9 AM - 4 PM
- Validates availability using existing `check_availability` logic
- Returns slots with metadata: day name, time period (Morning/Afternoon)

### 3. Preference Matching (`match_slot_to_preference`)

- Fetches client's `Preferences` record
- If client has a `details_vector`:
  - Embeds each slot description (e.g., "Monday Morning")
  - Calculates L2 distance between preference vector and slot embeddings
  - Returns the slot with smallest distance (best match)
- If no preferences exist:
  - Returns the first available slot

### 4. Email Generation (`generate_outreach_email`)

Constructs a prompt with:

- Pet name, species
- Owner name
- Suggested appointment time and veterinarian

Sends to Ollama LLM (`llama3`) to generate a warm, professional email. Includes fallback template if LLM fails.

### 5. Execution (`process_outreach`)

Orchestrates the workflow:

1. Identify target pets
2. Find open slots
3. For each pet:
   - Match best slot
   - Generate email
   - Print to stdout
   - Log to file
4. Return summary statistics

## Running the Script

### Manual Execution (Testing)

From the Docker backend container:

```bash
docker-compose exec backend python -m app.wellness_outreach
```

Or directly in the container:

```bash
docker-compose exec backend bash
python -m app.wellness_outreach
```

### As a Scheduled Job (Production)

#### Option 1: Docker Cron

Add to `docker-compose.yml` as a separate service:

```yaml
wellness-cron:
  build: ./backend
  command: >
    sh -c "echo '0 8 * * 1 cd /app && python -m app.wellness_outreach >> /var/log/cron.log 2>&1' > /etc/crontabs/root && crond -f"
  depends_on:
    - db
    - ollama
  environment:
    - DATABASE_URL=postgresql://user:password@db/interpawsdb
    - OLLAMA_HOST=http://ollama:11434
  volumes:
    - ./backend:/app
```

This runs every Monday at 8 AM.

#### Option 2: Host Cron

Add to your host machine's crontab:

```bash
# Run wellness outreach every Monday at 8 AM
0 8 * * 1 cd /path/to/Interpaws && docker-compose exec -T backend python -m app.wellness_outreach >> /var/log/interpaws-outreach.log 2>&1
```

#### Option 3: Python Scheduler (Recommended for Dev)

Create `backend/app/scheduler.py`:

```python
import asyncio
import schedule
import time
from app.wellness_outreach import main

async def job():
    await main()

def run_scheduler():
    schedule.every().monday.at("08:00").do(lambda: asyncio.run(job()))

    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    run_scheduler()
```

Then run: `docker-compose exec backend python -m app.scheduler`

## Output

### Console Output

```
🏥 Interpaws Wellness Outreach System
⏰ Run Time: 2025-11-13T10:30:00.000000
================================================================================
🔍 Identifying pets needing wellness outreach...
   Found 3 pets needing outreach.
📅 Finding open slots for next 7 days...
   Found 45 available slots.
✉️  Generating personalized outreach emails...

================================================================================
TO: john@example.com (John Doe)
RE: Wellness Check for Max
SUGGESTED SLOT: Monday, November 18 at 10:00 AM
================================================================================
Dear John Doe,

We hope this message finds you and Max doing well! It's been a while since
Max's last visit, and we wanted to reach out to schedule a wellness check...

[Email continues...]
================================================================================

📝 Emails logged to: /app/outreach_log.txt
================================================================================
📊 SUMMARY
================================================================================
Pets Identified: 3
Emails Generated: 3
✅ No errors!
================================================================================
✅ Wellness outreach complete!
```

### Log File Format

The script appends to `backend/outreach_log.txt`:

```
################################################################################
Wellness Outreach Run: 2025-11-13T10:30:00.000000
Pets Identified: 3
Emails Generated: 3
################################################################################

TO: john@example.com (John Doe)
RE: Wellness Check for Max
SLOT: 2025-11-18T10:00:00
--------------------------------------------------------------------------------
[Email body...]
================================================================================
```

## Error Handling

The script includes robust error handling:

1. **No pets found**: Exits gracefully with success message
2. **No available slots**: Logs error, returns summary with error count
3. **Individual email failures**: Catches exceptions per-pet, uses fallback template
4. **LLM failures**: Falls back to template email
5. **Database errors**: Propagates up, closes session properly in `finally` block

## Testing

### Create Test Data

Use the existing seed scripts or create test clients/pets manually:

```bash
# Create a client and pet with old booking
docker-compose exec backend python -c "
from app.database import SessionLocal
from app.models import Client, Pet, Booking
from datetime import datetime, timedelta
from passlib.context import CryptContext

db = SessionLocal()
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

# Create client
client = Client(
    name='Test User',
    email='test@example.com',
    hashed_password=pwd_context.hash('password'),
    clinic_id=1
)
db.add(client)
db.commit()

# Create pet
pet = Pet(
    name='Buddy',
    species='Dog',
    breed='Golden Retriever',
    client_id=client.id
)
db.add(pet)
db.commit()

# Create old booking (13 months ago)
old_date = datetime.utcnow() - timedelta(days=390)
booking = Booking(
    start_time=old_date,
    end_time=old_date + timedelta(hours=1),
    client_id=client.id,
    pet_id=pet.id,
    staff_id=1
)
db.add(booking)
db.commit()

print(f'Created test client {client.id} with pet {pet.id}')
"
```

### Run Script

```bash
docker-compose exec backend python -m app.wellness_outreach
```

### Verify Output

Check console output and `backend/outreach_log.txt` for generated emails.

## Integration with Existing System

### Database Schema

Uses existing tables:

- `clients` - Owner information
- `pets` - Pet records
- `bookings` - Appointment history
- `preferences` - Client preference vectors (for slot matching)
- `staff` - Available veterinarians

No new tables required.

### AI Services

Reuses existing infrastructure:

- `get_embedding()` - sentence-transformers for vector embeddings
- `get_ollama_recommendation()` - Ollama/llama3 for email generation

Ensure the Ollama container has the `llama3` model pulled:

```bash
docker-compose exec ollama ollama pull llama3
```

## Customization

### Email Tone

Modify the prompt in `generate_outreach_email()` to adjust tone, length, or content.

### Search Window

Adjust `LOOKAHEAD_DAYS` to search further ahead (e.g., 14 days).

### Business Hours

Modify `BUSINESS_START_HOUR` and `BUSINESS_END_HOUR` for different clinic hours.

### Eligibility Criteria

Change `LOOKBACK_MONTHS` or modify `get_target_pets()` logic for different criteria (e.g., only cats, or pets with specific conditions).

## Future Enhancements

1. **Email Delivery**: Integrate with SendGrid, Mailgun, or AWS SES
2. **Client Opt-Out**: Add preference for clients to disable outreach
3. **Smart Timing**: Use historical booking data to predict best times
4. **Multi-Language**: Detect client language preference and generate localized emails
5. **A/B Testing**: Test different email templates and measure booking conversion
6. **Pet-Specific Recommendations**: Include vaccination reminders, breed-specific care tips

## Troubleshooting

### "No available slots found"

- Check if staff members exist in database
- Verify `BUSINESS_START_HOUR` and `BUSINESS_END_HOUR` are correct
- Ensure date range includes weekdays

### "Ollama connection failed"

- Verify Ollama container is running: `docker-compose ps`
- Check model is pulled: `docker-compose exec ollama ollama list`
- Pull llama3: `docker-compose exec ollama ollama pull llama3`

### "No pets need outreach"

- Normal if all pets have recent or future bookings
- Create test data (see Testing section)
- Adjust `LOOKBACK_MONTHS` to a smaller value for testing

## Support

For issues or questions, refer to:

- Main project docs: `README.md`, `QUICK_START.md`
- Copilot instructions: `.github/copilot-instructions.md`
- Backend API docs: http://localhost:8000/docs

---

**Sprint**: 7 - Proactive Client Wellness Outreach  
**Version**: 1.0  
**Last Updated**: November 13, 2025
