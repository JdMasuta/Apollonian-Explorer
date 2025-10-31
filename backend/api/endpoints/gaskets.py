"""
Gasket API endpoints.

Reference: .DESIGN_SPEC.md section 5 (REST API Endpoints)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Use relative import
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.deps import get_db
from schemas import GasketCreate, GasketResponse
from services import GasketService

router = APIRouter()


@router.post("/gaskets", response_model=GasketResponse, status_code=status.HTTP_201_CREATED)
def create_gasket(
    gasket_data: GasketCreate,
    db: Session = Depends(get_db)
):
    """
    Create or retrieve an Apollonian gasket.

    If a gasket with the same initial curvatures exists and has sufficient
    depth, returns the cached version. Otherwise, generates a new gasket.

    Args:
        gasket_data: Request data with curvatures and max_depth
        db: Database session (dependency injection)

    Returns:
        GasketResponse with gasket data and all circles

    Raises:
        HTTPException 400: Invalid curvatures or parameters
        HTTPException 500: Server error during generation

    Example:
        POST /api/gaskets
        {
            "curvatures": ["1", "1", "1"],
            "max_depth": 5
        }

    Reference:
        .DESIGN_SPEC.md section 5.1 - POST /api/gaskets endpoint
    """
    try:
        service = GasketService(db)
        gasket = service.create_or_get_gasket(
            curvatures=gasket_data.curvatures,
            max_depth=gasket_data.max_depth
        )
        return gasket

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_CURVATURES", "message": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "GENERATION_ERROR", "message": str(e)}
        )


@router.get("/gaskets/{gasket_id}", response_model=GasketResponse)
def get_gasket(gasket_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a gasket by ID.

    Args:
        gasket_id: Gasket database ID
        db: Database session (dependency injection)

    Returns:
        GasketResponse with gasket data and all circles

    Raises:
        HTTPException 404: Gasket not found

    Example:
        GET /api/gaskets/1

    Reference:
        .DESIGN_SPEC.md section 5.2 - GET /api/gaskets/{id} endpoint
    """
    service = GasketService(db)
    gasket = service.get_gasket(gasket_id)

    if not gasket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "GASKET_NOT_FOUND", "message": f"Gasket with ID {gasket_id} not found"}
        )

    return gasket
