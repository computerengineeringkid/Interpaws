from typing import List, Optional, Any, Dict
from datetime import datetime, date
from pydantic import BaseModel

# =======================
# Authentication Schemas
# =======================
class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str

class TokenData(BaseModel):
    email: Optional[str] = None

class TokenRefreshRequest(BaseModel):
    refresh_token: str

# =======================
# Base Models
# =======================
class ClientBase(BaseModel):
    name: str
    email: str
    clinic_id: Optional[int] = None

class ClientCreate(ClientBase):
    password: str

class Client(ClientBase):
    id: int
    is_active: bool = True
    class Config:
        orm_mode = True

class StaffBase(BaseModel):
    name: str
    email: str
    role: str
    skills_description: Optional[str] = None

class StaffCreate(StaffBase):
    password: str

class StaffUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    skills_description: Optional[str] = None

class Staff(StaffBase):
    id: int
    class Config:
        orm_mode = True

class PetBase(BaseModel):
    name: str
    species: str
    breed: Optional[str] = None
    date_of_birth: Optional[datetime] = None

class PetCreate(PetBase):
    pass

class Pet(PetBase):
    id: int
    client_id: int
    class Config:
        orm_mode = True

# =======================
# Booking Schemas (The Dashboard Fix)
# =======================

# Nested schemas for the Admin Dashboard
class ClientNested(BaseModel):
    id: int
    name: str
    email: str
    class Config:
        orm_mode = True

class PetNested(BaseModel):
    id: int
    name: str
    species: str
    breed: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    class Config:
        orm_mode = True

class StaffNested(BaseModel):
    id: int
    name: str
    role: str
    class Config:
        orm_mode = True

class BookingBase(BaseModel):
    start_time: datetime
    end_time: datetime
    pet_id: int
    staff_id: int
    complaint_reason: Optional[str] = None

class BookingCreate(BookingBase):
    pass

class BookingUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None
    staff_id: Optional[int] = None
    complaint_reason: Optional[str] = None

class Booking(BaseModel):
    id: int
    start_time: datetime
    end_time: datetime
    status: str
    complaint_reason: Optional[str] = None
    client_id: int
    pet_id: int
    staff_id: int
    
    # These nested fields allow the dashboard to show names!
    client: Optional[ClientNested] = None
    pet: Optional[PetNested] = None
    staff: Optional[StaffNested] = None

    class Config:
        orm_mode = True

class BookingByNameCreate(BaseModel):
    pet_name: str
    complaint_reason: Optional[str] = None
    service_type: Optional[str] = None
    preferred_time: datetime

class SuggestedSlot(BaseModel):
    start_time: datetime
    end_time: datetime
    staff_id: int
    staff_name: str
    preference_match: float = 0.0
    reason: str = ""

class ClientRescheduleRequest(BaseModel):
    start_time: datetime
    end_time: datetime
    staff_id: Optional[int] = None

# =======================
# AI & Risk Schemas
# =======================
class RiskAssessment(BaseModel):
    risk_score: float
    risk_level: str
    reasoning: str

class SuggestionRequest(BaseModel):
    complaint_text: str

class SuggestedStaff(BaseModel):
    id: int
    name: str
    role: str

class SuggestionResponse(BaseModel):
    generative_recommendation: str
    suggested_staff: List[SuggestedStaff]

class ChatRequest(BaseModel):
    message: str

class SmartChatRequest(BaseModel):
    prompt: str
    complaint_text: str = ""
    session_id: Optional[str] = None
    conversation_history: Optional[List[Dict[str, str]]] = None
    client_email: Optional[str] = None
    pet_name: Optional[str] = None
    owner_name: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    slots: Optional[List[SuggestedSlot]] = None
    service_type: Optional[str] = None
    ui_action: Optional[str] = None
    suggested_date: Optional[datetime] = None

class AIFeedbackLogResponse(BaseModel):
    id: int
    booking_id: int
    staff_id: int
    message: str

# =======================
# Surgery & Medical Schemas
# =======================
class SurgeryBase(BaseModel):
    surgery_type: str
    start_time: datetime
    end_time: datetime
    pet_id: int
    staff_id: int
    notes: Optional[str] = None
    status: Optional[str] = "Scheduled"

class SurgeryCreate(SurgeryBase):
    pass

class SurgeryUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None

class Surgery(SurgeryBase):
    id: int
    class Config:
        orm_mode = True

class SurgerySmartNotesRequest(BaseModel):
    raw_transcript: str

class SurgerySmartNotesResponse(BaseModel):
    surgery_id: int
    notes: str

class MedicationBase(BaseModel):
    name: str
    stock_quantity: int
    unit: str

class MedicationCreate(MedicationBase):
    pass

class MedicationUpdate(BaseModel):
    stock_quantity: Optional[int] = None

class Medication(MedicationBase):
    id: int
    class Config:
        orm_mode = True

class InventoryCheckItem(BaseModel):
    medication_id: int
    medication_name: str
    required_quantity: int
    stock_quantity: int
    status: str

class InventoryCheckResponse(BaseModel):
    items: List[InventoryCheckItem]

class InventoryForecastItem(BaseModel):
    medication_name: str
    current_stock: int
    daily_usage: float
    days_remaining: float

# =======================
# Preferences Schemas
# =======================
class PreferencesBase(BaseModel):
    details: str

class PreferencesCreate(PreferencesBase):
    pass

class Preferences(PreferencesBase):
    id: int
    client_id: int
    class Config:
        orm_mode = True

class CancellationSuggestion(BaseModel):
    client_name: str
    client_email: str
    current_booking_id: int
    current_booking_time: datetime
    match_score: float
    reason: str

class CancellationSuggestionResponse(BaseModel):
    cancelled_slot_time: datetime
    suggestions: List[CancellationSuggestion]

# =======================
# Staff AI Agent Schemas
# =======================
class StaffChatRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None

class StaffChatResponse(BaseModel):
    response: str
    data: Optional[Dict[str, Any]] = None
    intent: Optional[str] = None
    suggestions: Optional[List[str]] = None

# =======================
# Comprehensive Inventory Schemas
# =======================
class InventoryItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: str  # medications, equipment, supplies, surgical, diagnostic, office
    subcategory: Optional[str] = None
    stock_quantity: int = 0
    min_stock_level: int = 5
    unit: str
    unit_cost: Optional[int] = None  # Cost in cents
    location: Optional[str] = None
    supplier: Optional[str] = None
    sku: Optional[str] = None
    expiration_date: Optional[datetime] = None

class InventoryItemCreate(InventoryItemBase):
    pass

class InventoryItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    stock_quantity: Optional[int] = None
    min_stock_level: Optional[int] = None
    unit: Optional[str] = None
    unit_cost: Optional[int] = None
    location: Optional[str] = None
    supplier: Optional[str] = None
    sku: Optional[str] = None
    expiration_date: Optional[datetime] = None
    is_active: Optional[bool] = None

class InventoryItem(InventoryItemBase):
    id: int
    last_restocked: Optional[datetime] = None
    is_active: bool = True
    class Config:
        orm_mode = True

class InventoryStockAdjustment(BaseModel):
    quantity_change: int  # Positive to add, negative to subtract
    reason: Optional[str] = None

class InventoryCategoryStats(BaseModel):
    category: str
    total_items: int
    low_stock_count: int
    out_of_stock_count: int
    total_value: int  # In cents

class InventorySummary(BaseModel):
    total_items: int
    total_value: int  # In cents
    low_stock_items: int
    out_of_stock_items: int
    expiring_soon: int  # Within 30 days
    category_breakdown: List[InventoryCategoryStats]

# =======================
# Client Analytics Schemas
# =======================
class ClientAnalyticsBase(BaseModel):
    total_appointments: int = 0
    completed_appointments: int = 0
    cancelled_appointments: int = 0
    no_show_count: int = 0
    last_visit_date: Optional[datetime] = None
    first_visit_date: Optional[datetime] = None
    total_spent: int = 0
    preferred_staff_id: Optional[int] = None
    average_booking_lead_time: Optional[int] = None

class ClientAnalytics(ClientAnalyticsBase):
    id: int
    client_id: int

    # Computed fields
    no_show_rate: Optional[float] = None
    cancellation_rate: Optional[float] = None
    completion_rate: Optional[float] = None
    risk_level: Optional[str] = None  # low, medium, high

    class Config:
        orm_mode = True

class ClientWithAnalytics(BaseModel):
    id: int
    name: str
    email: str
    analytics: Optional[ClientAnalytics] = None
    pets_count: int = 0

    class Config:
        orm_mode = True

class NoShowRiskReport(BaseModel):
    high_risk_clients: List[ClientWithAnalytics]
    medium_risk_clients: List[ClientWithAnalytics]
    total_high_risk: int
    total_medium_risk: int
    overall_no_show_rate: float

class ClientEngagementStats(BaseModel):
    active_clients: int  # Visited in last 90 days
    inactive_clients: int  # No visit in 90+ days
    new_clients_this_month: int
    returning_clients_this_month: int
    average_visits_per_client: float
    top_clients: List[ClientWithAnalytics]  # By visit count

# =======================
# Service & Pricing Schemas
# =======================
class ServiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: str  # checkup, vaccination, surgery, dental, grooming, emergency
    duration_minutes: int = 30
    base_price: int  # Price in cents

class ServiceCreate(ServiceBase):
    pass

class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    duration_minutes: Optional[int] = None
    base_price: Optional[int] = None
    is_active: Optional[bool] = None

class Service(ServiceBase):
    id: int
    is_active: bool = True
    class Config:
        orm_mode = True

class RevenueStats(BaseModel):
    total_revenue: int  # In cents
    revenue_this_month: int
    revenue_last_month: int
    average_booking_value: int
    top_services: List[Dict[str, Any]]
    revenue_by_category: Dict[str, int]

# =======================
# Email Campaign Schemas
# =======================
class EmailCampaignBase(BaseModel):
    name: str
    subject: str
    body: str
    campaign_type: str  # reminder, promotion, follow_up, vaccination_due, checkup_reminder

class EmailCampaignCreate(EmailCampaignBase):
    scheduled_for: Optional[datetime] = None

class EmailCampaignUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    campaign_type: Optional[str] = None
    status: Optional[str] = None
    scheduled_for: Optional[datetime] = None

class EmailCampaign(EmailCampaignBase):
    id: int
    status: str = "draft"
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    scheduled_for: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    recipient_count: int = 0
    class Config:
        orm_mode = True

class EmailSendCreate(BaseModel):
    campaign_id: Optional[int] = None
    client_id: Optional[int] = None
    email_address: str

class EmailSend(BaseModel):
    id: int
    campaign_id: Optional[int] = None
    client_id: Optional[int] = None
    email_address: str
    status: str = "pending"
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    class Config:
        orm_mode = True

class EmailGenerateRequest(BaseModel):
    campaign_type: str  # reminder, promotion, follow_up, vaccination_due, checkup_reminder
    tone: Optional[str] = "friendly"  # friendly, professional, urgent
    context: Optional[str] = None  # Additional context for the AI
    client_name: Optional[str] = None
    pet_name: Optional[str] = None

class EmailGenerateResponse(BaseModel):
    subject: str
    body: str

class SendEmailRequest(BaseModel):
    to_email: str
    subject: str
    body: str
    campaign_id: Optional[int] = None
    client_id: Optional[int] = None

class SendEmailResponse(BaseModel):
    success: bool
    message: str
    email_send_id: Optional[int] = None