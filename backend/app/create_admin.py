"""
Create an admin staff account for Interpaws

Usage:
    python -m app.create_admin
"""

from app.database import SessionLocal
from app import models
from app.auth import get_password_hash

def create_admin_user():
    """Create a default admin user."""
    db = SessionLocal()
    
    try:
        # Check if admin already exists
        existing_admin = db.query(models.Staff).filter(models.Staff.email == "admin@interpaws.com").first()
        
        if existing_admin:
            print("Admin user already exists!")
            print(f"Email: admin@interpaws.com")
            print(f"Name: {existing_admin.name}")
            print(f"Role: {existing_admin.role}")
            return
        
        # Create admin user
        admin = models.Staff(
            name="Admin User",
            email="admin@interpaws.com",
            hashed_password=get_password_hash("admin123"),
            role="Administrator",
            skills_description="System administrator with full access to all features"
        )
        
        db.add(admin)
        db.commit()
        
        print("=" * 60)
        print("ADMIN USER CREATED SUCCESSFULLY!")
        print("=" * 60)
        print(f"Email: admin@interpaws.com")
        print(f"Password: admin123")
        print(f"Role: Administrator")
        print("=" * 60)
        print("You can now login at: http://localhost:3000/admin/admin-login")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_admin_user()
