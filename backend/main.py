from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from api.router import api_router
from db import create_tables

app = FastAPI(title="Apollonian Gasket API", version="1.0.0")

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables on startup
@app.on_event("startup")
def startup_event():
    """Initialize database on startup."""
    create_tables()

# Health check endpoint
@app.get("/health")
def health_check():
    """
    Health check endpoint.

    Returns application status and database connectivity.
    """
    try:
        from db import SessionLocal
        db = SessionLocal()
        # Test DB connection
        db.execute("SELECT 1")
        db.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "database": db_status,
        "version": "1.0.0"
    }

# Mount API routes
app.include_router(api_router, prefix="/api")

# Mount static files (frontend build) - only in production
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
