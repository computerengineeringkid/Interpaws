import time
from datetime import date
from typing import List

from fastapi import FastAPI, Depends
from sqlalchemy import Date, cast, text
from sqlalchemy.orm import Session

from . import models, schemas
from .database import engine, SessionLocal

app = FastAPI()

@app.on_event("startup")
def on_startup() -> None:
    """Ensure DB is reachable and create tables with simple retries.

    This avoids import-time connection attempts and tolerates slow DB startup.
    """
    max_attempts = 10
    delay_seconds = 2

    for attempt in range(1, max_attempts + 1):
        try:
            # Try to connect; this ensures the database is up
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            # Create tables once connection succeeds
            models.Base.metadata.create_all(bind=engine)
            break
        except Exception:  # noqa: BLE001 - broad to handle transient DB errors
            if attempt == max_attempts:
                raise
            time.sleep(delay_seconds)


@app.get("/")
def read_root():
    return {"message": "Welcome to the Interpaws API!"}


def get_db():
    """Provide a database session per request."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/bookings/", response_model=schemas.Booking)
async def create_booking(booking: schemas.BookingCreate, db: Session = Depends(get_db)):
    db_booking = models.Booking(**booking.model_dump())  # type: ignore[arg-type]
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking


@app.get("/bookings/{date}", response_model=List[schemas.Booking])
async def get_bookings_for_date(date: date, db: Session = Depends(get_db)):
    return (
        db.query(models.Booking)
        .filter(cast(models.Booking.start_time, Date) == date)
        .all()
    )
