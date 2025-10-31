"""
API router aggregating all endpoint routes.

Reference: .DESIGN_SPEC.md section 5 (API Endpoints)
"""

from fastapi import APIRouter

# Use relative import
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.endpoints import gaskets

# Create main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(gaskets.router, tags=["gaskets"])

# Future routers can be added here:
# api_router.include_router(sequences.router, prefix="/sequences", tags=["sequences"])
# api_router.include_router(export.router, prefix="/export", tags=["export"])
