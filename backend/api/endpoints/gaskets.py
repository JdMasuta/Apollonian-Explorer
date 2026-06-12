"""
Gasket API endpoints.

Reference: .DESIGN_SPEC.md section 5 (REST API Endpoints)
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

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
            max_depth=gasket_data.max_depth,
            min_radius=gasket_data.min_radius,
            include_circles=gasket_data.include_circles,
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


@router.get("/gaskets/{gasket_id}/circles")
def get_circles_in_viewport(
    gasket_id: int,
    min_x: Optional[float] = None,
    max_x: Optional[float] = None,
    min_y: Optional[float] = None,
    max_y: Optional[float] = None,
    min_radius: Optional[float] = None,
    limit: int = Query(default=20000, ge=1, le=200000),
    db: Session = Depends(get_db),
):
    """
    Retrieve cached circles intersecting a viewport rectangle.

    Filters on the indexed float mirrors (schema v2): a circle is returned
    when its disk overlaps the bbox and its radius is >= min_radius. All
    parameters optional; omitted bounds are unconstrained.

    Example:
        GET /api/gaskets/1/circles?min_x=-0.5&max_x=0.5&min_y=-0.5&max_y=0.5&min_radius=0.01

    Reference:
        REVAMP_BLUEPRINT.md Milestone 2 (viewport-driven queries)
    """
    service = GasketService(db)
    circles = service.get_circles_in_viewport(
        gasket_id,
        min_x=min_x,
        max_x=max_x,
        min_y=min_y,
        max_y=max_y,
        min_radius=min_radius,
        limit=limit,
    )

    if circles is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "GASKET_NOT_FOUND", "message": f"Gasket with ID {gasket_id} not found"}
        )

    return {"gasket_id": gasket_id, "count": len(circles), "circles": circles}


class DeepenRequest(BaseModel):
    """Local refinement request: resume the walk at a circle's tree node."""

    word: str = Field(
        ...,
        min_length=1,
        max_length=120,
        pattern=r"^(S[0-3]|[0-3]+)$",
        description="Group word of the circle to refine around ('S0'-'S3' for seeds)",
    )
    min_radius: float = Field(
        ..., gt=0, description="Resolution bound for the refinement (model units)"
    )
    max_extra_depth: int = Field(
        default=24, ge=1, le=64, description="Generations to descend below the word"
    )


@router.post("/gaskets/{gasket_id}/deepen")
def deepen_gasket(
    gasket_id: int,
    request: DeepenRequest,
    db: Session = Depends(get_db),
):
    """
    Refine the packing locally around a cached circle (deep-zoom support).

    Resumes the generation walk at the tree node addressed by the circle's
    group word, bounded by resolution; new circles are persisted and the
    full local subtree (capped) is returned.

    Reference: REVAMP_BLUEPRINT.md Milestone 3 (viewport-driven deepening).
    """
    service = GasketService(db)
    try:
        result = service.deepen(
            gasket_id,
            word=request.word,
            min_radius=request.min_radius,
            max_extra_depth=request.max_extra_depth,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_WORD", "message": str(e)},
        )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "GASKET_NOT_FOUND", "message": f"Gasket with ID {gasket_id} not found"}
        )

    return result


@router.delete("/gaskets/{gasket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_gasket(gasket_id: int, db: Session = Depends(get_db)):
    """
    Delete a gasket and all associated data.

    Returns 204 No Content on success. Raises 404 if gasket not found.
    """
    service = GasketService(db)
    deleted = service.delete_gasket(gasket_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "GASKET_NOT_FOUND", "message": f"Gasket with ID {gasket_id} not found"}
        )

    # FastAPI will use the status_code on the decorator; return an empty Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)
