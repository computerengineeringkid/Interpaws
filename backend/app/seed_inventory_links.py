"""
Seed script to populate surgery inventory links with sample data.
Run this after creating medications to link them to surgery types.

Example usage:
    from app.seed_inventory_links import seed_inventory_links
    seed_inventory_links(db)
"""

from sqlalchemy.orm import Session
from . import models


def seed_inventory_links(db: Session):
    """
    Seed the surgery_inventory_links table with common surgery-medication associations.
    
    This is a helper function - you'll need medications already created in the database.
    Adjust medication_ids based on your actual medication records.
    """
    
    # Example inventory links (adjust medication_ids to match your database)
    # These are just examples - you'll need to create medications first
    
    sample_links = [
        # Spay surgery typically needs anesthesia, pain meds, and antibiotics
        {"surgery_type": "Spay", "medication_id": 1, "required_quantity": 2},  # e.g., Anesthesia
        {"surgery_type": "Spay", "medication_id": 2, "required_quantity": 3},  # e.g., Pain medication
        {"surgery_type": "Spay", "medication_id": 3, "required_quantity": 1},  # e.g., Antibiotics
        
        # Neuter surgery
        {"surgery_type": "Neuter", "medication_id": 1, "required_quantity": 1},  # e.g., Anesthesia
        {"surgery_type": "Neuter", "medication_id": 2, "required_quantity": 2},  # e.g., Pain medication
        
        # Orthopedic surgery
        {"surgery_type": "Orthopedic", "medication_id": 1, "required_quantity": 3},  # e.g., Anesthesia
        {"surgery_type": "Orthopedic", "medication_id": 2, "required_quantity": 5},  # e.g., Pain medication
        {"surgery_type": "Orthopedic", "medication_id": 3, "required_quantity": 2},  # e.g., Antibiotics
        {"surgery_type": "Orthopedic", "medication_id": 4, "required_quantity": 1},  # e.g., Anti-inflammatory
    ]
    
    # Check if links already exist to avoid duplicates
    existing_count = db.query(models.SurgeryInventoryLink).count()
    if existing_count > 0:
        print(f"Surgery inventory links already exist ({existing_count} records). Skipping seed.")
        return
    
    # Create the links
    for link_data in sample_links:
        # Verify medication exists before creating link
        med = db.query(models.Medication).filter(models.Medication.id == link_data["medication_id"]).first()
        if med:
            link = models.SurgeryInventoryLink(**link_data)
            db.add(link)
        else:
            print(f"Warning: Medication ID {link_data['medication_id']} not found, skipping link.")
    
    db.commit()
    print(f"Seeded {len(sample_links)} surgery inventory links.")


if __name__ == "__main__":
    print("This is a helper module. Import and call seed_inventory_links(db) from your main application.")
    print("Make sure you have medications created first, then adjust the medication_ids in this file.")
