# Prompt Pilot Backend Application

This directory contains the core FastAPI application logic for Prompt Pilot.

- `main.py`: The main FastAPI application instance and startup.
- `models.py`: Pydantic models representing data structures (e.g., for database interaction, internal objects).
- `schemas.py`: Pydantic schemas for API request and response validation and serialization.
- `crud.py`: Functions for Create, Read, Update, Delete operations, abstracting data access.
- `auth.py`: Authentication logic, including password hashing, JWT management, and dependency for current user.
- `routers/`: Directory containing API route modules.
