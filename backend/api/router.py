"""
API router aggregating all endpoint routes.

Reference: .DESIGN_SPEC.md section 5 (API Endpoints)
"""

from fastapi import APIRouter

from api.endpoints import analytics, export, gaskets

# Create main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(gaskets.router, tags=["gaskets"])
api_router.include_router(analytics.router, tags=["analytics"])
api_router.include_router(export.router, tags=["export"])

# Future routers can be added here:
# api_router.include_router(sequences.router, prefix="/sequences", tags=["sequences"])
