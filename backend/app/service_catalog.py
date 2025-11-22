"""Service inference utilities for booking flows."""

from __future__ import annotations

from typing import Tuple

SERVICE_KEYWORDS = {
    "urgent care": ["vomit", "vomiting", "bleeding", "seizure", "collapse", "emergency", "injury"],
    "vaccination": ["vaccine", "shot", "shots", "booster", "rabies", "distemper"],
    "wellness exam": ["checkup", "wellness", "annual", "physical", "exam"],
    "surgery consult": ["surgery", "spay", "neuter", "mass", "lump", "growth"],
    "dental cleaning": ["dental", "teeth", "tooth", "cleaning", "tartar"],
    "behavior consult": ["behavior", "anxious", "anxiety", "aggression", "fear"],
}

SERVICE_DURATIONS = {
    "urgent care": 60,
    "vaccination": 30,
    "wellness exam": 45,
    "surgery consult": 60,
    "dental cleaning": 90,
    "behavior consult": 60,
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

    return "urgent care", "Defaulted to urgent care when no clear match was found."


def get_service_duration_minutes(service_type: str) -> int:
    return SERVICE_DURATIONS.get(service_type.lower(), 60)
