"""
Data Simulator Script for Interpaws

This script populates the database with realistic test data including:
- Staff members with skills and embeddings
- Clients with authentication
- Pets
- Preferences with embeddings
- Bookings with complaint embeddings

Usage:
    python -m app.seed
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import List
from faker import Faker
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app import models
from app.auth import get_password_hash
from app.ai_services import get_embedding

# Initialize Faker
fake = Faker()

# Define realistic roles and skills
STAFF_ROLES = [
    'Veterinarian',
    'Technician',
    'Orthopedic Surgeon',
    'Dermatologist',
    'Cardiologist',
    'Emergency Veterinarian',
    'Dental Specialist',
    'Behavioral Specialist',
    'Exotic Animal Specialist',
    'Oncologist',
]

STAFF_SKILLS = {
    'Veterinarian': [
        "General practice veterinarian with 10 years experience in small animal care",
        "Experienced in routine checkups, vaccinations, and common illnesses",
        "Skilled in general surgery and preventive care for dogs and cats",
        "Expert in diagnosing and treating common pet ailments",
    ],
    'Technician': [
        "Certified veterinary technician specializing in surgical assistance",
        "Expert in laboratory procedures and diagnostic testing",
        "Skilled in patient care, monitoring, and post-operative recovery",
        "Experienced in handling anxious and aggressive animals",
    ],
    'Orthopedic Surgeon': [
        "Specialist in small animal orthopedics and joint replacements",
        "Expert in treating fractures, ligament tears, and bone diseases",
        "Skilled in advanced surgical techniques for mobility issues",
        "Experienced in post-operative rehabilitation for orthopedic cases",
    ],
    'Dermatologist': [
        "Specialist in feline and canine dermatology and allergic reactions",
        "Expert in treating skin conditions, allergies, and parasitic infections",
        "Skilled in diagnosing chronic skin issues and autoimmune disorders",
        "Experienced in managing hair loss, itching, and skin infections",
    ],
    'Cardiologist': [
        "Veterinary cardiologist specializing in heart disease in small animals",
        "Expert in diagnosing and treating congestive heart failure",
        "Skilled in echocardiography and cardiac monitoring",
        "Experienced in managing chronic heart conditions in elderly pets",
    ],
    'Emergency Veterinarian': [
        "Emergency care specialist available for critical and urgent cases",
        "Expert in trauma care, poisoning, and acute illness management",
        "Skilled in rapid assessment and life-saving interventions",
        "Experienced in handling high-stress emergency situations",
    ],
    'Dental Specialist': [
        "Veterinary dental specialist focusing on oral health and surgery",
        "Expert in teeth cleaning, extractions, and periodontal disease",
        "Skilled in treating dental infections and oral tumors",
        "Experienced in preventive dental care and oral hygiene education",
    ],
    'Behavioral Specialist': [
        "Animal behavior specialist for anxiety and aggression issues",
        "Expert in treating separation anxiety and destructive behaviors",
        "Skilled in positive reinforcement training and behavior modification",
        "Experienced in helping pets with fear and socialization problems",
    ],
    'Exotic Animal Specialist': [
        "Specialist in exotic pets including birds, reptiles, and small mammals",
        "Expert in the unique health needs of non-traditional pets",
        "Skilled in treating exotic animal diseases and dietary issues",
        "Experienced in handling and caring for rare and unusual species",
    ],
    'Oncologist': [
        "Veterinary oncologist specializing in cancer diagnosis and treatment",
        "Expert in chemotherapy, radiation therapy, and palliative care",
        "Skilled in surgical oncology and tumor removal",
        "Experienced in managing quality of life for pets with cancer",
    ],
}

# Pet species and breeds
PET_SPECIES_BREEDS = {
    'Dog': ['Labrador Retriever', 'German Shepherd', 'Golden Retriever', 'French Bulldog', 
            'Beagle', 'Poodle', 'Rottweiler', 'Yorkshire Terrier', 'Boxer', 'Dachshund'],
    'Cat': ['Domestic Shorthair', 'Siamese', 'Persian', 'Maine Coon', 'Ragdoll', 
            'Bengal', 'British Shorthair', 'Sphynx', 'Scottish Fold', 'Abyssinian'],
    'Bird': ['Parakeet', 'Cockatiel', 'African Grey', 'Macaw', 'Canary'],
    'Rabbit': ['Holland Lop', 'Netherland Dwarf', 'Flemish Giant', 'Rex', 'Lionhead'],
}

# Realistic complaint reasons
COMPLAINT_REASONS = [
    "limping on front left paw",
    "constant scratching and hair loss on back",
    "not eating for two days",
    "vomiting after meals",
    "excessive drinking and urination",
    "coughing and difficulty breathing",
    "swollen abdomen",
    "behavioral changes and aggression",
    "ear infection with discharge",
    "dental pain and bad breath",
    "skin rash and redness",
    "weight loss despite normal appetite",
    "diarrhea for several days",
    "eye discharge and squinting",
    "lump or mass noticed on body",
    "seizure episode",
    "lethargy and weakness",
    "broken nail and bleeding",
    "suspected poisoning",
    "anxiety and fear of loud noises",
    "chronic joint pain and stiffness",
    "heart murmur detected",
    "difficulty urinating",
    "fever and loss of appetite",
    "allergic reaction with swelling",
]

# Client preferences
CLIENT_PREFERENCES = [
    "Prefers morning appointments between 8-10 AM",
    "My dog is very anxious around other animals, please schedule accordingly",
    "Prefers the same veterinarian for consistency",
    "Needs appointments after 5 PM due to work schedule",
    "Cat is afraid of dogs, please keep separate in waiting room",
    "Prefers female veterinarians",
    "Needs extra time for appointments due to pet's anxiety",
    "Prefers to discuss treatment options thoroughly before proceeding",
    "My pet requires sedation for examinations",
    "Prefers natural and holistic treatment approaches when possible",
]


def create_staff(db: Session, count: int = 15) -> List[models.Staff]:
    """Generate staff members with skills and embeddings."""
    print(f"Creating {count} staff members...")
    staff_list = []
    
    for i in range(count):
        role = random.choice(STAFF_ROLES)
        name = fake.name()
        skills_description = random.choice(STAFF_SKILLS[role])
        
        # Generate embedding for skills
        skills_vector = asyncio.run(get_embedding(skills_description))
        
        staff = models.Staff(
            name=name,
            role=role,
            skills_description=skills_description,
            skills_vector=skills_vector
        )
        
        db.add(staff)
        staff_list.append(staff)
    
    db.commit()
    print(f"Created {len(staff_list)} staff members")
    return staff_list


def create_clinic(db: Session) -> models.Clinic:
    """Create a default clinic."""
    print("Creating clinic...")
    clinic = models.Clinic(name="Interpaws Veterinary Clinic")
    db.add(clinic)
    db.commit()
    print(f"Created clinic: {clinic.name}")
    return clinic


def create_clients(db: Session, clinic_id: int, count: int = 100) -> List[models.Client]:
    """Generate client users with hashed passwords."""
    print(f"Creating {count} clients...")
    clients_list = []
    
    for i in range(count):
        name = fake.name()
        email = fake.unique.email()
        # Use a default password for all test clients
        hashed_password = get_password_hash("password123")
        
        client = models.Client(
            name=name,
            email=email,
            hashed_password=hashed_password,
            clinic_id=clinic_id
        )
        
        db.add(client)
        clients_list.append(client)
    
    db.commit()
    print(f"Created {len(clients_list)} clients")
    return clients_list


def create_pets(db: Session, clients: List[models.Client]) -> List[models.Pet]:
    """Generate 1-3 pets for each client."""
    print("Creating pets...")
    pets_list = []
    
    for client in clients:
        # Each client gets 1-3 pets
        num_pets = random.randint(1, 3)
        
        for _ in range(num_pets):
            species = random.choice(list(PET_SPECIES_BREEDS.keys()))
            breed = random.choice(PET_SPECIES_BREEDS[species])
            name = fake.first_name()
            
            pet = models.Pet(
                name=name,
                species=species,
                breed=breed,
                client_id=client.id
            )
            
            db.add(pet)
            pets_list.append(pet)
    
    db.commit()
    print(f"Created {len(pets_list)} pets")
    return pets_list


def create_preferences(db: Session, clients: List[models.Client]) -> List[models.Preferences]:
    """Generate preferences for 20-30% of clients."""
    print("Creating client preferences...")
    preferences_list = []
    
    # Select 20-30% of clients randomly
    num_with_prefs = int(len(clients) * random.uniform(0.20, 0.30))
    clients_with_prefs = random.sample(clients, num_with_prefs)
    
    for client in clients_with_prefs:
        details = random.choice(CLIENT_PREFERENCES)
        
        # Generate embedding for preferences
        details_vector = asyncio.run(get_embedding(details))
        
        preference = models.Preferences(
            details=details,
            client_id=client.id,
            details_vector=details_vector
        )
        
        db.add(preference)
        preferences_list.append(preference)
    
    db.commit()
    print(f"Created {len(preferences_list)} preferences")
    return preferences_list


def create_bookings(
    db: Session,
    clients: List[models.Client],
    pets: List[models.Pet],
    staff: List[models.Staff],
    count: int = 300
) -> List[models.Booking]:
    """Generate bookings with complaint reasons and embeddings."""
    print(f"Creating {count} bookings...")
    bookings_list = []
    
    # Build a map of client_id to their pets for quick lookup
    client_pets_map = {}
    for pet in pets:
        if pet.client_id not in client_pets_map:
            client_pets_map[pet.client_id] = []
        client_pets_map[pet.client_id].append(pet)
    
    for i in range(count):
        # Random client
        client = random.choice(clients)
        
        # Get one of this client's pets
        client_pets = client_pets_map.get(client.id, [])
        if not client_pets:
            continue
        pet = random.choice(client_pets)
        
        # Random staff
        staff_member = random.choice(staff)
        
        # Random date in the past 60 days or future 30 days
        days_offset = random.randint(-60, 30)
        start_time = datetime.now() + timedelta(days=days_offset, hours=random.randint(8, 16))
        end_time = start_time + timedelta(hours=1)
        
        # Determine status
        if days_offset < 0:
            status = random.choice(['completed', 'completed', 'completed', 'cancelled'])
        else:
            status = 'confirmed'
        
        # 70% of bookings have a complaint reason
        complaint_reason = None
        complaint_vector = None
        if random.random() < 0.7:
            complaint_reason = random.choice(COMPLAINT_REASONS)
            # Generate embedding for complaint
            complaint_vector = asyncio.run(get_embedding(complaint_reason))
        
        booking = models.Booking(
            start_time=start_time,
            end_time=end_time,
            status=status,
            client_id=client.id,
            pet_id=pet.id,
            staff_id=staff_member.id,
            complaint_reason=complaint_reason,
            complaint_vector=complaint_vector
        )
        
        db.add(booking)
        bookings_list.append(booking)
    
    db.commit()
    print(f"Created {len(bookings_list)} bookings")
    return bookings_list


def main():
    """Main function to seed the database."""
    print("=" * 60)
    print("INTERPAWS DATA SIMULATOR")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Create clinic
        clinic = create_clinic(db)
        
        # Create staff
        staff = create_staff(db, count=15)
        
        # Create clients
        clients = create_clients(db, clinic_id=clinic.id, count=100)
        
        # Create pets
        pets = create_pets(db, clients)
        
        # Create preferences
        preferences = create_preferences(db, clients)
        
        # Create bookings
        bookings = create_bookings(db, clients, pets, staff, count=300)
        
        print("=" * 60)
        print("DATABASE SEEDING COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"Summary:")
        print(f"  - Clinics: 1")
        print(f"  - Staff: {len(staff)}")
        print(f"  - Clients: {len(clients)}")
        print(f"  - Pets: {len(pets)}")
        print(f"  - Preferences: {len(preferences)}")
        print(f"  - Bookings: {len(bookings)}")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
