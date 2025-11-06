from fastapi import FastAPI  # Import the FastAPI framework class
from . import models  # Import our new models
from .database import engine  # Import the engine from database.py

# Create the database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI()  # Instantiate the FastAPI application

@app.get("/")  # Declare a GET endpoint at the root URL path
def read_root():  # Define the handler function for the root endpoint
    return {"message": "Welcome to the Interpaws API!"}  # Return a JSON response payload
