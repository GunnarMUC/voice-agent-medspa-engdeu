"""
FastAPI Booking-API.
Endpoints für Slots, Buchung, Stornierung, GDPR Auskunft/Löschung.
"""

from datetime import date, time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent.config import get_settings
from booking.database import (
    cancel_booking,
    create_booking,
    delete_patient,
    get_available_slots,
    get_booking_by_id,
    get_next_available,
    get_patient_data,
    get_session,
    cleanup_old_bookings,
)
from booking.models import (
    BookRequest,
    BookResponse,
    CancelResponse,
    NextAvailableResponse,
    PatientDataResponse,
    Slot,
    SlotResponse,
)

settings = get_settings()
app = FastAPI(title="Voice Agent Booking API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/slots", response_model=SlotResponse)
def list_slots(date_param: date):
    """Verfügbare Slots für ein Datum. Query: ?date_param=2025-02-20"""
    with get_session() as session:
        slots_tuples = get_available_slots(session, date_param)
        slots = [
            Slot(
                date=d,
                time=t,
                slot_id=f"{d.isoformat()}_{t.strftime('%H:%M')}",
            )
            for d, t in slots_tuples
        ]
        return SlotResponse(slots=slots, date=date_param)


@app.post("/book", response_model=BookResponse)
def book_appointment(req: BookRequest):
    """Termin buchen."""
    try:
        date_str, time_str = req.slot_id.split("_")
        slot_date = date.fromisoformat(date_str)
        if len(time_str) == 5:  # "09:00"
            time_str = time_str + ":00"
        slot_time = time.fromisoformat(time_str)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Ungültiges slot_id Format (erwartet: YYYY-MM-DD_HH:MM)")

    with get_session() as session:
        # Prüfen ob Slot frei
        available = get_available_slots(session, slot_date)
        if (slot_date, slot_time) not in available:
            raise HTTPException(status_code=409, detail="Slot nicht mehr verfügbar")

        booking_id = create_booking(
            session=session,
            slot_date=slot_date,
            slot_time=slot_time,
            patient_name=req.patient.name,
            patient_phone=req.patient.phone,
            treatment=req.treatment,
            notes=req.notes,
        )

    return BookResponse(
        booking_id=booking_id,
        slot_id=req.slot_id,
        date=slot_date,
        time=slot_time,
        patient_name=req.patient.name,
    )


@app.get("/next-available", response_model=NextAvailableResponse)
def next_available(treatment: str | None = None):
    """Nächster freier Termin."""
    with get_session() as session:
        result = get_next_available(session, treatment=treatment)
        if not result:
            raise HTTPException(status_code=404, detail="Kein freier Slot in den nächsten 14 Tagen")

        slot_date, slot_time = result
        slot_id = f"{slot_date.isoformat()}_{slot_time.strftime('%H:%M')}"
        return NextAvailableResponse(
            slot_id=slot_id,
            date=slot_date,
            time=slot_time,
            treatment=treatment,
        )


@app.delete("/cancel/{booking_id}", response_model=CancelResponse)
def cancel_appointment(booking_id: int):
    """Termin stornieren."""
    with get_session() as session:
        if not cancel_booking(session, booking_id):
            raise HTTPException(status_code=404, detail="Buchung nicht gefunden")
    return CancelResponse(booking_id=booking_id)


@app.get("/patient/{patient_id}/data", response_model=PatientDataResponse)
def patient_data(patient_id: int):
    """GDPR Auskunft – alle gespeicherten Daten eines Patienten."""
    with get_session() as session:
        data = get_patient_data(session, patient_id)
        if not data:
            raise HTTPException(status_code=404, detail="Patient nicht gefunden")
        return PatientDataResponse(**data)


@app.delete("/patient/{patient_id}")
def patient_delete(patient_id: int):
    """GDPR Löschung – Patient und alle Buchungen entfernen."""
    with get_session() as session:
        if not delete_patient(session, patient_id):
            raise HTTPException(status_code=404, detail="Patient nicht gefunden")
    return {"message": "Patient und alle zugehörigen Daten gelöscht."}


@app.post("/cleanup")
def cleanup(days: int = 30):
    """Alte Termine löschen (GDPR Retention). Default: >30 Tage."""
    deleted = cleanup_old_bookings(days=days)
    return {"deleted": deleted, "message": f"{deleted} alte Buchungen gelöscht."}


@app.get("/health")
def health():
    """Health-Check."""
    return {"status": "ok"}


def run_server():
    """Startet den Uvicorn-Server."""
    import uvicorn

    uvicorn.run(
        "booking.api:app",
        host=settings.booking_api_host,
        port=settings.booking_api_port,
        reload=True,
    )


if __name__ == "__main__":
    run_server()
