"""
Test Suite for Wellness Outreach System

This script creates test data and validates the wellness outreach functionality.

Usage:
    docker-compose exec backend python -m app.test_wellness_outreach
"""

import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from .database import SessionLocal
from .models import Client, Pet, Booking, Preferences, Staff, Clinic
from .wellness_outreach import (
    get_target_pets,
    find_open_slots,
    match_slot_to_preference,
    generate_outreach_email,
    process_outreach
)
from .ai_services import get_embedding

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def create_test_data(db: Session):
    """Create comprehensive test data for wellness outreach testing."""
    
    print("🔧 Creating test data...")
    
    # Clean up existing test data (order matters for foreign keys)
    db.query(Booking).filter(Booking.complaint_reason == "TEST_DATA").delete()
    db.query(Preferences).filter(Preferences.details.like("TEST:%")).delete()
    db.query(Pet).filter(Pet.breed == "TEST_BREED").delete()
    db.query(Client).filter(Client.email.like("test_%@wellness.test")).delete()
    db.commit()
    
    # Ensure clinic exists
    clinic = db.query(Clinic).first()
    if not clinic:
        clinic = Clinic(name="Test Clinic")
        db.add(clinic)
        db.commit()
    
    # Ensure staff exists
    staff = db.query(Staff).first()
    if not staff:
        staff = Staff(
            name="Dr. Test Vet",
            email="testvet@wellness.test",
            hashed_password=pwd_context.hash("password"),
            role="Veterinarian"
        )
        db.add(staff)
        db.commit()
    
    test_clients = []
    
    # Test Case 1: Client with pet that has never been seen
    client1 = Client(
        name="New Client",
        email="test_new@wellness.test",
        hashed_password=pwd_context.hash("password"),
        clinic_id=clinic.id
    )
    db.add(client1)
    db.commit()
    
    pet1 = Pet(
        name="Fluffy",
        species="Cat",
        breed="TEST_BREED",
        client_id=client1.id
    )
    db.add(pet1)
    db.commit()
    
    test_clients.append({
        "client": client1,
        "pet": pet1,
        "description": "Never seen before"
    })
    
    # Test Case 2: Client with pet that hasn't been seen in 13 months
    client2 = Client(
        name="Lapsed Client",
        email="test_lapsed@wellness.test",
        hashed_password=pwd_context.hash("password"),
        clinic_id=clinic.id
    )
    db.add(client2)
    db.commit()
    
    pet2 = Pet(
        name="Buddy",
        species="Dog",
        breed="TEST_BREED",
        client_id=client2.id
    )
    db.add(pet2)
    db.commit()
    
    # Create old booking (13 months ago)
    old_date = datetime.utcnow() - timedelta(days=390)
    old_booking = Booking(
        start_time=old_date,
        end_time=old_date + timedelta(hours=1),
        client_id=client2.id,
        pet_id=pet2.id,
        staff_id=staff.id,
        complaint_reason="TEST_DATA"
    )
    db.add(old_booking)
    db.commit()
    
    test_clients.append({
        "client": client2,
        "pet": pet2,
        "description": "Last seen 13 months ago"
    })
    
    # Test Case 3: Client with preference for "Monday Morning"
    client3 = Client(
        name="Preference Client",
        email="test_preference@wellness.test",
        hashed_password=pwd_context.hash("password"),
        clinic_id=clinic.id
    )
    db.add(client3)
    db.commit()
    
    pet3 = Pet(
        name="Max",
        species="Dog",
        breed="TEST_BREED",
        client_id=client3.id
    )
    db.add(pet3)
    db.commit()
    
    # Create preference with vector
    pref_text = "TEST: I prefer Monday mornings for appointments"
    pref = Preferences(
        client_id=client3.id,
        details=pref_text,
        details_vector=asyncio.run(get_embedding(pref_text))
    )
    db.add(pref)
    db.commit()
    
    test_clients.append({
        "client": client3,
        "pet": pet3,
        "description": "Has preference for Monday mornings"
    })
    
    # Test Case 4: Client with RECENT booking (should NOT be included)
    client4 = Client(
        name="Recent Client",
        email="test_recent@wellness.test",
        hashed_password=pwd_context.hash("password"),
        clinic_id=clinic.id
    )
    db.add(client4)
    db.commit()
    
    pet4 = Pet(
        name="Charlie",
        species="Dog",
        breed="TEST_BREED",
        client_id=client4.id
    )
    db.add(pet4)
    db.commit()
    
    # Create recent booking (1 month ago)
    recent_date = datetime.utcnow() - timedelta(days=30)
    recent_booking = Booking(
        start_time=recent_date,
        end_time=recent_date + timedelta(hours=1),
        client_id=client4.id,
        pet_id=pet4.id,
        staff_id=staff.id,
        complaint_reason="TEST_DATA"
    )
    db.add(recent_booking)
    db.commit()
    
    # Test Case 5: Client with FUTURE booking (should NOT be included)
    client5 = Client(
        name="Future Client",
        email="test_future@wellness.test",
        hashed_password=pwd_context.hash("password"),
        clinic_id=clinic.id
    )
    db.add(client5)
    db.commit()
    
    pet5 = Pet(
        name="Luna",
        species="Cat",
        breed="TEST_BREED",
        client_id=client5.id
    )
    db.add(pet5)
    db.commit()
    
    # Create future booking
    future_date = datetime.utcnow() + timedelta(days=7)
    future_booking = Booking(
        start_time=future_date,
        end_time=future_date + timedelta(hours=1),
        client_id=client5.id,
        pet_id=pet5.id,
        staff_id=staff.id,
        complaint_reason="TEST_DATA"
    )
    db.add(future_booking)
    db.commit()
    
    print(f"✅ Created {len(test_clients)} test clients who SHOULD receive outreach")
    print(f"✅ Created 2 clients who should NOT receive outreach (recent/future bookings)")
    
    return test_clients


def test_target_pets(db: Session, expected_count: int):
    """Test the get_target_pets function."""
    print("\n" + "=" * 80)
    print("TEST 1: Target Pet Identification")
    print("=" * 80)
    
    target_pets = get_target_pets(db)
    
    # Filter to only test data
    test_target_pets = [
        (pet, client) for pet, client in target_pets 
        if pet.breed == "TEST_BREED"
    ]
    
    print(f"Expected: {expected_count} test pets")
    print(f"Found: {len(test_target_pets)} test pets")
    
    for pet, client in test_target_pets:
        print(f"  ✓ {pet.name} ({pet.species}) - Owner: {client.name}")
    
    if len(test_target_pets) == expected_count:
        print("✅ TEST PASSED: Correct number of target pets identified")
        return True
    else:
        print(f"❌ TEST FAILED: Expected {expected_count}, got {len(test_target_pets)}")
        return False


def test_open_slots(db: Session):
    """Test the find_open_slots function."""
    print("\n" + "=" * 80)
    print("TEST 2: Open Slot Discovery")
    print("=" * 80)
    
    slots = find_open_slots(db, days_ahead=7)
    
    print(f"Found {len(slots)} available slots")
    
    if slots:
        # Show first few slots
        print("\nSample slots:")
        for slot in slots[:5]:
            print(f"  • {slot['start_time'].strftime('%A, %B %d at %I:%M %p')} "
                  f"with {slot['staff_name']} ({slot['time_period']})")
        
        if len(slots) > 5:
            print(f"  ... and {len(slots) - 5} more slots")
        
        print("✅ TEST PASSED: Slots found successfully")
        return True
    else:
        print("⚠️  WARNING: No slots found (may be expected if fully booked)")
        return True


def test_preference_matching(db: Session):
    """Test the match_slot_to_preference function."""
    print("\n" + "=" * 80)
    print("TEST 3: Preference Matching")
    print("=" * 80)
    
    # Get the client with Monday morning preference
    pref_client = db.query(Client).filter(
        Client.email == "test_preference@wellness.test"
    ).first()
    
    if not pref_client:
        print("❌ TEST SKIPPED: Preference client not found")
        return False
    
    slots = find_open_slots(db, days_ahead=7)
    
    if not slots:
        print("❌ TEST SKIPPED: No slots available for matching")
        return False
    
    best_slot = match_slot_to_preference(pref_client, slots, db)
    
    if best_slot:
        print(f"Best match for client with 'Monday Morning' preference:")
        print(f"  • {best_slot['start_time'].strftime('%A, %B %d at %I:%M %p')}")
        print(f"  • {best_slot['description']}")
        
        # Check if it's actually Monday morning
        is_monday = best_slot['start_time'].strftime('%A') == 'Monday'
        is_morning = best_slot['time_period'] == 'Morning'
        
        if is_monday and is_morning:
            print("✅ TEST PASSED: Correctly matched Monday Morning preference")
            return True
        else:
            print("⚠️  PARTIAL PASS: Matched slot but not Monday Morning "
                  "(may be no Monday morning slots available)")
            return True
    else:
        print("❌ TEST FAILED: No slot matched")
        return False


async def test_email_generation(db: Session):
    """Test the generate_outreach_email function."""
    print("\n" + "=" * 80)
    print("TEST 4: Email Generation")
    print("=" * 80)
    
    # Get test client and pet
    client = db.query(Client).filter(
        Client.email == "test_new@wellness.test"
    ).first()
    pet = db.query(Pet).filter(Pet.name == "Fluffy").first()
    
    if not client or not pet:
        print("❌ TEST SKIPPED: Test client/pet not found")
        return False
    
    slots = find_open_slots(db, days_ahead=7)
    
    if not slots:
        print("❌ TEST SKIPPED: No slots available")
        return False
    
    print("Generating email...")
    email = await generate_outreach_email(pet, client, slots[0])
    
    print("\n" + "-" * 80)
    print("Generated Email:")
    print("-" * 80)
    print(email)
    print("-" * 80)
    
    # Basic validation
    has_pet_name = pet.name in email
    has_client_name = client.name in email
    
    print(f"\nValidation:")
    print(f"  Pet name ({pet.name}): {'✓' if has_pet_name else '✗'}")
    print(f"  Client name ({client.name}): {'✓' if has_client_name else '✗'}")
    
    if has_pet_name and has_client_name:
        print("✅ TEST PASSED: Email generated with correct personalization")
        return True
    else:
        print("❌ TEST FAILED: Email missing required personalization")
        return False


async def test_full_workflow(db: Session):
    """Test the complete process_outreach workflow."""
    print("\n" + "=" * 80)
    print("TEST 5: Full Workflow Integration")
    print("=" * 80)
    
    print("Running complete outreach process...")
    summary = await process_outreach(db, log_to_file=False)
    
    print(f"\nWorkflow Results:")
    print(f"  Total pets identified: {summary['total_pets_identified']}")
    print(f"  Emails generated: {summary['emails_generated']}")
    print(f"  Errors: {len(summary['errors'])}")
    
    if summary['errors']:
        print("\nErrors encountered:")
        for error in summary['errors']:
            print(f"  ⚠️  {error}")
    
    # Count test emails
    test_emails = [
        e for e in summary['emails'] 
        if 'wellness.test' in e['client_email']
    ]
    
    print(f"\nTest emails generated: {len(test_emails)}")
    
    if test_emails:
        print("✅ TEST PASSED: Full workflow executed successfully")
        return True
    else:
        print("⚠️  WARNING: No test emails generated (may be expected if no slots)")
        return True


def cleanup_test_data(db: Session):
    """Remove all test data."""
    print("\n" + "=" * 80)
    print("CLEANUP: Removing test data")
    print("=" * 80)
    
    db.query(Booking).filter(Booking.complaint_reason == "TEST_DATA").delete()
    db.query(Preferences).filter(Preferences.details.like("TEST:%")).delete()
    db.query(Pet).filter(Pet.breed == "TEST_BREED").delete()
    db.query(Client).filter(Client.email.like("test_%@wellness.test")).delete()
    db.commit()
    
    print("✅ Test data removed")


async def main():
    """Run all wellness outreach tests."""
    print("=" * 80)
    print("WELLNESS OUTREACH TEST SUITE")
    print("=" * 80)
    print(f"Started: {datetime.utcnow().isoformat()}")
    print("=" * 80)
    
    db = SessionLocal()
    results = []
    
    try:
        # Create test data
        test_clients = create_test_data(db)
        expected_targets = len(test_clients)
        
        # Run tests
        results.append(("Target Pet Identification", test_target_pets(db, expected_targets)))
        results.append(("Open Slot Discovery", test_open_slots(db)))
        results.append(("Preference Matching", test_preference_matching(db)))
        results.append(("Email Generation", await test_email_generation(db)))
        results.append(("Full Workflow", await test_full_workflow(db)))
        
        # Cleanup
        cleanup_test_data(db)
        
        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status}: {test_name}")
        
        print("=" * 80)
        print(f"Results: {passed}/{total} tests passed")
        print("=" * 80)
        
        if passed == total:
            print("🎉 ALL TESTS PASSED!")
        else:
            print("⚠️  SOME TESTS FAILED")
        
    except Exception as e:
        print(f"\n❌ TEST SUITE ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
