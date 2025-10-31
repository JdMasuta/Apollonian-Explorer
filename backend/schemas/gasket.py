"""
Pydantic schemas for Gasket API requests and responses.

Reference: .DESIGN_SPEC.md section 5 (API Endpoints) and API_USAGE_GUIDE.md
"""

from typing import List, Optional
from fractions import Fraction
from pydantic import BaseModel, Field, field_validator

from schemas.circle import CircleResponse


class GasketCreate(BaseModel):
    """
    Request schema for creating/retrieving a gasket.

    Attributes:
        curvatures: List of 3-4 curvature strings (e.g., ["1", "1", "1"] or ["3/2", "5/3", "7/4"])
        max_depth: Maximum recursion depth (1-15, default 5)

    Example:
        {
            "curvatures": ["1", "1", "1"],
            "max_depth": 5
        }
    """

    curvatures: List[str] = Field(
        ...,
        min_length=3,
        max_length=4,
        description="List of 3-4 curvature strings (e.g., ['1', '1', '1'])",
    )
    max_depth: int = Field(
        default=5,
        ge=1,
        le=15,
        description="Maximum recursion depth (1-15)",
    )

    @field_validator("curvatures")
    @classmethod
    def validate_curvatures(cls, v: List[str]) -> List[str]:
        """
        Validate that curvatures are valid Fraction strings.

        Args:
            v: List of curvature strings

        Returns:
            Validated list of curvature strings

        Raises:
            ValueError: If any curvature is invalid
        """
        if not (3 <= len(v) <= 4):
            raise ValueError("Must provide 3 or 4 curvatures")

        # Try to parse each as Fraction to validate format
        parsed_fractions = []
        for i, curv_str in enumerate(v):
            try:
                frac = Fraction(curv_str)
                parsed_fractions.append(frac)
            except (ValueError, ZeroDivisionError) as e:
                raise ValueError(
                    f"Invalid curvature at index {i}: '{curv_str}'. "
                    f"Must be a valid fraction string (e.g., '1', '3/2'). Error: {e}"
                )

        # Check for zero curvatures (infinite radius circles not yet supported)
        if any(f == 0 for f in parsed_fractions):
            raise ValueError(
                "Zero curvatures (infinite radius circles) are not yet supported"
            )

        return v

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "examples": [
                {"curvatures": ["1", "1", "1"], "max_depth": 5},
                {"curvatures": ["-1", "2", "2"], "max_depth": 7},
                {"curvatures": ["3/2", "5/3", "7/4"], "max_depth": 3},
            ]
        }


class GasketResponse(BaseModel):
    """
    Response schema for gasket data.

    Attributes:
        id: Gasket database ID
        hash: SHA-256 hash of initial curvatures (cache key)
        initial_curvatures: List of curvature strings
        num_circles: Total number of circles in gasket
        max_depth_cached: Maximum depth cached in database
        created_at: ISO timestamp of creation
        last_accessed_at: ISO timestamp of last access
        access_count: Number of times accessed
        circles: List of circle data

    Example:
        {
            "id": 1,
            "hash": "abc123...",
            "initial_curvatures": ["1", "1", "1"],
            "num_circles": 50,
            "max_depth_cached": 5,
            "created_at": "2025-10-31T12:00:00Z",
            "last_accessed_at": "2025-10-31T12:30:00Z",
            "access_count": 3,
            "circles": [...]
        }
    """

    id: int = Field(..., description="Gasket database ID")
    hash: str = Field(..., description="SHA-256 hash of initial curvatures")
    initial_curvatures: List[str] = Field(
        ..., description="Initial curvature strings"
    )
    num_circles: int = Field(..., description="Total number of circles")
    max_depth_cached: int = Field(..., description="Maximum depth cached")
    created_at: str = Field(..., description="ISO timestamp of creation")
    last_accessed_at: Optional[str] = Field(
        None, description="ISO timestamp of last access"
    )
    access_count: int = Field(..., description="Number of times accessed")
    circles: List[CircleResponse] = Field(..., description="List of circles")

    class Config:
        """Pydantic config."""

        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "hash": "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
                "initial_curvatures": ["1", "1", "1"],
                "num_circles": 50,
                "max_depth_cached": 5,
                "created_at": "2025-10-31T12:00:00Z",
                "last_accessed_at": "2025-10-31T12:30:00Z",
                "access_count": 3,
                "circles": [
                    {
                        "id": 1,
                        "curvature": "1/1",
                        "center": {"x": "0/1", "y": "0/1"},
                        "radius": "1/1",
                        "generation": 0,
                        "parent_ids": [],
                        "tangent_ids": [2, 3],
                    }
                ],
            }
        }
