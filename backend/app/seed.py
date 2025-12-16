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
    """Generate staff members with skills, embeddings, and login credentials."""
    print(f"Creating {count} staff members...")
    staff_list = []

    for i in range(count):
        role = random.choice(STAFF_ROLES)
        name = fake.name()
        email = fake.unique.email()
        skills_description = random.choice(STAFF_SKILLS[role])

        # Generate embedding for skills
        skills_vector = asyncio.run(get_embedding(skills_description))

        # Hash password (password123 for all staff)
        hashed_password = get_password_hash("password123")

        staff = models.Staff(
            name=name,
            email=email,
            hashed_password=hashed_password,
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


# Medication data
MEDICATIONS = [
    {"name": "Carprofen", "description": "Non-steroidal anti-inflammatory for pain relief", "stock_quantity": 150, "unit": "tablets"},
    {"name": "Amoxicillin", "description": "Broad-spectrum antibiotic", "stock_quantity": 200, "unit": "capsules"},
    {"name": "Metronidazole", "description": "Antibiotic for GI and dental infections", "stock_quantity": 100, "unit": "tablets"},
    {"name": "Prednisone", "description": "Corticosteroid for inflammation and allergies", "stock_quantity": 180, "unit": "tablets"},
    {"name": "Gabapentin", "description": "Pain medication and anti-anxiety", "stock_quantity": 120, "unit": "capsules"},
    {"name": "Apoquel", "description": "Allergy and itch relief medication", "stock_quantity": 80, "unit": "tablets"},
    {"name": "Heartgard", "description": "Monthly heartworm prevention", "stock_quantity": 50, "unit": "chewables"},
    {"name": "Frontline Plus", "description": "Flea and tick prevention", "stock_quantity": 60, "unit": "doses"},
    {"name": "Cerenia", "description": "Anti-nausea medication", "stock_quantity": 40, "unit": "tablets"},
    {"name": "Tramadol", "description": "Pain relief for moderate to severe pain", "stock_quantity": 90, "unit": "tablets"},
    {"name": "Clavamox", "description": "Antibiotic for skin and soft tissue infections", "stock_quantity": 75, "unit": "tablets"},
    {"name": "Rimadyl", "description": "NSAID for arthritis and pain", "stock_quantity": 110, "unit": "tablets"},
    {"name": "Vetsulin", "description": "Insulin for diabetic pets", "stock_quantity": 15, "unit": "vials"},
    {"name": "Adequan", "description": "Injectable for joint health", "stock_quantity": 25, "unit": "vials"},
    {"name": "Baytril", "description": "Fluoroquinolone antibiotic", "stock_quantity": 65, "unit": "tablets"},
    {"name": "Simplicef", "description": "Antibiotic for skin infections", "stock_quantity": 45, "unit": "tablets"},
    {"name": "Onsior", "description": "NSAID for cats", "stock_quantity": 30, "unit": "tablets"},
    {"name": "Convenia", "description": "Long-acting injectable antibiotic", "stock_quantity": 20, "unit": "vials"},
    {"name": "Ketamine", "description": "Anesthetic agent", "stock_quantity": 10, "unit": "vials"},
    {"name": "Propofol", "description": "Anesthetic induction agent", "stock_quantity": 8, "unit": "vials"},
]

SURGERY_TYPES = [
    "Spay",
    "Neuter",
    "Dental Cleaning",
    "Mass Removal",
    "Orthopedic Repair",
    "Laceration Repair",
    "Foreign Body Removal",
    "Cystotomy",
    "Gastropexy",
    "Enucleation",
]

# Comprehensive inventory items for an animal hospital
INVENTORY_ITEMS = [
    # Medications
    {"name": "Carprofen 75mg", "category": "medications", "subcategory": "NSAID", "stock_quantity": 150, "min_stock_level": 20, "unit": "tablets", "unit_cost": 75, "location": "Pharmacy Shelf A"},
    {"name": "Amoxicillin 250mg", "category": "medications", "subcategory": "antibiotic", "stock_quantity": 200, "min_stock_level": 30, "unit": "capsules", "unit_cost": 45, "location": "Pharmacy Shelf A"},
    {"name": "Rabies Vaccine", "category": "medications", "subcategory": "vaccine", "stock_quantity": 50, "min_stock_level": 10, "unit": "doses", "unit_cost": 1200, "location": "Vaccine Fridge"},
    {"name": "DHPP Vaccine", "category": "medications", "subcategory": "vaccine", "stock_quantity": 45, "min_stock_level": 10, "unit": "doses", "unit_cost": 1500, "location": "Vaccine Fridge"},
    {"name": "FVRCP Vaccine", "category": "medications", "subcategory": "vaccine", "stock_quantity": 40, "min_stock_level": 10, "unit": "doses", "unit_cost": 1400, "location": "Vaccine Fridge"},
    {"name": "Ketamine 100mg/ml", "category": "medications", "subcategory": "anesthetic", "stock_quantity": 10, "min_stock_level": 3, "unit": "vials", "unit_cost": 4500, "location": "Controlled Substances"},
    {"name": "Propofol", "category": "medications", "subcategory": "anesthetic", "stock_quantity": 8, "min_stock_level": 2, "unit": "vials", "unit_cost": 8500, "location": "Controlled Substances"},

    # Surgical instruments
    {"name": "Scalpel Blades #10", "category": "surgical", "subcategory": "blades", "stock_quantity": 100, "min_stock_level": 20, "unit": "units", "unit_cost": 50, "location": "Surgery Suite"},
    {"name": "Scalpel Blades #15", "category": "surgical", "subcategory": "blades", "stock_quantity": 100, "min_stock_level": 20, "unit": "units", "unit_cost": 50, "location": "Surgery Suite"},
    {"name": "Suture Kit 3-0 Vicryl", "category": "surgical", "subcategory": "sutures", "stock_quantity": 50, "min_stock_level": 10, "unit": "kits", "unit_cost": 850, "location": "Surgery Suite"},
    {"name": "Suture Kit 4-0 Monocryl", "category": "surgical", "subcategory": "sutures", "stock_quantity": 40, "min_stock_level": 10, "unit": "kits", "unit_cost": 950, "location": "Surgery Suite"},
    {"name": "Hemostatic Forceps", "category": "surgical", "subcategory": "instruments", "stock_quantity": 12, "min_stock_level": 4, "unit": "units", "unit_cost": 4500, "location": "Surgery Suite"},
    {"name": "Needle Holders", "category": "surgical", "subcategory": "instruments", "stock_quantity": 8, "min_stock_level": 3, "unit": "units", "unit_cost": 5500, "location": "Surgery Suite"},

    # Supplies
    {"name": "Gauze Pads 4x4", "category": "supplies", "subcategory": "bandaging", "stock_quantity": 500, "min_stock_level": 100, "unit": "units", "unit_cost": 15, "location": "Supply Room"},
    {"name": "Vet Wrap 2 inch", "category": "supplies", "subcategory": "bandaging", "stock_quantity": 100, "min_stock_level": 20, "unit": "rolls", "unit_cost": 350, "location": "Supply Room"},
    {"name": "Vet Wrap 4 inch", "category": "supplies", "subcategory": "bandaging", "stock_quantity": 80, "min_stock_level": 15, "unit": "rolls", "unit_cost": 450, "location": "Supply Room"},
    {"name": "Syringes 3ml", "category": "supplies", "subcategory": "injection", "stock_quantity": 200, "min_stock_level": 50, "unit": "units", "unit_cost": 25, "location": "Supply Room"},
    {"name": "Syringes 10ml", "category": "supplies", "subcategory": "injection", "stock_quantity": 150, "min_stock_level": 30, "unit": "units", "unit_cost": 35, "location": "Supply Room"},
    {"name": "IV Catheters 22g", "category": "supplies", "subcategory": "IV", "stock_quantity": 100, "min_stock_level": 20, "unit": "units", "unit_cost": 250, "location": "Treatment Area"},
    {"name": "IV Catheters 24g", "category": "supplies", "subcategory": "IV", "stock_quantity": 80, "min_stock_level": 15, "unit": "units", "unit_cost": 250, "location": "Treatment Area"},
    {"name": "Exam Gloves (M)", "category": "supplies", "subcategory": "PPE", "stock_quantity": 500, "min_stock_level": 100, "unit": "pairs", "unit_cost": 15, "location": "Supply Room"},
    {"name": "Exam Gloves (L)", "category": "supplies", "subcategory": "PPE", "stock_quantity": 500, "min_stock_level": 100, "unit": "pairs", "unit_cost": 15, "location": "Supply Room"},
    {"name": "Surgical Gloves Sterile", "category": "supplies", "subcategory": "PPE", "stock_quantity": 100, "min_stock_level": 20, "unit": "pairs", "unit_cost": 150, "location": "Surgery Suite"},
    {"name": "Face Masks", "category": "supplies", "subcategory": "PPE", "stock_quantity": 200, "min_stock_level": 50, "unit": "units", "unit_cost": 25, "location": "Supply Room"},

    # Diagnostic
    {"name": "Blood Collection Tubes (Purple)", "category": "diagnostic", "subcategory": "blood collection", "stock_quantity": 100, "min_stock_level": 25, "unit": "tubes", "unit_cost": 75, "location": "Lab"},
    {"name": "Blood Collection Tubes (Red)", "category": "diagnostic", "subcategory": "blood collection", "stock_quantity": 100, "min_stock_level": 25, "unit": "tubes", "unit_cost": 75, "location": "Lab"},
    {"name": "Fecal Float Solution", "category": "diagnostic", "subcategory": "parasitology", "stock_quantity": 10, "min_stock_level": 2, "unit": "liters", "unit_cost": 2500, "location": "Lab"},
    {"name": "Urine Test Strips", "category": "diagnostic", "subcategory": "urinalysis", "stock_quantity": 200, "min_stock_level": 50, "unit": "strips", "unit_cost": 50, "location": "Lab"},
    {"name": "Heartworm Test Kits", "category": "diagnostic", "subcategory": "serology", "stock_quantity": 50, "min_stock_level": 10, "unit": "kits", "unit_cost": 800, "location": "Lab"},
    {"name": "FeLV/FIV Test Kits", "category": "diagnostic", "subcategory": "serology", "stock_quantity": 30, "min_stock_level": 10, "unit": "kits", "unit_cost": 1200, "location": "Lab"},

    # Equipment
    {"name": "Digital Thermometer", "category": "equipment", "subcategory": "monitoring", "stock_quantity": 10, "min_stock_level": 3, "unit": "units", "unit_cost": 2500, "location": "Exam Rooms"},
    {"name": "Stethoscope", "category": "equipment", "subcategory": "monitoring", "stock_quantity": 8, "min_stock_level": 3, "unit": "units", "unit_cost": 15000, "location": "Exam Rooms"},
    {"name": "Otoscope", "category": "equipment", "subcategory": "examination", "stock_quantity": 4, "min_stock_level": 2, "unit": "units", "unit_cost": 25000, "location": "Exam Rooms"},
    {"name": "Ophthalmoscope", "category": "equipment", "subcategory": "examination", "stock_quantity": 3, "min_stock_level": 1, "unit": "units", "unit_cost": 35000, "location": "Exam Rooms"},
    {"name": "Nail Clippers (Large)", "category": "equipment", "subcategory": "grooming", "stock_quantity": 6, "min_stock_level": 2, "unit": "units", "unit_cost": 2000, "location": "Treatment Area"},
    {"name": "Nail Clippers (Small)", "category": "equipment", "subcategory": "grooming", "stock_quantity": 6, "min_stock_level": 2, "unit": "units", "unit_cost": 1500, "location": "Treatment Area"},

    # Office
    {"name": "Patient Intake Forms", "category": "office", "subcategory": "forms", "stock_quantity": 500, "min_stock_level": 100, "unit": "sheets", "unit_cost": 5, "location": "Front Desk"},
    {"name": "Prescription Pads", "category": "office", "subcategory": "forms", "stock_quantity": 20, "min_stock_level": 5, "unit": "pads", "unit_cost": 500, "location": "Pharmacy"},
    {"name": "Cleaning Wipes", "category": "office", "subcategory": "cleaning", "stock_quantity": 50, "min_stock_level": 10, "unit": "containers", "unit_cost": 800, "location": "Supply Room"},
    {"name": "Hand Sanitizer", "category": "office", "subcategory": "cleaning", "stock_quantity": 30, "min_stock_level": 10, "unit": "bottles", "unit_cost": 600, "location": "Supply Room"},
]

# Service pricing
SERVICES = [
    # Checkups
    {"name": "Wellness Exam", "category": "checkup", "description": "Comprehensive annual wellness examination", "duration_minutes": 30, "base_price": 6500},
    {"name": "New Patient Exam", "category": "checkup", "description": "Initial examination for new patients", "duration_minutes": 45, "base_price": 8500},
    {"name": "Follow-up Exam", "category": "checkup", "description": "Follow-up visit for ongoing conditions", "duration_minutes": 20, "base_price": 4500},
    {"name": "Senior Wellness Exam", "category": "checkup", "description": "Comprehensive exam for senior pets (7+ years)", "duration_minutes": 45, "base_price": 9500},

    # Vaccinations
    {"name": "Rabies Vaccine", "category": "vaccination", "description": "Required rabies vaccination", "duration_minutes": 15, "base_price": 2500},
    {"name": "DHPP Vaccine", "category": "vaccination", "description": "Distemper, Hepatitis, Parvo, Parainfluenza", "duration_minutes": 15, "base_price": 3500},
    {"name": "FVRCP Vaccine", "category": "vaccination", "description": "Feline viral rhinotracheitis, calicivirus, panleukopenia", "duration_minutes": 15, "base_price": 3000},
    {"name": "Bordetella Vaccine", "category": "vaccination", "description": "Kennel cough prevention", "duration_minutes": 15, "base_price": 2500},
    {"name": "Lyme Vaccine", "category": "vaccination", "description": "Lyme disease prevention", "duration_minutes": 15, "base_price": 3500},
    {"name": "FeLV Vaccine", "category": "vaccination", "description": "Feline leukemia virus vaccine", "duration_minutes": 15, "base_price": 3500},

    # Surgery
    {"name": "Spay (Dog)", "category": "surgery", "description": "Ovariohysterectomy for female dogs", "duration_minutes": 60, "base_price": 35000},
    {"name": "Neuter (Dog)", "category": "surgery", "description": "Castration for male dogs", "duration_minutes": 45, "base_price": 25000},
    {"name": "Spay (Cat)", "category": "surgery", "description": "Ovariohysterectomy for female cats", "duration_minutes": 45, "base_price": 25000},
    {"name": "Neuter (Cat)", "category": "surgery", "description": "Castration for male cats", "duration_minutes": 30, "base_price": 18000},
    {"name": "Mass Removal", "category": "surgery", "description": "Surgical removal of masses/tumors", "duration_minutes": 60, "base_price": 45000},
    {"name": "Laceration Repair", "category": "surgery", "description": "Wound repair and suturing", "duration_minutes": 45, "base_price": 35000},

    # Dental
    {"name": "Dental Cleaning", "category": "dental", "description": "Professional dental cleaning under anesthesia", "duration_minutes": 60, "base_price": 35000},
    {"name": "Dental Extraction (Simple)", "category": "dental", "description": "Simple tooth extraction", "duration_minutes": 30, "base_price": 15000},
    {"name": "Dental Extraction (Surgical)", "category": "dental", "description": "Surgical tooth extraction", "duration_minutes": 45, "base_price": 25000},
    {"name": "Dental X-rays", "category": "dental", "description": "Full mouth dental radiographs", "duration_minutes": 30, "base_price": 18000},

    # Diagnostics
    {"name": "Blood Panel (Basic)", "category": "diagnostic", "description": "Basic CBC and chemistry panel", "duration_minutes": 15, "base_price": 12000},
    {"name": "Blood Panel (Comprehensive)", "category": "diagnostic", "description": "Complete blood work and organ function", "duration_minutes": 15, "base_price": 22000},
    {"name": "Urinalysis", "category": "diagnostic", "description": "Complete urine analysis", "duration_minutes": 15, "base_price": 5500},
    {"name": "Fecal Exam", "category": "diagnostic", "description": "Parasite screening", "duration_minutes": 15, "base_price": 4500},
    {"name": "X-rays (per view)", "category": "diagnostic", "description": "Radiograph imaging", "duration_minutes": 20, "base_price": 15000},
    {"name": "Ultrasound", "category": "diagnostic", "description": "Abdominal or cardiac ultrasound", "duration_minutes": 45, "base_price": 35000},

    # Emergency
    {"name": "Emergency Exam", "category": "emergency", "description": "After-hours emergency examination", "duration_minutes": 30, "base_price": 15000},
    {"name": "Hospitalization (per day)", "category": "emergency", "description": "24-hour inpatient care", "duration_minutes": 1440, "base_price": 75000},
    {"name": "IV Fluid Therapy", "category": "emergency", "description": "Intravenous fluid administration", "duration_minutes": 30, "base_price": 8500},

    # Wellness
    {"name": "Microchip Implant", "category": "wellness", "description": "Permanent identification microchip", "duration_minutes": 15, "base_price": 5500},
    {"name": "Nail Trim", "category": "wellness", "description": "Professional nail trimming", "duration_minutes": 15, "base_price": 2000},
    {"name": "Anal Gland Expression", "category": "wellness", "description": "Manual anal gland expression", "duration_minutes": 15, "base_price": 2500},
    {"name": "Ear Cleaning", "category": "wellness", "description": "Professional ear cleaning", "duration_minutes": 15, "base_price": 2500},
]


def create_medications(db: Session) -> List[models.Medication]:
    """Create medication inventory."""
    print("Creating medications...")
    medications_list = []

    for med_data in MEDICATIONS:
        medication = models.Medication(
            name=med_data["name"],
            description=med_data["description"],
            stock_quantity=med_data["stock_quantity"],
            unit=med_data["unit"]
        )
        db.add(medication)
        medications_list.append(medication)

    db.commit()
    print(f"Created {len(medications_list)} medications")
    return medications_list


def create_surgeries(
    db: Session,
    pets: List[models.Pet],
    staff: List[models.Staff],
    count: int = 50
) -> List[models.Surgery]:
    """Create surgery records."""
    print(f"Creating {count} surgeries...")
    surgeries_list = []

    # Filter staff to only surgeons/vets
    surgeons = [s for s in staff if s.role in ['Veterinarian', 'Orthopedic Surgeon', 'Dental Specialist', 'Oncologist']]
    if not surgeons:
        surgeons = staff  # fallback

    for i in range(count):
        pet = random.choice(pets)
        surgeon = random.choice(surgeons)
        surgery_type = random.choice(SURGERY_TYPES)

        # Random date in past 90 days or future 14 days
        days_offset = random.randint(-90, 14)
        start_time = datetime.now() + timedelta(days=days_offset, hours=random.randint(9, 14))
        end_time = start_time + timedelta(hours=random.randint(1, 3))

        # Determine status based on date
        if days_offset < -1:
            status = random.choice(['Completed', 'Completed', 'Completed', 'Cancelled'])
        elif days_offset < 0:
            status = 'Completed'
        elif days_offset == 0:
            status = random.choice(['In-Progress', 'Scheduled'])
        else:
            status = 'Scheduled'

        notes = f"Routine {surgery_type.lower()} procedure" if random.random() > 0.3 else None

        surgery = models.Surgery(
            pet_id=pet.id,
            staff_id=surgeon.id,
            surgery_type=surgery_type,
            notes=notes,
            start_time=start_time,
            end_time=end_time,
            status=status
        )
        db.add(surgery)
        surgeries_list.append(surgery)

    db.commit()
    print(f"Created {len(surgeries_list)} surgeries")
    return surgeries_list


def create_inventory_items(db: Session) -> List[models.InventoryItem]:
    """Create comprehensive inventory items for the animal hospital."""
    print("Creating inventory items...")
    inventory_list = []

    for item_data in INVENTORY_ITEMS:
        item = models.InventoryItem(
            name=item_data["name"],
            category=item_data["category"],
            subcategory=item_data.get("subcategory"),
            stock_quantity=item_data["stock_quantity"],
            min_stock_level=item_data.get("min_stock_level", 5),
            unit=item_data["unit"],
            unit_cost=item_data.get("unit_cost"),
            location=item_data.get("location"),
            last_restocked=datetime.now() - timedelta(days=random.randint(1, 30)),
            is_active=True
        )
        db.add(item)
        inventory_list.append(item)

    db.commit()
    print(f"Created {len(inventory_list)} inventory items")
    return inventory_list


def create_services(db: Session) -> List[models.Service]:
    """Create service catalog with pricing."""
    print("Creating services...")
    services_list = []

    for service_data in SERVICES:
        service = models.Service(
            name=service_data["name"],
            description=service_data.get("description"),
            category=service_data["category"],
            duration_minutes=service_data["duration_minutes"],
            base_price=service_data["base_price"],
            is_active=True
        )
        db.add(service)
        services_list.append(service)

    db.commit()
    print(f"Created {len(services_list)} services")
    return services_list


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

        # Create medications/inventory (legacy)
        medications = create_medications(db)

        # Create surgeries
        surgeries = create_surgeries(db, pets, staff, count=50)

        # Create comprehensive inventory items
        inventory_items = create_inventory_items(db)

        # Create service catalog with pricing
        services = create_services(db)

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
        print(f"  - Medications (legacy): {len(medications)}")
        print(f"  - Surgeries: {len(surgeries)}")
        print(f"  - Inventory Items: {len(inventory_items)}")
        print(f"  - Services: {len(services)}")
        print("=" * 60)

    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
