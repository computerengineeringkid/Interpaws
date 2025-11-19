"""
Wellness Outreach: Proactive Client Wellness Outreach System

This standalone script identifies pets due for care, matches them with open appointment 
slots based on client preferences (vector search), and generates personalized outreach 
emails using the LLM.

Designed to run as a scheduled job (cron), but callable manually for testing.
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from .database import SessionLocal
from .models import Client, Pet, Booking, Preferences, Staff
from .ai_services import get_embedding, get_ollama_recommendation
from .booking_logic import check_availability


# Configuration
LOOKBACK_MONTHS = 12  # Consider pets with no bookings in last 12 months
LOOKAHEAD_DAYS = 7    # Search for slots in the next 7 days
SLOT_DURATION_HOURS = 1  # Wellness check duration
BUSINESS_START_HOUR = 9  # 9 AM
BUSINESS_END_HOUR = 17   # 5 PM (last slot starts at 4 PM)
OUTREACH_LOG_FILE = "outreach_log.txt"


def get_target_pets(db: Session) -> List[Tuple[Pet, Client]]:
    """
    Identify "at-risk" pets that need wellness outreach.
    
    Criteria: Pets who have no future bookings AND 
    (have no past bookings OR last booking was > 12 months ago).
    
    Args:
        db: Database session
        
    Returns:
        List of tuples (Pet, Client) for pets needing outreach
    """
    now = datetime.utcnow()
    cutoff_date = now - timedelta(days=LOOKBACK_MONTHS * 30)
    
    # Get all pets with their clients
    all_pets = (
        db.query(Pet, Client)
        .join(Client, Pet.client_id == Client.id)
        .all()
    )
    
    target_pets = []
    
    for pet, client in all_pets:
        # Check for future bookings
        future_booking = (
            db.query(Booking)
            .filter(
                Booking.pet_id == pet.id,
                Booking.start_time > now
            )
            .first()
        )
        
        if future_booking:
            # Pet already has future booking, skip
            continue
        
        # Check last booking
        last_booking = (
            db.query(Booking)
            .filter(Booking.pet_id == pet.id)
            .order_by(Booking.start_time.desc())
            .first()
        )
        
        if last_booking is None or last_booking.start_time < cutoff_date:
            # No booking or last booking > 12 months ago
            target_pets.append((pet, client))
    
    return target_pets


def find_open_slots(db: Session, days_ahead: int = LOOKAHEAD_DAYS) -> List[dict]:
    """
    Find all open appointment slots for the next N days.
    
    Args:
        db: Database session
        days_ahead: Number of days to look ahead
        
    Returns:
        List of dicts with slot information: 
        {start_time, end_time, staff_id, staff_name, day_name, time_period}
    """
    now = datetime.utcnow()
    end_search = now + timedelta(days=days_ahead)
    
    # Get all staff who can perform wellness checks (all staff for now)
    all_staff = db.query(Staff).all()
    
    open_slots = []
    
    # Iterate through each day
    current_date = now.replace(hour=BUSINESS_START_HOUR, minute=0, second=0, microsecond=0)
    if current_date < now:
        current_date += timedelta(days=1)
    
    while current_date < end_search:
        # Skip weekends (assuming Monday=0, Sunday=6)
        if current_date.weekday() >= 5:
            current_date += timedelta(days=1)
            continue
        
        # Check each hour slot for each staff member
        for hour in range(BUSINESS_START_HOUR, BUSINESS_END_HOUR):
            slot_start = current_date.replace(hour=hour, minute=0, second=0, microsecond=0)
            slot_end = slot_start + timedelta(hours=SLOT_DURATION_HOURS)
            
            for staff in all_staff:
                if check_availability(db, staff.id, slot_start, slot_end):
                    # Determine time period for natural language matching
                    if hour < 12:
                        time_period = "Morning"
                    elif hour < 17:
                        time_period = "Afternoon"
                    else:
                        time_period = "Evening"
                    
                    open_slots.append({
                        "start_time": slot_start,
                        "end_time": slot_end,
                        "staff_id": staff.id,
                        "staff_name": staff.name,
                        "day_name": slot_start.strftime("%A"),  # e.g., "Monday"
                        "time_period": time_period,
                        "description": f"{slot_start.strftime('%A')} {time_period}",
                    })
        
        current_date += timedelta(days=1)
    
    return open_slots


def match_slot_to_preference(
    client: Client, 
    open_slots: List[dict], 
    db: Session
) -> dict:
    """
    Match the best slot to a client's preferences using vector search.
    
    If client has preferences with a vector, perform L2 distance search.
    Otherwise, return the first available slot.
    
    Args:
        client: The client to match
        open_slots: List of available slots
        db: Database session
        
    Returns:
        The best matching slot dict
    """
    if not open_slots:
        return None
    
    # Get client preferences
    preference = (
        db.query(Preferences)
        .filter(Preferences.client_id == client.id)
        .first()
    )
    
    if not preference or preference.details_vector is None:
        # No preference or no vector, return first available slot
        return open_slots[0]
    
    # Perform vector similarity search on slot descriptions
    best_slot = None
    best_distance = float('inf')
    
    for slot in open_slots:
        # Create embedding for slot description
        slot_embedding = get_embedding(slot["description"])
        
        # Calculate L2 distance manually (simple Euclidean distance)
        distance = sum(
            (a - b) ** 2 
            for a, b in zip(preference.details_vector, slot_embedding)
        ) ** 0.5
        
        if distance < best_distance:
            best_distance = distance
            best_slot = slot
    
    return best_slot


async def generate_outreach_email(
    pet: Pet,
    client: Client,
    slot: dict
) -> str:
    """
    Generate a personalized wellness outreach email using the LLM.
    
    Args:
        pet: The pet needing care
        client: The pet's owner
        slot: The suggested appointment slot
        
    Returns:
        Generated email text
    """
    slot_time = slot["start_time"].strftime("%A, %B %d at %I:%M %p")
    
    prompt = f"""Write a warm, professional veterinary outreach email for the following:

Pet Name: {pet.name}
Pet Species: {pet.species}
Owner Name: {client.name}
Suggested Appointment: {slot_time}
Veterinarian: {slot["staff_name"]}

The email should:
- Express genuine care for the pet's wellbeing
- Mention it's been a while since their last visit
- Suggest the specific appointment time
- Invite them to book or call if the time doesn't work
- Keep it concise (3-4 short paragraphs)
- Sign off professionally as "The Interpaws Team"

Write only the email body, no subject line."""

    try:
        email_content = await get_ollama_recommendation(prompt)
        return email_content
    except Exception as e:
        # Fallback email if LLM fails
        return f"""Dear {client.name},

We hope this message finds you and {pet.name} doing well! We noticed it's been a while since {pet.name}'s last visit, and we wanted to reach out about scheduling a wellness check.

We have an opening on {slot_time} with {slot["staff_name"]}. This would be a great opportunity to ensure {pet.name} is healthy and up-to-date on any needed care.

If this time works for you, please give us a call to confirm. If not, we're happy to find another time that fits your schedule better.

Looking forward to seeing you both soon!

Best regards,
The Interpaws Team"""


async def send_wellness_email(
    client_name: str,
    client_email: str,
    pet_name: str,
    html_content: str,
) -> None:
    """Send a wellness outreach email using SendGrid.

    Args:
        client_name: Name of the client
        client_email: Client email address
        pet_name: Name of the pet
        html_content: Email body in HTML
    """
    api_key = os.getenv("SENDGRID_API_KEY")
    from_email = os.getenv("SENDGRID_FROM_EMAIL")

    if not api_key or not from_email:
        raise ValueError("SendGrid configuration is missing")

    message = Mail(
        from_email=from_email,
        to_emails=client_email,
        subject=f"A wellness update for {pet_name} from Interpaws",
        html_content=html_content,
    )

    try:
        sg = SendGridAPIClient(api_key)
        await asyncio.to_thread(sg.send, message)
    except Exception as e:
        raise e


async def process_outreach(db: Session, log_to_file: bool = True) -> dict:
    """
    Main workflow: Identify pets, find slots, match preferences, generate emails.
    
    Args:
        db: Database session
        log_to_file: Whether to write emails to log file (default: True)
        
    Returns:
        Summary dict with counts and any errors
    """
    summary = {
        "total_pets_identified": 0,
        "emails_generated": 0,
        "errors": [],
        "emails": []
    }
    
    # Step 1: Identify target pets
    print("🔍 Identifying pets needing wellness outreach...")
    target_pets = get_target_pets(db)
    summary["total_pets_identified"] = len(target_pets)
    print(f"   Found {len(target_pets)} pets needing outreach.")
    
    if not target_pets:
        print("✅ No pets need outreach at this time.")
        return summary
    
    # Step 2: Find open slots
    print(f"📅 Finding open slots for next {LOOKAHEAD_DAYS} days...")
    open_slots = find_open_slots(db, LOOKAHEAD_DAYS)
    print(f"   Found {len(open_slots)} available slots.")
    
    if not open_slots:
        error_msg = "No available slots found. Cannot generate outreach."
        print(f"❌ {error_msg}")
        summary["errors"].append(error_msg)
        return summary
    
    # Step 3: Process each pet
    print(f"✉️  Generating personalized outreach emails...")
    
    for pet, client in target_pets:
        try:
            # Match slot to client preference
            best_slot = match_slot_to_preference(client, open_slots, db)
            
            if not best_slot:
                error_msg = f"No slot available for {client.name}'s pet {pet.name}"
                summary["errors"].append(error_msg)
                continue
            
            # Generate email
            email_content = await generate_outreach_email(pet, client, best_slot)

            try:
                await send_wellness_email(
                    client_name=client.name,
                    client_email=client.email,
                    pet_name=pet.name,
                    html_content=email_content,
                )
            except Exception as e:
                error_msg = f"Failed to send email to {client.email}: {e}"
                print(f"⚠️  {error_msg}")
                summary["errors"].append(error_msg)
                continue

            email_record = {
                "client_email": client.email,
                "client_name": client.name,
                "pet_name": pet.name,
                "slot_time": best_slot["start_time"].isoformat(),
                "email_body": email_content
            }
            
            summary["emails"].append(email_record)
            summary["emails_generated"] += 1
            
            # Print to stdout
            print(f"\n{'='*80}")
            print(f"TO: {client.email} ({client.name})")
            print(f"RE: Wellness Check for {pet.name}")
            print(f"SUGGESTED SLOT: {best_slot['start_time'].strftime('%A, %B %d at %I:%M %p')}")
            print(f"{'='*80}")
            print(email_content)
            print(f"{'='*80}\n")
            
        except Exception as e:
            error_msg = f"Error processing {client.name}/{pet.name}: {str(e)}"
            print(f"❌ {error_msg}")
            summary["errors"].append(error_msg)
    
    # Step 4: Log to file if requested
    if log_to_file and summary["emails_generated"] > 0:
        log_path = os.path.join(os.path.dirname(__file__), "..", OUTREACH_LOG_FILE)
        try:
            with open(log_path, "a") as f:
                f.write(f"\n{'#'*80}\n")
                f.write(f"Wellness Outreach Run: {datetime.utcnow().isoformat()}\n")
                f.write(f"Pets Identified: {summary['total_pets_identified']}\n")
                f.write(f"Emails Generated: {summary['emails_generated']}\n")
                f.write(f"{'#'*80}\n\n")
                
                for email in summary["emails"]:
                    f.write(f"TO: {email['client_email']} ({email['client_name']})\n")
                    f.write(f"RE: Wellness Check for {email['pet_name']}\n")
                    f.write(f"SLOT: {email['slot_time']}\n")
                    f.write(f"{'-'*80}\n")
                    f.write(f"{email['email_body']}\n")
                    f.write(f"{'='*80}\n\n")
            
            print(f"📝 Emails logged to: {log_path}")
        except Exception as e:
            error_msg = f"Failed to write log file: {str(e)}"
            print(f"⚠️  {error_msg}")
            summary["errors"].append(error_msg)
    
    return summary


async def main():
    """
    Main entry point for the wellness outreach script.
    Run this as a scheduled job or manually for testing.
    """
    print("🏥 Interpaws Wellness Outreach System")
    print(f"⏰ Run Time: {datetime.utcnow().isoformat()}")
    print("=" * 80)
    
    db = SessionLocal()
    
    try:
        summary = await process_outreach(db, log_to_file=True)
        
        print("\n" + "=" * 80)
        print("📊 SUMMARY")
        print("=" * 80)
        print(f"Pets Identified: {summary['total_pets_identified']}")
        print(f"Emails Generated: {summary['emails_generated']}")
        
        if summary['errors']:
            print(f"\n⚠️  Errors Encountered: {len(summary['errors'])}")
            for error in summary['errors']:
                print(f"   - {error}")
        else:
            print("✅ No errors!")
        
        print("=" * 80)
        print("✅ Wellness outreach complete!\n")
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
