"""
SQLite-Datenbank für Terminbuchung.
GDPR: Automatische Löschung alter Termine (>30 Tage).
"""

from contextlib import contextmanager
from datetime import date, datetime, timedelta, time
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from agent.config import get_settings

Base = declarative_base()


def get_engine():
    """Erstellt SQLite-Engine mit DB-Pfad aus Config."""
    settings = get_settings()
    path = Path(settings.booking_db_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}", echo=False)


def init_db(engine=None) -> None:
    """Erstellt Tabellen falls nicht vorhanden."""
    if engine is None:
        engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                slot_date DATE NOT NULL,
                slot_time TIME NOT NULL,
                treatment TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_bookings_date 
            ON bookings(slot_date)
        """))


def cleanup_old_bookings(engine=None, days: int = 30) -> int:
    """
    Löscht Termine älter als N Tage (GDPR Retention).
    Returns: Anzahl gelöschter Buchungen.
    """
    if engine is None:
        engine = get_engine()
    cutoff = date.today() - timedelta(days=days)

    with engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM bookings WHERE slot_date < :cutoff"),
            {"cutoff": cutoff.isoformat()},
        )
        return result.rowcount


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context Manager für DB-Session."""
    engine = get_engine()
    init_db(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_available_slots(session: Session, target_date: date) -> list[tuple[date, time]]:
    """
    Gibt verfügbare Slots für ein Datum zurück.
    Slots: 9:00–17:00, 30-Min-Intervalle, außer bereits gebuchte.
    """
    from sqlalchemy import text as sql_text

    slots = []
    for hour in range(9, 17):
        for minute in (0, 30):
            t = time(hour, minute)
            slots.append((target_date, t))

    # Gebuchte Slots abziehen
    result = session.execute(
        sql_text("SELECT slot_date, slot_time FROM bookings WHERE slot_date = :d"),
        {"d": target_date.isoformat()},
    )
    booked = {(row[0], row[1]) for row in result}

    return [(d, t) for d, t in slots if (d, t) not in booked]


def create_booking(
    session: Session,
    slot_date: date,
    slot_time: time,
    patient_name: str,
    patient_phone: Optional[str] = None,
    treatment: Optional[str] = None,
    notes: Optional[str] = None,
) -> int:
    """Erstellt Patient + Buchung. Returns booking_id."""
    from sqlalchemy import text as sql_text

    # Patient anlegen
    session.execute(
        sql_text(
            "INSERT INTO patients (name, phone) VALUES (:name, :phone)"
        ),
        {"name": patient_name, "phone": patient_phone},
    )
    session.flush()
    patient_id = session.execute(sql_text("SELECT last_insert_rowid()")).scalar()

    # Buchung anlegen
    session.execute(
        sql_text("""
            INSERT INTO bookings (patient_id, slot_date, slot_time, treatment, notes)
            VALUES (:pid, :d, :t, :tr, :n)
        """),
        {
            "pid": patient_id,
            "d": slot_date.isoformat(),
            "t": slot_time.strftime("%H:%M:%S"),
            "tr": treatment,
            "n": notes,
        },
    )
    session.flush()
    booking_id = session.execute(sql_text("SELECT last_insert_rowid()")).scalar()
    return booking_id


def cancel_booking(session: Session, booking_id: int) -> bool:
    """Storniert Buchung. Returns True wenn gefunden."""
    from sqlalchemy import text as sql_text

    result = session.execute(
        sql_text("DELETE FROM bookings WHERE id = :id"),
        {"id": booking_id},
    )
    return result.rowcount > 0


def get_next_available(
    session: Session,
    treatment: Optional[str] = None,
    from_date: Optional[date] = None,
) -> Optional[tuple[date, time]]:
    """Nächster freier Slot ab from_date (default: heute)."""
    start = from_date or date.today()
    for delta in range(14):  # 2 Wochen suchen
        d = start + timedelta(days=delta)
        slots = get_available_slots(session, d)
        if slots:
            return slots[0]
    return None


def get_patient_data(session: Session, patient_id: int) -> Optional[dict]:
    """GDPR Auskunft: Alle Daten eines Patienten."""
    from sqlalchemy import text as sql_text

    row = session.execute(
        sql_text("SELECT id, name, phone FROM patients WHERE id = :id"),
        {"id": patient_id},
    ).fetchone()
    if not row:
        return None

    bookings = session.execute(
        sql_text("""
            SELECT id, slot_date, slot_time, treatment 
            FROM bookings WHERE patient_id = :pid
        """),
        {"pid": patient_id},
    ).fetchall()

    return {
        "patient_id": row[0],
        "name": row[1],
        "phone": row[2],
        "bookings": [
            {
                "id": b[0],
                "date": str(b[1]),
                "time": str(b[2]),
                "treatment": b[3],
            }
            for b in bookings
        ],
    }


def delete_patient(session: Session, patient_id: int) -> bool:
    """GDPR Löschung: Patient und alle Buchungen entfernen."""
    from sqlalchemy import text as sql_text

    session.execute(sql_text("DELETE FROM bookings WHERE patient_id = :id"), {"id": patient_id})
    result = session.execute(sql_text("DELETE FROM patients WHERE id = :id"), {"id": patient_id})
    return result.rowcount > 0


def get_booking_by_id(session: Session, booking_id: int) -> Optional[dict]:
    """Buchung nach ID (für Cancel-Validierung)."""
    from sqlalchemy import text as sql_text

    row = session.execute(
        sql_text("""
            SELECT b.id, b.patient_id, b.slot_date, b.slot_time, p.name
            FROM bookings b JOIN patients p ON b.patient_id = p.id
            WHERE b.id = :id
        """),
        {"id": booking_id},
    ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "patient_id": row[1],
        "slot_date": row[2],
        "slot_time": row[3],
        "patient_name": row[4],
    }
