"""Staff-specific tools for the Staff AI Agent."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from collections import defaultdict

from sqlalchemy import Date, cast, func
from sqlalchemy.orm import Session

from app import models
from app.ai_services import get_embedding, get_ollama_recommendation, extract_json_payload
from app.booking_logic import check_availability
from app.service_catalog import get_service_duration_minutes, infer_service_type


class StaffAgentTools:
    """Tools for staff AI agent operations."""

    def __init__(self, db: Session, staff_member: models.Staff):
        self.db = db
        self.staff = staff_member

    # =========================================================================
    # SCHEDULE MANAGEMENT
    # =========================================================================

    async def get_my_schedule(self, date_str: str) -> Dict[str, Any]:
        """Get the logged-in staff member's schedule for a specific date."""
        try:
            target_date = self._parse_date(date_str)
            if not target_date:
                return {"status": "error", "message": f"Could not parse date: {date_str}"}

            bookings = (
                self.db.query(models.Booking)
                .filter(
                    models.Booking.staff_id == self.staff.id,
                    cast(models.Booking.start_time, Date) == target_date,
                    models.Booking.status == "confirmed"
                )
                .order_by(models.Booking.start_time)
                .all()
            )

            if not bookings:
                return {
                    "status": "success",
                    "date": target_date.strftime("%A, %B %d, %Y"),
                    "staff_name": self.staff.name,
                    "appointments": [],
                    "message": f"No appointments scheduled for {target_date.strftime('%A, %B %d')}."
                }

            appointments = []
            for b in bookings:
                pet = self.db.query(models.Pet).filter(models.Pet.id == b.pet_id).first()
                client = self.db.query(models.Client).filter(models.Client.id == b.client_id).first()
                appointments.append({
                    "booking_id": b.id,
                    "time": b.start_time.strftime("%I:%M %p"),
                    "end_time": b.end_time.strftime("%I:%M %p"),
                    "pet_name": pet.name if pet else "Unknown",
                    "pet_species": pet.species if pet else "Unknown",
                    "client_name": client.name if client else "Unknown",
                    "reason": b.complaint_reason or "General checkup"
                })

            return {
                "status": "success",
                "date": target_date.strftime("%A, %B %d, %Y"),
                "staff_name": self.staff.name,
                "appointments": appointments,
                "total_appointments": len(appointments)
            }

        except Exception as e:
            return {"status": "error", "message": f"Error fetching schedule: {str(e)}"}

    async def get_all_bookings(self, date_str: str) -> Dict[str, Any]:
        """Get all clinic bookings for a specific date."""
        try:
            target_date = self._parse_date(date_str)
            if not target_date:
                return {"status": "error", "message": f"Could not parse date: {date_str}"}

            bookings = (
                self.db.query(models.Booking)
                .filter(
                    cast(models.Booking.start_time, Date) == target_date,
                    models.Booking.status == "confirmed"
                )
                .order_by(models.Booking.start_time)
                .all()
            )

            if not bookings:
                return {
                    "status": "success",
                    "date": target_date.strftime("%A, %B %d, %Y"),
                    "appointments": [],
                    "message": f"No appointments scheduled for {target_date.strftime('%A, %B %d')}."
                }

            appointments = []
            for b in bookings:
                pet = self.db.query(models.Pet).filter(models.Pet.id == b.pet_id).first()
                client = self.db.query(models.Client).filter(models.Client.id == b.client_id).first()
                staff = self.db.query(models.Staff).filter(models.Staff.id == b.staff_id).first()
                appointments.append({
                    "booking_id": b.id,
                    "time": b.start_time.strftime("%I:%M %p"),
                    "end_time": b.end_time.strftime("%I:%M %p"),
                    "pet_name": pet.name if pet else "Unknown",
                    "pet_species": pet.species if pet else "Unknown",
                    "client_name": client.name if client else "Unknown",
                    "staff_name": staff.name if staff else "Unassigned",
                    "reason": b.complaint_reason or "General checkup"
                })

            return {
                "status": "success",
                "date": target_date.strftime("%A, %B %d, %Y"),
                "appointments": appointments,
                "total_appointments": len(appointments)
            }

        except Exception as e:
            return {"status": "error", "message": f"Error fetching bookings: {str(e)}"}

    async def get_staff_availability(self, staff_id: Optional[int], date_str: str) -> Dict[str, Any]:
        """Check availability for a staff member on a specific date."""
        try:
            target_date = self._parse_date(date_str)
            if not target_date:
                return {"status": "error", "message": f"Could not parse date: {date_str}"}

            # Use provided staff_id or default to current staff
            check_staff_id = staff_id or self.staff.id
            staff = self.db.query(models.Staff).filter(models.Staff.id == check_staff_id).first()
            if not staff:
                return {"status": "error", "message": "Staff member not found."}

            # Get existing bookings
            bookings = (
                self.db.query(models.Booking)
                .filter(
                    models.Booking.staff_id == check_staff_id,
                    cast(models.Booking.start_time, Date) == target_date,
                    models.Booking.status == "confirmed"
                )
                .all()
            )

            booked_hours = set()
            for b in bookings:
                hour = b.start_time.hour
                while hour < b.end_time.hour:
                    booked_hours.add(hour)
                    hour += 1

            # Available slots (9 AM - 5 PM)
            all_hours = list(range(9, 17))
            available_slots = [
                f"{h}:00 {'AM' if h < 12 else 'PM'}" if h <= 12 else f"{h-12}:00 PM"
                for h in all_hours if h not in booked_hours
            ]

            return {
                "status": "success",
                "staff_name": staff.name,
                "date": target_date.strftime("%A, %B %d, %Y"),
                "available_slots": available_slots,
                "booked_count": len(booked_hours),
                "available_count": len(available_slots)
            }

        except Exception as e:
            return {"status": "error", "message": f"Error checking availability: {str(e)}"}

    # =========================================================================
    # PATIENT/CLIENT LOOKUP
    # =========================================================================

    async def search_pets(
        self,
        pet_name: Optional[str] = None,
        owner_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search for pets by name and/or owner name."""
        try:
            query = self.db.query(models.Pet)

            if pet_name:
                query = query.filter(models.Pet.name.ilike(f"%{pet_name}%"))

            if owner_name:
                # Join with clients to filter by owner name
                query = query.join(models.Client).filter(
                    models.Client.name.ilike(f"%{owner_name}%")
                )

            pets = query.limit(10).all()

            if not pets:
                search_terms = []
                if pet_name:
                    search_terms.append(f"pet name '{pet_name}'")
                if owner_name:
                    search_terms.append(f"owner '{owner_name}'")
                return {
                    "status": "not_found",
                    "message": f"No pets found matching {' and '.join(search_terms)}."
                }

            results = []
            for pet in pets:
                client = self.db.query(models.Client).filter(
                    models.Client.id == pet.client_id
                ).first()

                # Calculate age
                age_str = "Unknown"
                if pet.date_of_birth:
                    today = datetime.now()
                    age_years = today.year - pet.date_of_birth.year
                    if today.month < pet.date_of_birth.month or (
                        today.month == pet.date_of_birth.month and
                        today.day < pet.date_of_birth.day
                    ):
                        age_years -= 1
                    age_str = f"{age_years} years old" if age_years > 0 else "Less than 1 year"

                results.append({
                    "pet_id": pet.id,
                    "name": pet.name,
                    "species": pet.species,
                    "breed": pet.breed or "Unknown",
                    "age": age_str,
                    "date_of_birth": pet.date_of_birth.strftime("%Y-%m-%d") if pet.date_of_birth else None,
                    "owner_name": client.name if client else "Unknown",
                    "owner_email": client.email if client else None
                })

            return {
                "status": "success",
                "pets": results,
                "total_found": len(results)
            }

        except Exception as e:
            return {"status": "error", "message": f"Error searching pets: {str(e)}"}

    async def get_pet_history(self, pet_id: int) -> Dict[str, Any]:
        """Get booking history for a specific pet."""
        try:
            pet = self.db.query(models.Pet).filter(models.Pet.id == pet_id).first()
            if not pet:
                return {"status": "error", "message": "Pet not found."}

            client = self.db.query(models.Client).filter(
                models.Client.id == pet.client_id
            ).first()

            # Get recent bookings
            bookings = (
                self.db.query(models.Booking)
                .filter(models.Booking.pet_id == pet_id)
                .order_by(models.Booking.start_time.desc())
                .limit(10)
                .all()
            )

            history = []
            for b in bookings:
                staff = self.db.query(models.Staff).filter(
                    models.Staff.id == b.staff_id
                ).first()
                history.append({
                    "date": b.start_time.strftime("%B %d, %Y"),
                    "time": b.start_time.strftime("%I:%M %p"),
                    "reason": b.complaint_reason or "General visit",
                    "staff": staff.name if staff else "Unknown",
                    "status": b.status
                })

            return {
                "status": "success",
                "pet": {
                    "name": pet.name,
                    "species": pet.species,
                    "breed": pet.breed,
                    "owner": client.name if client else "Unknown"
                },
                "visit_history": history,
                "total_visits": len(history)
            }

        except Exception as e:
            return {"status": "error", "message": f"Error fetching pet history: {str(e)}"}

    # =========================================================================
    # INVENTORY MANAGEMENT
    # =========================================================================

    async def check_medication_stock(self, medication_name: Optional[str] = None) -> Dict[str, Any]:
        """Check inventory stock levels (medications, equipment, supplies)."""
        try:
            if medication_name:
                # Search for specific item in InventoryItem table
                items = (
                    self.db.query(models.InventoryItem)
                    .filter(
                        models.InventoryItem.name.ilike(f"%{medication_name}%"),
                        models.InventoryItem.is_active == True
                    )
                    .all()
                )

                # Also check legacy Medication table
                medications = (
                    self.db.query(models.Medication)
                    .filter(models.Medication.name.ilike(f"%{medication_name}%"))
                    .all()
                )

                if not items and not medications:
                    return {
                        "status": "not_found",
                        "message": f"No inventory item found matching '{medication_name}'."
                    }

                results = []
                # Add InventoryItem results
                for item in items:
                    status = "Out of Stock" if item.stock_quantity == 0 else \
                             "Low Stock" if item.stock_quantity < item.min_stock_level else "In Stock"
                    results.append({
                        "name": item.name,
                        "category": item.category,
                        "stock_quantity": item.stock_quantity,
                        "min_stock_level": item.min_stock_level,
                        "unit": item.unit,
                        "location": item.location,
                        "status": status
                    })

                # Add legacy Medication results (if not already found in InventoryItem)
                item_names = [i.name.lower() for i in items]
                for med in medications:
                    if med.name.lower() not in item_names:
                        results.append({
                            "name": med.name,
                            "category": "medications",
                            "stock_quantity": med.stock_quantity,
                            "min_stock_level": 10,  # Default threshold for legacy
                            "unit": med.unit,
                            "status": "Out of Stock" if med.stock_quantity == 0 else
                                     "Low Stock" if med.stock_quantity < 10 else "In Stock"
                        })

                return {
                    "status": "success",
                    "items": results,
                    "total_found": len(results)
                }

            else:
                # Return summary of all inventory
                items = self.db.query(models.InventoryItem).filter(
                    models.InventoryItem.is_active == True
                ).all()

                out_of_stock = []
                low_stock = []
                in_stock = []

                for item in items:
                    item_info = {
                        "name": item.name,
                        "category": item.category,
                        "stock_quantity": item.stock_quantity,
                        "min_stock_level": item.min_stock_level,
                        "unit": item.unit,
                        "location": item.location
                    }
                    if item.stock_quantity == 0:
                        out_of_stock.append(item_info)
                    elif item.stock_quantity < item.min_stock_level:
                        low_stock.append(item_info)
                    else:
                        in_stock.append(item_info)

                # Also include legacy medications
                medications = self.db.query(models.Medication).all()
                for med in medications:
                    med_info = {
                        "name": med.name,
                        "category": "medications",
                        "stock_quantity": med.stock_quantity,
                        "min_stock_level": 10,
                        "unit": med.unit
                    }
                    if med.stock_quantity == 0:
                        out_of_stock.append(med_info)
                    elif med.stock_quantity < 10:
                        low_stock.append(med_info)
                    else:
                        in_stock.append(med_info)

                total_items = len(items) + len(medications)

                return {
                    "status": "success",
                    "summary": {
                        "total_items": total_items,
                        "out_of_stock_count": len(out_of_stock),
                        "low_stock_count": len(low_stock),
                        "in_stock_count": len(in_stock)
                    },
                    "out_of_stock": out_of_stock,
                    "low_stock": low_stock
                }

        except Exception as e:
            return {"status": "error", "message": f"Error checking inventory: {str(e)}"}

    async def get_low_stock_alerts(self) -> Dict[str, Any]:
        """Get all inventory items that need reordering."""
        try:
            alerts = []

            # Check InventoryItem table (uses min_stock_level for smart alerts)
            items = self.db.query(models.InventoryItem).filter(
                models.InventoryItem.is_active == True
            ).all()

            for item in items:
                if item.stock_quantity <= item.min_stock_level:
                    urgency = "CRITICAL" if item.stock_quantity == 0 else "LOW"
                    alerts.append({
                        "name": item.name,
                        "category": item.category,
                        "current_stock": item.stock_quantity,
                        "min_stock_level": item.min_stock_level,
                        "unit": item.unit,
                        "location": item.location,
                        "supplier": item.supplier,
                        "urgency": urgency
                    })

            # Also check legacy Medication table (uses hardcoded threshold of 10)
            medications = (
                self.db.query(models.Medication)
                .filter(models.Medication.stock_quantity < 10)
                .order_by(models.Medication.stock_quantity)
                .all()
            )

            for med in medications:
                alerts.append({
                    "name": med.name,
                    "category": "medications",
                    "current_stock": med.stock_quantity,
                    "min_stock_level": 10,
                    "unit": med.unit,
                    "urgency": "CRITICAL" if med.stock_quantity == 0 else "LOW"
                })

            # Sort by urgency (CRITICAL first) then by stock quantity
            alerts.sort(key=lambda x: (0 if x["urgency"] == "CRITICAL" else 1, x["current_stock"]))

            return {
                "status": "success",
                "alerts": alerts,
                "total_alerts": len(alerts),
                "critical_count": sum(1 for a in alerts if a["urgency"] == "CRITICAL"),
                "message": f"Found {len(alerts)} items needing attention." if alerts else "All inventory levels are adequate."
            }

        except Exception as e:
            return {"status": "error", "message": f"Error fetching alerts: {str(e)}"}

    # =========================================================================
    # TRIAGE ASSISTANCE
    # =========================================================================

    async def assess_symptom_urgency(
        self,
        symptoms: str,
        species: Optional[str] = None
    ) -> Dict[str, Any]:
        """Use AI to assess the urgency of reported symptoms."""
        try:
            species_context = f"Species: {species}" if species else "Species: Unknown"

            prompt = f"""You are an experienced veterinary triage nurse. Assess the urgency of these symptoms.

{species_context}
Symptoms: {symptoms}

Respond in JSON format:
{{
    "urgency_level": "EMERGENCY" | "URGENT" | "SOON" | "ROUTINE",
    "urgency_score": 0.0-1.0,
    "recommended_action": "brief action recommendation",
    "reasoning": "brief clinical reasoning",
    "red_flags": ["list of concerning symptoms if any"]
}}

Guidelines:
- EMERGENCY (0.8-1.0): Life-threatening, needs immediate attention (bleeding, difficulty breathing, seizures, toxin ingestion, inability to urinate)
- URGENT (0.6-0.8): Serious but not immediately life-threatening (persistent vomiting, limping, eye issues)
- SOON (0.4-0.6): Should be seen within 24-48 hours (mild symptoms, minor injuries)
- ROUTINE (0.0-0.4): Can wait for regular appointment (checkups, vaccinations)
"""

            response = await get_ollama_recommendation(prompt, json_mode=True)
            result = extract_json_payload(response)

            if result:
                return {
                    "status": "success",
                    "symptoms": symptoms,
                    "species": species,
                    **result
                }
            else:
                # Fallback if JSON parsing fails
                return {
                    "status": "success",
                    "symptoms": symptoms,
                    "species": species,
                    "urgency_level": "UNKNOWN",
                    "recommended_action": "Unable to assess. Please evaluate manually.",
                    "raw_response": response
                }

        except Exception as e:
            return {"status": "error", "message": f"Error assessing symptoms: {str(e)}"}

    # =========================================================================
    # MEDICATION DOSING REFERENCE
    # =========================================================================

    # Standard veterinary medication dosing reference (for clinical staff use)
    # Dosages are in mg/kg with typical frequency
    MEDICATION_DOSING_REFERENCE = {
        "cephalexin": {
            "class": "Antibiotic (Cephalosporin)",
            "dog": {"dose_mg_per_kg": (10, 30), "frequency": "Every 8-12 hours", "notes": "Common for skin/soft tissue infections"},
            "cat": {"dose_mg_per_kg": (15, 30), "frequency": "Every 8-12 hours", "notes": "Use cautiously in cats with kidney issues"},
            "common_forms": ["250mg capsules", "500mg capsules", "oral suspension"],
        },
        "amoxicillin": {
            "class": "Antibiotic (Penicillin)",
            "dog": {"dose_mg_per_kg": (10, 25), "frequency": "Every 8-12 hours", "notes": "Broad spectrum, good for respiratory/UTI"},
            "cat": {"dose_mg_per_kg": (10, 25), "frequency": "Every 12 hours", "notes": "Well tolerated in cats"},
            "common_forms": ["250mg capsules", "500mg capsules", "oral suspension"],
        },
        "amoxicillin-clavulanate": {
            "class": "Antibiotic (Penicillin + Beta-lactamase inhibitor)",
            "dog": {"dose_mg_per_kg": (12.5, 25), "frequency": "Every 12 hours", "notes": "Enhanced spectrum, good for resistant infections"},
            "cat": {"dose_mg_per_kg": (12.5, 25), "frequency": "Every 12 hours", "notes": "Give with food to reduce GI upset"},
            "common_forms": ["62.5mg tablets", "125mg tablets", "250mg tablets", "375mg tablets"],
        },
        "metronidazole": {
            "class": "Antibiotic/Antiprotozoal",
            "dog": {"dose_mg_per_kg": (10, 25), "frequency": "Every 12 hours", "notes": "GI infections, giardia. Max 65mg/kg/day"},
            "cat": {"dose_mg_per_kg": (10, 25), "frequency": "Every 12-24 hours", "notes": "Bitter taste - may need compounding"},
            "common_forms": ["250mg tablets", "500mg tablets"],
        },
        "meloxicam": {
            "class": "NSAID (Pain/Inflammation)",
            "dog": {"dose_mg_per_kg": (0.1, 0.2), "frequency": "Once daily", "notes": "Loading dose 0.2, maintenance 0.1. Give with food"},
            "cat": {"dose_mg_per_kg": (0.05, 0.1), "frequency": "Once daily (short term only)", "notes": "CAUTION: Cats are sensitive to NSAIDs. Short-term use only"},
            "common_forms": ["1.5mg/ml oral suspension", "7.5mg tablets"],
        },
        "carprofen": {
            "class": "NSAID (Pain/Inflammation)",
            "dog": {"dose_mg_per_kg": (2, 4), "frequency": "Once daily or divided BID", "notes": "Can give 4mg/kg once or 2mg/kg twice daily"},
            "cat": {"dose_mg_per_kg": (0, 0), "frequency": "Not recommended", "notes": "NOT approved for cats"},
            "common_forms": ["25mg tablets", "75mg tablets", "100mg tablets"],
        },
        "gabapentin": {
            "class": "Analgesic/Anticonvulsant",
            "dog": {"dose_mg_per_kg": (5, 10), "frequency": "Every 8-12 hours", "notes": "Neuropathic pain, seizures. May cause sedation"},
            "cat": {"dose_mg_per_kg": (5, 10), "frequency": "Every 8-12 hours", "notes": "Good for anxiety/pain. Avoid products with xylitol"},
            "common_forms": ["100mg capsules", "300mg capsules", "oral solution"],
        },
        "tramadol": {
            "class": "Opioid Analgesic",
            "dog": {"dose_mg_per_kg": (2, 5), "frequency": "Every 8-12 hours", "notes": "Moderate pain. Watch for sedation/GI upset"},
            "cat": {"dose_mg_per_kg": (1, 2), "frequency": "Every 12 hours", "notes": "Use lower doses in cats"},
            "common_forms": ["50mg tablets"],
        },
        "prednisone": {
            "class": "Corticosteroid",
            "dog": {"dose_mg_per_kg": (0.5, 2), "frequency": "Once daily initially, then taper", "notes": "Anti-inflammatory: 0.5-1mg/kg. Immunosuppressive: 2mg/kg"},
            "cat": {"dose_mg_per_kg": (1, 2), "frequency": "Once daily initially, then taper", "notes": "Cats may need higher doses. Prednisolone preferred"},
            "common_forms": ["5mg tablets", "10mg tablets", "20mg tablets"],
        },
        "diphenhydramine": {
            "class": "Antihistamine",
            "dog": {"dose_mg_per_kg": (2, 4), "frequency": "Every 8-12 hours", "notes": "Allergies, mild sedation, motion sickness"},
            "cat": {"dose_mg_per_kg": (1, 2), "frequency": "Every 8-12 hours", "notes": "Can be sedating"},
            "common_forms": ["25mg tablets", "25mg capsules"],
        },
        "famotidine": {
            "class": "H2 Blocker (Antacid)",
            "dog": {"dose_mg_per_kg": (0.5, 1), "frequency": "Every 12-24 hours", "notes": "GI ulcers, acid reflux. Give before meals"},
            "cat": {"dose_mg_per_kg": (0.5, 1), "frequency": "Every 12-24 hours", "notes": "Well tolerated"},
            "common_forms": ["10mg tablets", "20mg tablets"],
        },
        "omeprazole": {
            "class": "Proton Pump Inhibitor",
            "dog": {"dose_mg_per_kg": (0.5, 1), "frequency": "Once daily", "notes": "Give 30 min before meals. More potent than famotidine"},
            "cat": {"dose_mg_per_kg": (0.5, 1), "frequency": "Once daily", "notes": "Give before meals"},
            "common_forms": ["10mg capsules", "20mg capsules"],
        },
        "cerenia": {
            "class": "Antiemetic (maropitant)",
            "dog": {"dose_mg_per_kg": (2, 2), "frequency": "Once daily", "notes": "Prevents vomiting. Can use for motion sickness"},
            "cat": {"dose_mg_per_kg": (1, 1), "frequency": "Once daily", "notes": "Injectable available for acute cases"},
            "common_forms": ["16mg tablets", "24mg tablets", "60mg tablets", "injectable"],
        },
        "apoquel": {
            "class": "Janus Kinase Inhibitor (Itch Relief)",
            "dog": {"dose_mg_per_kg": (0.4, 0.6), "frequency": "Every 12 hours x 14 days, then once daily", "notes": "For allergic dermatitis/itch. Not for dogs <12 months"},
            "cat": {"dose_mg_per_kg": (0, 0), "frequency": "Not approved", "notes": "NOT approved for cats"},
            "common_forms": ["3.6mg tablets", "5.4mg tablets", "16mg tablets"],
        },
        "trazodone": {
            "class": "Anxiolytic/Sedative",
            "dog": {"dose_mg_per_kg": (2, 5), "frequency": "Every 8-12 hours as needed", "notes": "Anxiety, fear, post-op sedation. May combine with gabapentin"},
            "cat": {"dose_mg_per_kg": (2, 5), "frequency": "Every 8-12 hours as needed", "notes": "Good pre-visit anxiolytic"},
            "common_forms": ["50mg tablets", "100mg tablets"],
        },
    }

    async def get_medication_dosing(
        self,
        medication_name: str,
        weight_lbs: Optional[float] = None,
        species: str = "dog"
    ) -> Dict[str, Any]:
        """Get medication dosing guidelines from clinical reference."""
        try:
            # Normalize inputs
            med_name = medication_name.lower().strip()
            species = species.lower().strip() if species else "dog"

            # Search for medication (allow partial matches)
            matched_med = None
            matched_key = None
            for key, data in self.MEDICATION_DOSING_REFERENCE.items():
                if key in med_name or med_name in key:
                    matched_med = data
                    matched_key = key
                    break

            if not matched_med:
                # List available medications
                available = list(self.MEDICATION_DOSING_REFERENCE.keys())
                return {
                    "status": "not_found",
                    "message": f"'{medication_name}' not found in dosing reference.",
                    "available_medications": available,
                    "suggestion": "Try searching for one of the listed medications."
                }

            # Get species-specific dosing
            if species not in matched_med:
                species = "dog"  # Default to dog if species not found

            species_data = matched_med.get(species, matched_med.get("dog"))

            # Build response
            result = {
                "status": "success",
                "medication": matched_key.title(),
                "class": matched_med["class"],
                "species": species,
                "dose_range_mg_per_kg": species_data["dose_mg_per_kg"],
                "frequency": species_data["frequency"],
                "clinical_notes": species_data["notes"],
                "common_forms": matched_med.get("common_forms", []),
            }

            # Calculate actual dose if weight provided
            if weight_lbs and species_data["dose_mg_per_kg"][0] > 0:
                weight_kg = weight_lbs / 2.205
                low_dose = species_data["dose_mg_per_kg"][0]
                high_dose = species_data["dose_mg_per_kg"][1]

                result["weight_kg"] = round(weight_kg, 2)
                result["calculated_dose"] = {
                    "low_mg": round(low_dose * weight_kg, 1),
                    "high_mg": round(high_dose * weight_kg, 1),
                    "range_description": f"{round(low_dose * weight_kg, 1)} - {round(high_dose * weight_kg, 1)} mg per dose"
                }

            result["disclaimer"] = "Reference dosing only. Always verify with veterinarian and adjust based on patient condition."

            return result

        except Exception as e:
            return {"status": "error", "message": f"Error looking up dosing: {str(e)}"}

    # =========================================================================
    # ANALYTICS
    # =========================================================================

    async def get_booking_analytics(self, period: str = "week") -> Dict[str, Any]:
        """Get booking statistics for a time period."""
        try:
            now = datetime.now()

            if period == "week":
                start_date = now - timedelta(days=7)
                period_label = "Last 7 days"
            elif period == "month":
                start_date = now - timedelta(days=30)
                period_label = "Last 30 days"
            elif period == "today":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                period_label = "Today"
            else:
                start_date = now - timedelta(days=7)
                period_label = "Last 7 days"

            # Total bookings
            total_bookings = (
                self.db.query(models.Booking)
                .filter(models.Booking.start_time >= start_date)
                .count()
            )

            # Confirmed vs cancelled
            confirmed = (
                self.db.query(models.Booking)
                .filter(
                    models.Booking.start_time >= start_date,
                    models.Booking.status == "confirmed"
                )
                .count()
            )

            cancelled = (
                self.db.query(models.Booking)
                .filter(
                    models.Booking.start_time >= start_date,
                    models.Booking.status == "cancelled"
                )
                .count()
            )

            # Bookings by day of week
            bookings_by_day = defaultdict(int)
            bookings = (
                self.db.query(models.Booking)
                .filter(
                    models.Booking.start_time >= start_date,
                    models.Booking.status == "confirmed"
                )
                .all()
            )

            for b in bookings:
                day_name = b.start_time.strftime("%A")
                bookings_by_day[day_name] += 1

            busiest_day = max(bookings_by_day, key=bookings_by_day.get) if bookings_by_day else None

            # Bookings by hour
            bookings_by_hour = defaultdict(int)
            for b in bookings:
                hour = b.start_time.hour
                bookings_by_hour[hour] += 1

            busiest_hour = max(bookings_by_hour, key=bookings_by_hour.get) if bookings_by_hour else None
            busiest_hour_str = f"{busiest_hour}:00" if busiest_hour else None

            return {
                "status": "success",
                "period": period_label,
                "total_bookings": total_bookings,
                "confirmed": confirmed,
                "cancelled": cancelled,
                "cancellation_rate": f"{(cancelled / total_bookings * 100):.1f}%" if total_bookings > 0 else "0%",
                "busiest_day": busiest_day,
                "busiest_hour": busiest_hour_str,
                "bookings_by_day": dict(bookings_by_day)
            }

        except Exception as e:
            return {"status": "error", "message": f"Error fetching analytics: {str(e)}"}

    # =========================================================================
    # ADMIN BOOKING
    # =========================================================================

    async def book_for_client(
        self,
        pet_name: str,
        owner_name: str,
        complaint: str,
        preferred_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """Book an appointment on behalf of a client."""
        try:
            # Find client
            client = (
                self.db.query(models.Client)
                .filter(models.Client.name.ilike(f"%{owner_name}%"))
                .first()
            )
            if not client:
                return {
                    "status": "error",
                    "message": f"Could not find client '{owner_name}'. Please verify the name."
                }

            # Find pet
            pet = (
                self.db.query(models.Pet)
                .filter(
                    models.Pet.client_id == client.id,
                    models.Pet.name.ilike(f"%{pet_name}%")
                )
                .first()
            )
            if not pet:
                return {
                    "status": "error",
                    "message": f"Could not find pet '{pet_name}' for client '{client.name}'."
                }

            # Infer service type and find appropriate staff
            service_type, rationale = infer_service_type(complaint)
            duration_minutes = get_service_duration_minutes(service_type)

            # Find best staff using embeddings
            embedding = await get_embedding(f"{service_type}: {complaint}")
            best_staff = (
                self.db.query(models.Staff)
                .order_by(models.Staff.skills_vector.l2_distance(embedding))
                .first()
            )

            if not best_staff:
                return {"status": "error", "message": "No available staff found."}

            if not preferred_time:
                # Generate available slots
                slots = self._generate_slots(best_staff, duration_minutes)
                return {
                    "status": "need_time",
                    "message": f"Found {pet.name} (owned by {client.name}). For '{complaint}', I recommend a {service_type} appointment with {best_staff.name}.",
                    "service_type": service_type,
                    "staff_name": best_staff.name,
                    "available_slots": [
                        {
                            "time": s["start_time"].strftime("%A, %B %d at %I:%M %p"),
                            "iso": s["start_time"].isoformat()
                        }
                        for s in slots[:5]
                    ]
                }

            # Parse preferred time and create booking
            start_time = self._parse_datetime(preferred_time)
            if not start_time:
                return {"status": "error", "message": f"Could not parse time: {preferred_time}"}

            end_time = start_time + timedelta(minutes=duration_minutes)

            # Check availability
            if not check_availability(self.db, best_staff.id, start_time, end_time):
                return {
                    "status": "error",
                    "message": f"The slot at {start_time.strftime('%I:%M %p on %B %d')} is not available."
                }

            # Create booking
            new_booking = models.Booking(
                start_time=start_time,
                end_time=end_time,
                client_id=client.id,
                pet_id=pet.id,
                staff_id=best_staff.id,
                complaint_reason=complaint,
                status="confirmed"
            )
            self.db.add(new_booking)
            self.db.commit()
            self.db.refresh(new_booking)

            return {
                "status": "success",
                "message": f"Appointment booked for {pet.name} with {best_staff.name} at {start_time.strftime('%I:%M %p on %A, %B %d')}.",
                "booking_id": new_booking.id,
                "service_type": service_type,
                "pet_name": pet.name,
                "client_name": client.name,
                "staff_name": best_staff.name,
                "time": start_time.isoformat()
            }

        except Exception as e:
            return {"status": "error", "message": f"Booking failed: {str(e)}"}

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse a date string into a date object."""
        date_str = date_str.lower().strip()
        today = datetime.now().date()

        if date_str in ["today", "now"]:
            return today
        elif date_str == "tomorrow":
            return today + timedelta(days=1)
        elif date_str == "yesterday":
            return today - timedelta(days=1)

        # Try various formats
        formats = ["%Y-%m-%d", "%m/%d/%Y", "%B %d", "%b %d", "%d %B", "%d %b"]
        for fmt in formats:
            try:
                parsed = datetime.strptime(date_str, fmt).date()
                # If no year specified, use current year
                if parsed.year == 1900:
                    parsed = parsed.replace(year=today.year)
                return parsed
            except ValueError:
                continue

        # Try to extract day of week
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for i, day in enumerate(days):
            if day in date_str:
                current_day = today.weekday()
                days_ahead = i - current_day
                if days_ahead <= 0:
                    days_ahead += 7
                return today + timedelta(days=days_ahead)

        return None

    def _parse_datetime(self, time_str: str) -> Optional[datetime]:
        """Parse a datetime string."""
        try:
            # Try ISO format first
            return datetime.fromisoformat(time_str)
        except ValueError:
            pass

        try:
            return datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            pass

        # Try natural language parsing
        # This is simplified - in production you might use dateparser library
        return None

    def _generate_slots(
        self,
        staff: models.Staff,
        duration_minutes: int,
        max_slots: int = 5
    ) -> List[Dict[str, Any]]:
        """Generate available time slots for a staff member."""
        now = datetime.now()
        slots = []
        end_window = now + timedelta(days=5)
        cursor = now

        while cursor <= end_window and len(slots) < max_slots:
            day_start = cursor.replace(hour=9, minute=0, second=0, microsecond=0)
            for hour in range(9, 17):
                if len(slots) >= max_slots:
                    break
                start_time = day_start.replace(hour=hour)
                if start_time <= now:
                    continue
                end_time = start_time + timedelta(minutes=duration_minutes)
                if end_time.hour > 17:
                    continue
                if check_availability(self.db, staff.id, start_time, end_time):
                    slots.append({
                        "start_time": start_time,
                        "end_time": end_time,
                        "staff_id": staff.id,
                        "staff_name": staff.name
                    })
            cursor += timedelta(days=1)

        return slots

    # =========================================================================
    # ADDITIONAL TOOLS FOR FULL ACCESS
    # =========================================================================

    async def get_visit_history(
        self,
        pet_name: str,
        owner_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get visit history for a pet by name."""
        try:
            # Find the pet first
            query = self.db.query(models.Pet).filter(
                models.Pet.name.ilike(f"%{pet_name}%")
            )
            if owner_name:
                query = query.join(models.Client).filter(
                    models.Client.name.ilike(f"%{owner_name}%")
                )
            pet = query.first()

            if not pet:
                return {"status": "not_found", "message": f"Pet '{pet_name}' not found."}

            # Get visit history
            return await self.get_pet_history(pet.id)

        except Exception as e:
            return {"status": "error", "message": f"Error fetching visit history: {str(e)}"}

    async def cancel_booking(
        self,
        booking_id: Optional[int] = None,
        pet_name: Optional[str] = None,
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cancel an existing booking."""
        try:
            booking = None

            if booking_id:
                booking = self.db.query(models.Booking).filter(
                    models.Booking.id == booking_id
                ).first()
            elif pet_name and date:
                target_date = self._parse_date(date)
                if not target_date:
                    return {"status": "error", "message": f"Could not parse date: {date}"}

                pet = self.db.query(models.Pet).filter(
                    models.Pet.name.ilike(f"%{pet_name}%")
                ).first()
                if not pet:
                    return {"status": "error", "message": f"Pet '{pet_name}' not found."}

                booking = (
                    self.db.query(models.Booking)
                    .filter(
                        models.Booking.pet_id == pet.id,
                        cast(models.Booking.start_time, Date) == target_date,
                        models.Booking.status == "confirmed"
                    )
                    .first()
                )

            if not booking:
                return {"status": "error", "message": "Booking not found."}

            # Get details before cancelling
            pet = self.db.query(models.Pet).filter(models.Pet.id == booking.pet_id).first()
            client = self.db.query(models.Client).filter(models.Client.id == booking.client_id).first()

            # Cancel the booking
            booking.status = "cancelled"
            self.db.commit()

            return {
                "status": "success",
                "message": f"Appointment cancelled for {pet.name if pet else 'Unknown'} on {booking.start_time.strftime('%B %d at %I:%M %p')}.",
                "booking_id": booking.id,
                "pet_name": pet.name if pet else "Unknown",
                "client_name": client.name if client else "Unknown",
                "original_time": booking.start_time.isoformat()
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": f"Error cancelling booking: {str(e)}"}

    async def update_inventory(
        self,
        medication_name: str,
        quantity_change: int,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update inventory stock levels."""
        try:
            # First try InventoryItem table
            item = (
                self.db.query(models.InventoryItem)
                .filter(
                    models.InventoryItem.name.ilike(f"%{medication_name}%"),
                    models.InventoryItem.is_active == True
                )
                .first()
            )

            if item:
                old_quantity = item.stock_quantity
                new_quantity = max(0, old_quantity + quantity_change)
                item.stock_quantity = new_quantity
                if quantity_change > 0:
                    item.last_restocked = datetime.now()
                self.db.commit()

                status_msg = ""
                if new_quantity <= item.min_stock_level and new_quantity > 0:
                    status_msg = f" (Warning: Stock is now below minimum level of {item.min_stock_level})"
                elif new_quantity == 0:
                    status_msg = " (Warning: Item is now OUT OF STOCK)"

                return {
                    "status": "success",
                    "message": f"{'Added' if quantity_change > 0 else 'Removed'} {abs(quantity_change)} {item.unit} of {item.name}.{status_msg}",
                    "item": item.name,
                    "category": item.category,
                    "previous_quantity": old_quantity,
                    "new_quantity": new_quantity,
                    "min_stock_level": item.min_stock_level,
                    "change": quantity_change,
                    "reason": reason or "No reason provided"
                }

            # Fall back to legacy Medication table
            medication = (
                self.db.query(models.Medication)
                .filter(models.Medication.name.ilike(f"%{medication_name}%"))
                .first()
            )

            if not medication:
                return {"status": "error", "message": f"Item '{medication_name}' not found in inventory."}

            old_quantity = medication.stock_quantity
            new_quantity = max(0, old_quantity + quantity_change)
            medication.stock_quantity = new_quantity
            self.db.commit()

            return {
                "status": "success",
                "message": f"{'Added' if quantity_change > 0 else 'Removed'} {abs(quantity_change)} {medication.unit} of {medication.name}.",
                "item": medication.name,
                "category": "medications",
                "previous_quantity": old_quantity,
                "new_quantity": new_quantity,
                "change": quantity_change,
                "reason": reason or "No reason provided"
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": f"Error updating inventory: {str(e)}"}

    async def get_surgeries(
        self,
        date_str: str,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get surgeries for a specific date."""
        try:
            target_date = self._parse_date(date_str)
            if not target_date:
                return {"status": "error", "message": f"Could not parse date: {date_str}"}

            query = self.db.query(models.Surgery).filter(
                cast(models.Surgery.start_time, Date) == target_date
            )

            if status and status.lower() != "all":
                query = query.filter(models.Surgery.status.ilike(f"%{status}%"))

            surgeries = query.order_by(models.Surgery.start_time).all()

            if not surgeries:
                return {
                    "status": "success",
                    "date": target_date.strftime("%A, %B %d, %Y"),
                    "surgeries": [],
                    "message": f"No surgeries scheduled for {target_date.strftime('%A, %B %d')}."
                }

            results = []
            for s in surgeries:
                pet = self.db.query(models.Pet).filter(models.Pet.id == s.pet_id).first()
                surgeon = self.db.query(models.Staff).filter(models.Staff.id == s.staff_id).first()
                client = None
                if pet:
                    client = self.db.query(models.Client).filter(models.Client.id == pet.client_id).first()

                results.append({
                    "surgery_id": s.id,
                    "surgery_type": s.surgery_type,
                    "time": s.start_time.strftime("%I:%M %p"),
                    "end_time": s.end_time.strftime("%I:%M %p"),
                    "status": s.status,
                    "pet_name": pet.name if pet else "Unknown",
                    "pet_species": pet.species if pet else "Unknown",
                    "client_name": client.name if client else "Unknown",
                    "surgeon": surgeon.name if surgeon else "Unassigned",
                    "notes": s.notes
                })

            return {
                "status": "success",
                "date": target_date.strftime("%A, %B %d, %Y"),
                "surgeries": results,
                "total_surgeries": len(results)
            }

        except Exception as e:
            return {"status": "error", "message": f"Error fetching surgeries: {str(e)}"}

    async def get_client_info(
        self,
        client_name: str,
        client_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get detailed client information including their pets."""
        try:
            query = self.db.query(models.Client)

            if client_email:
                query = query.filter(models.Client.email.ilike(f"%{client_email}%"))
            else:
                query = query.filter(models.Client.name.ilike(f"%{client_name}%"))

            clients = query.limit(5).all()

            if not clients:
                return {"status": "not_found", "message": f"No client found matching '{client_name}'."}

            results = []
            for client in clients:
                # Get client's pets
                pets = self.db.query(models.Pet).filter(models.Pet.client_id == client.id).all()

                # Get client's upcoming appointments
                upcoming = (
                    self.db.query(models.Booking)
                    .filter(
                        models.Booking.client_id == client.id,
                        models.Booking.start_time >= datetime.now(),
                        models.Booking.status == "confirmed"
                    )
                    .order_by(models.Booking.start_time)
                    .limit(5)
                    .all()
                )

                # Get client preferences
                prefs = self.db.query(models.Preferences).filter(
                    models.Preferences.client_id == client.id
                ).first()

                pet_list = []
                for pet in pets:
                    age_str = "Unknown"
                    if pet.date_of_birth:
                        today = datetime.now()
                        age_years = today.year - pet.date_of_birth.year
                        age_str = f"{age_years} years old"
                    pet_list.append({
                        "id": pet.id,
                        "name": pet.name,
                        "species": pet.species,
                        "breed": pet.breed or "Unknown",
                        "age": age_str
                    })

                appointment_list = []
                for appt in upcoming:
                    pet = self.db.query(models.Pet).filter(models.Pet.id == appt.pet_id).first()
                    appointment_list.append({
                        "date": appt.start_time.strftime("%B %d, %Y"),
                        "time": appt.start_time.strftime("%I:%M %p"),
                        "pet": pet.name if pet else "Unknown",
                        "reason": appt.complaint_reason or "General visit"
                    })

                results.append({
                    "client_id": client.id,
                    "name": client.name,
                    "email": client.email,
                    "pets": pet_list,
                    "total_pets": len(pet_list),
                    "upcoming_appointments": appointment_list,
                    "preferences": prefs.details if prefs else None
                })

            return {
                "status": "success",
                "clients": results,
                "total_found": len(results)
            }

        except Exception as e:
            return {"status": "error", "message": f"Error fetching client info: {str(e)}"}

    async def get_staff_workload(self, date_str: str) -> Dict[str, Any]:
        """Get staff workload/appointments breakdown for a specific date."""
        try:
            target_date = self._parse_date(date_str)
            if not target_date:
                return {"status": "error", "message": f"Could not parse date: {date_str}"}

            # Get all bookings for this date
            bookings = (
                self.db.query(models.Booking)
                .filter(
                    cast(models.Booking.start_time, Date) == target_date,
                    models.Booking.status == "confirmed"
                )
                .all()
            )

            # Count bookings per staff
            staff_counts = defaultdict(int)
            staff_bookings = defaultdict(list)

            for b in bookings:
                staff = self.db.query(models.Staff).filter(models.Staff.id == b.staff_id).first()
                if staff:
                    staff_counts[staff.id] += 1
                    pet = self.db.query(models.Pet).filter(models.Pet.id == b.pet_id).first()
                    staff_bookings[staff.id].append({
                        "time": b.start_time.strftime("%I:%M %p"),
                        "pet": pet.name if pet else "Unknown",
                        "reason": b.complaint_reason or "General visit"
                    })

            # Build results sorted by count (busiest first)
            results = []
            all_staff = self.db.query(models.Staff).all()

            for staff in all_staff:
                count = staff_counts.get(staff.id, 0)
                results.append({
                    "staff_id": staff.id,
                    "name": staff.name,
                    "role": staff.role,
                    "appointment_count": count,
                    "appointments": staff_bookings.get(staff.id, [])
                })

            # Sort by appointment count (busiest first)
            results.sort(key=lambda x: x["appointment_count"], reverse=True)

            busiest = results[0] if results else None

            return {
                "status": "success",
                "date": target_date.strftime("%A, %B %d, %Y"),
                "total_appointments": len(bookings),
                "busiest_staff": {
                    "name": busiest["name"],
                    "role": busiest["role"],
                    "appointments": busiest["appointment_count"]
                } if busiest and busiest["appointment_count"] > 0 else None,
                "staff_workload": results
            }

        except Exception as e:
            return {"status": "error", "message": f"Error fetching staff workload: {str(e)}"}

    async def get_all_staff(self) -> Dict[str, Any]:
        """Get list of all staff members."""
        try:
            staff = self.db.query(models.Staff).all()

            results = []
            for s in staff:
                # Count today's appointments
                today = datetime.now().date()
                today_count = (
                    self.db.query(models.Booking)
                    .filter(
                        models.Booking.staff_id == s.id,
                        cast(models.Booking.start_time, Date) == today,
                        models.Booking.status == "confirmed"
                    )
                    .count()
                )

                results.append({
                    "id": s.id,
                    "name": s.name,
                    "email": s.email,
                    "role": s.role,
                    "skills": s.skills_description,
                    "appointments_today": today_count
                })

            return {
                "status": "success",
                "staff": results,
                "total_staff": len(results)
            }

        except Exception as e:
            return {"status": "error", "message": f"Error fetching staff: {str(e)}"}

    async def reschedule_booking(
        self,
        booking_id: int,
        new_date: str,
        new_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """Reschedule an existing booking to a new date/time."""
        try:
            booking = self.db.query(models.Booking).filter(models.Booking.id == booking_id).first()
            if not booking:
                return {"status": "error", "message": f"Booking #{booking_id} not found."}

            # Parse new datetime
            new_datetime = self._parse_datetime(f"{new_date} {new_time}" if new_time else new_date)
            if not new_datetime:
                # Try parsing as date only
                new_date_parsed = self._parse_date(new_date)
                if new_date_parsed:
                    # Keep the same time
                    new_datetime = datetime.combine(new_date_parsed, booking.start_time.time())
                else:
                    return {"status": "error", "message": f"Could not parse date: {new_date}"}

            # Calculate duration
            duration = booking.end_time - booking.start_time
            new_end = new_datetime + duration

            # Check availability
            if not check_availability(self.db, booking.staff_id, new_datetime, new_end):
                return {
                    "status": "error",
                    "message": f"The slot at {new_datetime.strftime('%I:%M %p on %B %d')} is not available."
                }

            old_time = booking.start_time.strftime("%I:%M %p on %B %d")
            booking.start_time = new_datetime
            booking.end_time = new_end
            self.db.commit()

            pet = self.db.query(models.Pet).filter(models.Pet.id == booking.pet_id).first()

            return {
                "status": "success",
                "message": f"Appointment rescheduled from {old_time} to {new_datetime.strftime('%I:%M %p on %B %d')}.",
                "booking_id": booking.id,
                "pet_name": pet.name if pet else "Unknown",
                "old_time": old_time,
                "new_time": new_datetime.strftime("%I:%M %p on %A, %B %d")
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": f"Error rescheduling: {str(e)}"}

    # =========================================================================
    # FULL ACCESS TOOLS - CREATE, UPDATE, DELETE
    # =========================================================================

    async def register_client(
        self,
        name: str,
        email: str,
        password: str = "password123"
    ) -> Dict[str, Any]:
        """Register a new client in the system."""
        try:
            from app.auth import get_password_hash

            # Check if email already exists
            existing = self.db.query(models.Client).filter(
                models.Client.email == email
            ).first()
            if existing:
                return {"status": "error", "message": f"Client with email {email} already exists."}

            hashed_password = get_password_hash(password)
            client = models.Client(
                name=name,
                email=email,
                hashed_password=hashed_password
            )
            self.db.add(client)
            self.db.commit()
            self.db.refresh(client)

            return {
                "status": "success",
                "message": f"Client '{name}' registered successfully.",
                "client_id": client.id,
                "name": client.name,
                "email": client.email
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": f"Error registering client: {str(e)}"}

    async def add_pet(
        self,
        client_name: str,
        pet_name: str,
        species: str,
        breed: Optional[str] = None,
        date_of_birth: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a new pet for a client."""
        try:
            # Find client
            client = self.db.query(models.Client).filter(
                models.Client.name.ilike(f"%{client_name}%")
            ).first()
            if not client:
                return {"status": "error", "message": f"Client '{client_name}' not found."}

            # Parse date of birth if provided
            dob = None
            if date_of_birth:
                dob = self._parse_date(date_of_birth)

            pet = models.Pet(
                name=pet_name,
                species=species,
                breed=breed,
                date_of_birth=dob,
                client_id=client.id
            )
            self.db.add(pet)
            self.db.commit()
            self.db.refresh(pet)

            return {
                "status": "success",
                "message": f"Pet '{pet_name}' added for {client.name}.",
                "pet_id": pet.id,
                "pet_name": pet.name,
                "species": pet.species,
                "breed": pet.breed,
                "owner": client.name
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": f"Error adding pet: {str(e)}"}

    async def get_client_preferences(self, client_name: str) -> Dict[str, Any]:
        """Get a client's preferences and special notes."""
        try:
            client = self.db.query(models.Client).filter(
                models.Client.name.ilike(f"%{client_name}%")
            ).first()
            if not client:
                return {"status": "not_found", "message": f"Client '{client_name}' not found."}

            prefs = self.db.query(models.Preferences).filter(
                models.Preferences.client_id == client.id
            ).all()

            if not prefs:
                return {
                    "status": "success",
                    "client_name": client.name,
                    "preferences": [],
                    "message": "No preferences on file for this client."
                }

            return {
                "status": "success",
                "client_name": client.name,
                "preferences": [p.details for p in prefs]
            }

        except Exception as e:
            return {"status": "error", "message": f"Error fetching preferences: {str(e)}"}

    async def update_booking_notes(
        self,
        booking_id: int,
        notes: str
    ) -> Dict[str, Any]:
        """Update notes/reason for a booking."""
        try:
            booking = self.db.query(models.Booking).filter(
                models.Booking.id == booking_id
            ).first()
            if not booking:
                return {"status": "error", "message": f"Booking #{booking_id} not found."}

            old_notes = booking.complaint_reason
            booking.complaint_reason = notes
            self.db.commit()

            return {
                "status": "success",
                "message": "Booking notes updated.",
                "booking_id": booking.id,
                "old_notes": old_notes,
                "new_notes": notes
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": f"Error updating notes: {str(e)}"}

    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get overall clinic dashboard statistics."""
        try:
            today = datetime.now().date()
            week_ago = today - timedelta(days=7)

            # Counts
            total_clients = self.db.query(models.Client).count()
            total_pets = self.db.query(models.Pet).count()
            total_staff = self.db.query(models.Staff).count()

            # Today's appointments
            today_appointments = (
                self.db.query(models.Booking)
                .filter(
                    cast(models.Booking.start_time, Date) == today,
                    models.Booking.status == "confirmed"
                )
                .count()
            )

            # This week's appointments
            week_appointments = (
                self.db.query(models.Booking)
                .filter(
                    models.Booking.start_time >= datetime.combine(week_ago, datetime.min.time()),
                    models.Booking.status == "confirmed"
                )
                .count()
            )

            # Pending surgeries
            pending_surgeries = (
                self.db.query(models.Surgery)
                .filter(models.Surgery.status == "Scheduled")
                .count()
            )

            # Low stock items (from both InventoryItem and Medication tables)
            low_stock_items = 0

            # Count low stock from InventoryItem table
            items = self.db.query(models.InventoryItem).filter(
                models.InventoryItem.is_active == True
            ).all()
            for item in items:
                if item.stock_quantity <= item.min_stock_level:
                    low_stock_items += 1

            # Count low stock from legacy Medication table
            low_stock_meds = (
                self.db.query(models.Medication)
                .filter(models.Medication.stock_quantity < 10)
                .count()
            )
            low_stock_items += low_stock_meds

            # Species breakdown
            species_counts = {}
            pets = self.db.query(models.Pet).all()
            for pet in pets:
                species = pet.species or "Unknown"
                species_counts[species] = species_counts.get(species, 0) + 1

            return {
                "status": "success",
                "dashboard": {
                    "total_clients": total_clients,
                    "total_pets": total_pets,
                    "total_staff": total_staff,
                    "appointments_today": today_appointments,
                    "appointments_this_week": week_appointments,
                    "pending_surgeries": pending_surgeries,
                    "low_stock_alerts": low_stock_items,
                    "species_breakdown": species_counts
                }
            }

        except Exception as e:
            return {"status": "error", "message": f"Error fetching stats: {str(e)}"}

    async def schedule_surgery(
        self,
        pet_name: str,
        owner_name: str,
        surgery_type: str,
        date: str,
        surgeon_name: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Schedule a new surgery."""
        try:
            # Find pet
            query = self.db.query(models.Pet).filter(
                models.Pet.name.ilike(f"%{pet_name}%")
            )
            if owner_name:
                query = query.join(models.Client).filter(
                    models.Client.name.ilike(f"%{owner_name}%")
                )
            pet = query.first()
            if not pet:
                return {"status": "error", "message": f"Pet '{pet_name}' not found."}

            # Find surgeon
            if surgeon_name:
                surgeon = self.db.query(models.Staff).filter(
                    models.Staff.name.ilike(f"%{surgeon_name}%")
                ).first()
            else:
                # Find any available surgeon
                surgeon = self.db.query(models.Staff).filter(
                    models.Staff.role.in_(['Veterinarian', 'Orthopedic Surgeon', 'Dental Specialist'])
                ).first()

            if not surgeon:
                return {"status": "error", "message": "No surgeon available."}

            # Parse date
            surgery_date = self._parse_date(date)
            if not surgery_date:
                return {"status": "error", "message": f"Could not parse date: {date}"}

            start_time = datetime.combine(surgery_date, datetime.strptime("10:00", "%H:%M").time())
            end_time = start_time + timedelta(hours=2)

            surgery = models.Surgery(
                pet_id=pet.id,
                staff_id=surgeon.id,
                surgery_type=surgery_type,
                notes=notes,
                start_time=start_time,
                end_time=end_time,
                status="Scheduled"
            )
            self.db.add(surgery)
            self.db.commit()
            self.db.refresh(surgery)

            client = self.db.query(models.Client).filter(models.Client.id == pet.client_id).first()

            return {
                "status": "success",
                "message": f"{surgery_type} scheduled for {pet.name} on {start_time.strftime('%B %d at %I:%M %p')}.",
                "surgery_id": surgery.id,
                "pet_name": pet.name,
                "owner_name": client.name if client else "Unknown",
                "surgeon": surgeon.name,
                "date": start_time.strftime("%A, %B %d, %Y"),
                "time": start_time.strftime("%I:%M %p")
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": f"Error scheduling surgery: {str(e)}"}

    async def update_pet_info(
        self,
        pet_name: str,
        owner_name: Optional[str] = None,
        new_name: Optional[str] = None,
        new_breed: Optional[str] = None,
        new_species: Optional[str] = None,
        new_dob: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update pet information."""
        try:
            query = self.db.query(models.Pet).filter(
                models.Pet.name.ilike(f"%{pet_name}%")
            )
            if owner_name:
                query = query.join(models.Client).filter(
                    models.Client.name.ilike(f"%{owner_name}%")
                )
            pet = query.first()

            if not pet:
                return {"status": "error", "message": f"Pet '{pet_name}' not found."}

            updates = []
            if new_name:
                pet.name = new_name
                updates.append(f"name to '{new_name}'")
            if new_breed:
                pet.breed = new_breed
                updates.append(f"breed to '{new_breed}'")
            if new_species:
                pet.species = new_species
                updates.append(f"species to '{new_species}'")
            if new_dob:
                dob = self._parse_date(new_dob)
                if dob:
                    pet.date_of_birth = dob
                    updates.append(f"date of birth to '{new_dob}'")

            if updates:
                self.db.commit()
                return {
                    "status": "success",
                    "message": f"Updated {', '.join(updates)} for {pet_name}.",
                    "pet_id": pet.id
                }
            else:
                return {"status": "error", "message": "No updates provided."}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": f"Error updating pet: {str(e)}"}
