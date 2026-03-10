"""Supplier Schemas

Request/response schemas for supplier operations.
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime


class SupplierBase(BaseModel):
    """Base supplier fields"""

    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    contact_person: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    credit_rating: str = Field("B", pattern="^[A-D]$")
    status: str = Field("active", pattern="^(active|inactive)$")


class SupplierCreate(SupplierBase):
    """Schema for creating a supplier"""

    pass


class SupplierUpdate(BaseModel):
    """Schema for updating a supplier"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    contact_person: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    credit_rating: Optional[str] = Field(None, pattern="^[A-D]$")
    status: Optional[str] = Field(None, pattern="^(active|inactive)$")


class SupplierResponse(SupplierBase):
    """Supplier response with ID and timestamps"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class SupplierListResponse(BaseModel):
    """Paginated supplier list response"""

    items: list[SupplierResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
