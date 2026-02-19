"""
Pydantic Models für Terminbuchung.
Termine, Patienten, Slots – GDPR-konform (minimale Datenspeicherung).
"""

from datetime import date, time
from typing import Optional

from pydantic import BaseModel, Field


class PatientCreate(BaseModel):
    """Minimale Patientendaten für Buchung (GDPR: nur nötiges)."""

    name: str = Field(..., min_length=1, max_length=200)
    phone: Optional[str] = Field(None, max_length=30)


class Slot(BaseModel):
    """Ein verfügbarer Termin-Slot."""

    date: date
    time: time
    slot_id: str  # z.B. "2025-02-20_09:00"


class SlotResponse(BaseModel):
    """Response für verfügbare Slots."""

    slots: list[Slot]
    date: date


class BookRequest(BaseModel):
    """Anfrage zum Buchen eines Termins."""

    slot_id: str = Field(..., description="z.B. 2025-02-20_09:00")
    patient: PatientCreate
    treatment: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)


class BookResponse(BaseModel):
    """Bestätigung nach erfolgreicher Buchung."""

    booking_id: int
    slot_id: str
    date: date
    time: time
    patient_name: str
    message: str = "Termin erfolgreich gebucht."


class CancelResponse(BaseModel):
    """Bestätigung nach Stornierung."""

    booking_id: int
    message: str = "Termin storniert."


class NextAvailableResponse(BaseModel):
    """Nächster freier Termin."""

    slot_id: str
    date: date
    time: time
    treatment: Optional[str] = None


class PatientDataResponse(BaseModel):
    """GDPR Auskunft – alle gespeicherten Daten eines Patienten."""

    patient_id: int
    name: str
    phone: Optional[str]
    bookings: list[dict]  # Termine mit Datum, Uhrzeit, Behandlung
