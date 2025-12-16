from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from .database import Base  # Import the Base from database.py

class Clinic(Base):
    __tablename__ = "clinics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

class Staff(Base):
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, index=True) # e.g., "Veterinarian", "Technician"
    skills_description = Column(Text, nullable=True)
    skills_vector = Column(Vector(384), nullable=True)


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    clinic_id = Column(Integer, ForeignKey("clinics.id"))


class Pet(Base):
    __tablename__ = "pets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    species = Column(String, index=True)
    breed = Column(String)
    date_of_birth = Column(DateTime, nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"))


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    start_time = Column(DateTime, index=True)
    end_time = Column(DateTime)
    status = Column(String, default='confirmed', index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    pet_id = Column(Integer, ForeignKey("pets.id"))
    staff_id = Column(Integer, ForeignKey("staff.id"))
    service_id = Column(Integer, ForeignKey("services.id"), nullable=True)
    price = Column(Integer, nullable=True)  # Price in cents for revenue tracking
    complaint_reason = Column(Text, nullable=True)
    complaint_vector = Column(Vector(384), nullable=True)

    # Relationships for eager loading
    client = relationship("Client", foreign_keys=[client_id])
    pet = relationship("Pet", foreign_keys=[pet_id])
    staff = relationship("Staff", foreign_keys=[staff_id])
    service = relationship("Service", foreign_keys=[service_id])


class Preferences(Base):
    __tablename__ = "preferences"

    id = Column(Integer, primary_key=True, index=True)
    details = Column(Text)
    client_id = Column(Integer, ForeignKey("clients.id"))
    details_vector = Column(Vector(384), nullable=True)


class AIFeedbackLog(Base):
    __tablename__ = "ai_feedback_logs"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"))
    staff_id = Column(Integer, ForeignKey("staff.id"))
    client_complaint_vector = Column(Vector(384), nullable=True)
    staff_skills_vector = Column(Vector(384), nullable=True)


class Surgery(Base):
    __tablename__ = "surgeries"

    id = Column(Integer, primary_key=True, index=True)
    pet_id = Column(Integer, ForeignKey("pets.id"))
    staff_id = Column(Integer, ForeignKey("staff.id"))  # Primary surgeon
    surgery_type = Column(String)  # e.g., "Spay", "Orthopedic"
    notes = Column(Text, nullable=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    status = Column(String, index=True)  # e.g., "Scheduled", "In-Progress", "Completed"


class Medication(Base):
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    stock_quantity = Column(Integer, default=0)
    unit = Column(String)  # e.g., "mg", "ml", "tablets"


class SurgeryInventoryLink(Base):
    __tablename__ = "surgery_inventory_links"

    id = Column(Integer, primary_key=True, index=True)
    surgery_type = Column(String, index=True)  # e.g., "Spay", "Orthopedic"
    medication_id = Column(Integer, ForeignKey("medications.id"))
    required_quantity = Column(Integer, default=1)


class InventoryItem(Base):
    """Comprehensive inventory for animal hospital - medications, equipment, supplies"""
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    category = Column(String, index=True)  # medications, equipment, supplies, surgical, diagnostic, office
    subcategory = Column(String, nullable=True)  # e.g., "antibiotics", "surgical tools", "bandages"
    stock_quantity = Column(Integer, default=0)
    min_stock_level = Column(Integer, default=5)  # Alert threshold
    unit = Column(String)  # e.g., "tablets", "units", "boxes", "pairs"
    unit_cost = Column(Integer, nullable=True)  # Cost in cents
    location = Column(String, nullable=True)  # e.g., "Storage Room A", "Surgery Suite"
    supplier = Column(String, nullable=True)
    sku = Column(String, nullable=True, index=True)  # Stock keeping unit
    expiration_date = Column(DateTime, nullable=True)
    last_restocked = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)


class ClientAnalytics(Base):
    """Track client behavior analytics for no-show risk, engagement, etc."""
    __tablename__ = "client_analytics"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), unique=True)
    total_appointments = Column(Integer, default=0)
    completed_appointments = Column(Integer, default=0)
    cancelled_appointments = Column(Integer, default=0)
    no_show_count = Column(Integer, default=0)
    last_visit_date = Column(DateTime, nullable=True)
    first_visit_date = Column(DateTime, nullable=True)
    total_spent = Column(Integer, default=0)  # In cents
    preferred_staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    average_booking_lead_time = Column(Integer, nullable=True)  # Days in advance they typically book

    # Relationships
    client = relationship("Client", foreign_keys=[client_id])


class Service(Base):
    """Services offered by the clinic with pricing"""
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    category = Column(String, index=True)  # checkup, vaccination, surgery, dental, grooming, emergency
    duration_minutes = Column(Integer, default=30)
    base_price = Column(Integer)  # Price in cents
    is_active = Column(Boolean, default=True)


class EmailCampaign(Base):
    """Email campaigns for client outreach"""
    __tablename__ = "email_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    subject = Column(String)
    body = Column(Text)
    campaign_type = Column(String)  # reminder, promotion, follow_up, vaccination_due, checkup_reminder
    status = Column(String, default='draft')  # draft, scheduled, sent
    created_by = Column(Integer, ForeignKey("staff.id"), nullable=True)
    created_at = Column(DateTime)
    scheduled_for = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    recipient_count = Column(Integer, default=0)

    # Relationships
    creator = relationship("Staff", foreign_keys=[created_by])


class EmailSend(Base):
    """Individual email sends for tracking"""
    __tablename__ = "email_sends"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("email_campaigns.id"), nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    email_address = Column(String)
    status = Column(String, default='pending')  # pending, sent, delivered, opened, clicked, bounced
    sent_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)

    # Relationships
    campaign = relationship("EmailCampaign", foreign_keys=[campaign_id])
    client = relationship("Client", foreign_keys=[client_id])
