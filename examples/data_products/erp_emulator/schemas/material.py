"""Material Schemas

Request/response schemas for material operations.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class MaterialBase(BaseModel):
    """Base material fields"""

    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    category: Optional[str] = Field(None, max_length=100)
    unit: str = Field("pcs", max_length=20)
    standard_price: float = Field(0.0, ge=0)
    lead_time_days: int = Field(7, ge=0)
    min_order_quantity: int = Field(1, ge=1)
    description: Optional[str] = None


class MaterialCreate(MaterialBase):
    """Schema for creating a material"""

    pass


class MaterialUpdate(BaseModel):
    """Schema for updating a material"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    unit: Optional[str] = Field(None, max_length=20)
    standard_price: Optional[float] = Field(None, ge=0)
    lead_time_days: Optional[int] = Field(None, ge=0)
    min_order_quantity: Optional[int] = Field(None, ge=1)
    description: Optional[str] = None


class MaterialResponse(MaterialBase):
    """Material response with ID and timestamps"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class MaterialListResponse(BaseModel):
    """Paginated material list response"""

    items: list[MaterialResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
