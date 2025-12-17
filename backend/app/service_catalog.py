"""Service inference utilities for booking flows."""

from __future__ import annotations

from typing import Tuple

SERVICE_KEYWORDS = {
    "urgent care": ["vomit", "vomiting", "bleeding", "seizure", "collapse", "emergency", "trauma", "hit by car", "poisoning", "not breathing"],
    "vaccination": ["vaccine", "shot", "shots", "booster", "rabies", "distemper", "parvo", "bordetella"],
    "wellness exam": ["checkup", "wellness", "annual", "physical", "exam", "routine"],
    "surgery consult": ["surgery", "spay", "neuter", "mass", "lump", "growth", "tumor"],
    "dental cleaning": ["dental", "teeth", "tooth", "cleaning", "tartar", "breath", "gums"],
    "behavior consult": ["behavior", "anxious", "anxiety", "aggression", "fear", "barking", "biting"],
    "sick visit": ["sick", "ill", "not eating", "lethargy", "diarrhea", "cough", "coughing", "sneeze", "sneezing", "discharge", "fever"],
    "dermatology": ["scratch", "scratching", "itch", "itching", "itchy", "skin", "rash", "hair loss", "hot spot", "allergies", "allergy", "fleas", "ear infection"],
    "orthopedic": ["limp", "limping", "leg", "hip", "joint", "arthritis", "lameness", "broken", "fracture"],
}

SERVICE_DURATIONS = {
    "urgent care": 60,
    "vaccination": 30,
    "wellness exam": 45,
    "surgery consult": 60,
    "dental cleaning": 90,
    "behavior consult": 60,
    "sick visit": 30,
    "dermatology": 45,
    "orthopedic": 45,
    "general visit": 30,
}


def infer_service_type(complaint: str, fallback: str | None = None) -> Tuple[str, str]:
    """Infer a service type from a free-text complaint."""
    if fallback:
        label = fallback.strip().lower()
        if label:
            return label, "Provided by user or calling flow."

    normalized = (complaint or "").lower()
    for service, keywords in SERVICE_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return service, f"Matched keywords for {service}."

    return "general visit", "Scheduled as a general visit - the vet will assess and determine the best course of action."


def get_service_duration_minutes(service_type: str) -> int:
    return SERVICE_DURATIONS.get(service_type.lower(), 60)
