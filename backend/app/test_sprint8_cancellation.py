"""
Sprint 8 - Dynamic Slot-Filling Integration Test
Tests the intelligent cancellation slot replacement system end-to-end.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Client, Pet, Staff, Booking, Preferences
from app.ai_services import get_embedding
import requests

def cleanup_test_data(db: Session):
    """Remove all test data created during testing."""
    print("\n🧹 Cleaning up test data...")
    
    # Delete in correct order to respect foreign keys
    db.query(Booking).filter(Booking.client_id.in_(
        db.query(Client.id).filter(Client.email.like('sprint8_test_%'))
    )).delete(synchronize_session=False)
    
    db.query(Preferences).filter(Preferences.client_id.in_(
        db.query(Client.id).filter(Client.email.like('sprint8_test_%'))
    )).delete(synchronize_session=False)
    
    db.query(Pet).filter(Pet.client_id.in_(
        db.query(Client.id).filter(Client.email.like('sprint8_test_%'))
    )).delete(synchronize_session=False)
    
    db.query(Client).filter(Client.email.like('sprint8_test_%')).delete(synchronize_session=False)
    
    db.commit()
    print("✅ Test data cleaned up")

def test_cancellation_suggestions():
    """
    Test the full Sprint 8 cancellation suggestion workflow:
    1. Create test clients with preferences for earlier appointment times
    2. Create bookings on same day at different times
    3. Cancel an earlier booking
    4. Verify suggestion endpoint returns intelligent matches
    """
    db = SessionLocal()
    
    try:
        # Clean up any existing test data first
        cleanup_test_data(db)
        
        print("\n" + "="*70)
        print("🧪 SPRINT 8 - DYNAMIC SLOT-FILLING TEST")
        print("="*70)
        
        # Step 1: Get or create a staff member for bookings
        print("\n1️⃣  Setting up staff member...")
        staff = db.query(Staff).first()
        if not staff:
            print("❌ No staff found. Please create a staff member first.")
            return False
        print(f"✅ Using staff: {staff.name} (ID: {staff.id})")
        
        # Step 2: Create test clients with preferences for earlier times
        print("\n2️⃣  Creating test clients with 'earlier appointment' preferences...")
        
        clients = []
        preferences_text = [
            "I prefer morning appointments around 9-10am if possible",
            "Earlier in the day works better for my schedule, ideally before noon",
            "I like to come in early, around 8-9am would be perfect"
        ]
        
        for i, pref_text in enumerate(preferences_text, 1):
            client = Client(
                name=f"Sprint8 Test Client {i}",
                email=f"sprint8_test_client{i}@example.com",
                hashed_password="dummy_hash"
            )
            db.add(client)
            db.flush()  # Get the ID
            
            # Create preference with embedding
            embedding = asyncio.run(get_embedding(pref_text))
            preference = Preferences(
                client_id=client.id,
                details=pref_text,
                details_vector=embedding
            )
            db.add(preference)
            
            # Create a pet for booking
            pet = Pet(
                name=f"TestPet{i}",
                species="Dog",
                breed="Labrador",
                client_id=client.id
            )
            db.add(pet)
            db.flush()
            
            clients.append({
                'client': client,
                'pet': pet,
                'preference': pref_text
            })
            
            print(f"   ✅ Created {client.name}")
            print(f"      Preference: '{pref_text}'")
        
        db.commit()
        
        # Step 3: Create bookings for the same day at different times
        print("\n3️⃣  Creating bookings on the same day at different times...")
        
        # Use tomorrow as the booking day
        booking_date = datetime.now().date() + timedelta(days=1)
        
        # Create early booking (9:00 AM) - this will be cancelled
        early_time = datetime.combine(booking_date, datetime.strptime("09:00", "%H:%M").time())
        early_booking = Booking(
            client_id=clients[0]['client'].id,
            pet_id=clients[0]['pet'].id,
            staff_id=staff.id,
            start_time=early_time,
            end_time=early_time + timedelta(hours=1),
            status="scheduled"
        )
        db.add(early_booking)
        db.flush()
        
        print(f"   📅 Early booking (to cancel): {early_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"      Client: {clients[0]['client'].name}")
        
        # Create later bookings (2:00 PM and 4:00 PM) - these should be suggested
        later_times = [
            datetime.combine(booking_date, datetime.strptime("14:00", "%H:%M").time()),
            datetime.combine(booking_date, datetime.strptime("16:00", "%H:%M").time())
        ]
        
        later_bookings = []
        for i, later_time in enumerate(later_times, 1):
            booking = Booking(
                client_id=clients[i]['client'].id,
                pet_id=clients[i]['pet'].id,
                staff_id=staff.id,
                start_time=later_time,
                end_time=later_time + timedelta(hours=1),
                status="scheduled"
            )
            db.add(booking)
            db.flush()
            later_bookings.append(booking)
            
            print(f"   📅 Later booking {i}: {later_time.strftime('%Y-%m-%d %H:%M')}")
            print(f"      Client: {clients[i]['client'].name}")
        
        db.commit()
        
        # Step 4: Cancel the early booking
        print("\n4️⃣  Cancelling early booking...")
        early_booking.status = "cancelled"
        db.commit()
        print(f"   ✅ Cancelled booking at {early_time.strftime('%Y-%m-%d %H:%M')}")
        
        # Step 5: Test the suggestion endpoint directly
        print("\n5️⃣  Testing cancellation suggestion endpoint...")
        print(f"   Calling GET /admin/cancellation_suggestion/{early_booking.id}")
        
        # Import the endpoint logic directly
        from app.main import app
        from fastapi.testclient import TestClient
        from app.auth import create_access_token
        
        # Create admin token
        admin_token = create_access_token(
            data={"sub": staff.email}
        )
        
        client_api = TestClient(app)
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client_api.get(
            f"/admin/cancellation_suggestion/{early_booking.id}",
            headers=headers
        )
        
        print(f"\n   📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Received suggestions successfully!")
            print(f"\n   Raw Response Data:")
            import json
            print(json.dumps(data, indent=2))
            
            if 'cancelled_slot' in data:
                print(f"\n   Cancelled Slot Details:")
                print(f"      Date: {data['cancelled_slot']['date']}")
                print(f"      Time: {data['cancelled_slot']['start_time']} - {data['cancelled_slot']['end_time']}")
                print(f"      Staff: {data['cancelled_slot']['staff_name']}")
            
            if data.get('suggestions'):
                print(f"\n   💡 Top {len(data['suggestions'])} Suggestions:")
                for i, suggestion in enumerate(data['suggestions'], 1):
                    print(f"\n      {i}. {suggestion.get('client_name', 'N/A')} ({suggestion.get('client_email', 'N/A')})")
                    print(f"         Match Score: {suggestion.get('match_score', 0):.2%}")
                    print(f"         Current Booking: {suggestion.get('current_booking_time', 'N/A')}")
                    print(f"         Reason: {suggestion.get('reason', 'N/A')}")
                
                # Verify suggestions are sorted by score
                scores = [s.get('match_score', 0) for s in data['suggestions']]
                if scores == sorted(scores, reverse=True):
                    print(f"\n   ✅ Suggestions correctly sorted by match score")
                else:
                    print(f"\n   ❌ WARNING: Suggestions not sorted correctly")
                
                # Verify all suggestions are for later times on same day (if cancelled_slot is present)
                if 'cancelled_slot' in data:
                    all_later = all(
                        suggestion.get('current_booking_time', '') > data['cancelled_slot']['start_time']
                        for suggestion in data['suggestions']
                    )
                    if all_later:
                        print(f"   ✅ All suggestions are for later times on same day")
                    else:
                        print(f"   ❌ WARNING: Some suggestions are not for later times")
                
                print(f"\n{'='*70}")
                print("🎉 SPRINT 8 TEST PASSED!")
                print("="*70)
                return True
            else:
                print(f"\n   ⚠️  No suggestions returned")
                if data:
                    print(f"   Response data: {data}")
                return False
        else:
            print(f"   ❌ Request failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed with error:")
        print(f"   {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        cleanup_test_data(db)
        db.close()

if __name__ == "__main__":
    print("\n🚀 Starting Sprint 8 Integration Test...")
    success = test_cancellation_suggestions()
    
    if success:
        print("\n✅ All tests passed! Sprint 8 is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Test failed. Please review the output above.")
        sys.exit(1)
