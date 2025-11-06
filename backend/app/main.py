import time
from fastapi import FastAPI
from . import models
from .database import engine

app = FastAPI()

@app.on_event("startup")
def on_startup() -> None:
    """Ensure DB is reachable and create tables with simple retries.

    This avoids import-time connection attempts and tolerates slow DB startup.
    """
    max_attempts = 10
    delay_seconds = 2

    from sqlalchemy import text

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
