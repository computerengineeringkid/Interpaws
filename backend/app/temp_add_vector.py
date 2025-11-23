"""
One-time script to seed the database with a staff member's AI-ready skill vector.
This allows testing the complete AI suggestion pipeline.
"""

import asyncio

from sqlalchemy import update
from .database import SessionLocal
from .models import Staff
from .ai_services import get_embedding

# Constants
STAFF_ID = 1
SKILL_DESCRIPTION = "Specialist in small animal orthopedics, joint pain, and canine physical therapy."


def add_skill_vector():
    """Add skill vector to an existing staff member."""
    db = SessionLocal()
    
    try:
        print("Connecting to database...")
        
        # Generate embedding for the skill description
        print(f"Generating embedding for: {SKILL_DESCRIPTION}")
        skill_vector = asyncio.run(get_embedding(SKILL_DESCRIPTION))
        
        # Construct update statement
        stmt = (
            update(Staff)
            .where(Staff.id == STAFF_ID)
            .values(
                skills_description=SKILL_DESCRIPTION,
                skills_vector=skill_vector
            )
        )
        
        # Execute and commit
        db.execute(stmt)
        db.commit()
        
        print(f"✓ Successfully updated staff member {STAFF_ID} with skill vector!")
        print(f"  - Skills: {SKILL_DESCRIPTION}")
        print(f"  - Vector dimension: {len(skill_vector)}")
        
    finally:
        db.close()
        print("Database connection closed.")


if __name__ == "__main__":
    add_skill_vector()
