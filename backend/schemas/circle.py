"""
Pydantic schemas for Circle API responses.

Reference: .DESIGN_SPEC.md section 5 (API Endpoints) and API_USAGE_GUIDE.md
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class CircleResponse(BaseModel):
    """
    Circle data in API response.

    All geometric values are returned as rational number strings (e.g., "3/2").

    Attributes:
        id: Circle database ID
        curvature: Curvature as string "num/denom"
        center: Center coordinates as {"x": "num/denom", "y": "num/denom"}
        radius: Radius as string "num/denom"
        generation: Recursion depth (0 for initial circles)
        parent_ids: List of parent circle IDs (circles used to generate this one)
        tangent_ids: List of circles tangent to this one

    Example:
        {
            "id": 5,
            "curvature": "3/2",
            "center": {"x": "1/4", "y": "-1/3"},
            "radius": "2/3",
            "generation": 2,
            "parent_ids": [1, 2, 3],
            "tangent_ids": [2, 3, 4, 6]
        }
    """

    id: int = Field(..., description="Circle database ID")
    curvature: str = Field(..., description="Curvature as rational string (num/denom)")
    center: Dict[str, str] = Field(
        ..., description='Center as {"x": "num/denom", "y": "num/denom"}'
    )
    radius: str = Field(..., description="Radius as rational string (num/denom)")
    generation: int = Field(..., description="Recursion depth (0 = initial circle)")
    parent_ids: List[int] = Field(
        default_factory=list, description="Parent circle IDs"
    )
    tangent_ids: List[int] = Field(
        default_factory=list, description="Tangent circle IDs"
    )

    class Config:
        """Pydantic config."""

        from_attributes = True  # Enable ORM mode for SQLAlchemy models
        json_schema_extra = {
            "example": {
                "id": 5,
                "curvature": "3/2",
                "center": {"x": "1/4", "y": "-1/3"},
                "radius": "2/3",
                "generation": 2,
                "parent_ids": [1, 2, 3],
                "tangent_ids": [2, 3, 4, 6],
            }
        }
