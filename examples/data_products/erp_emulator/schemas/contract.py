"""Contract Schemas

Request/response schemas for contract operations.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class ContractBase(BaseModel):
    """Base contract fields"""

    supplier_id: int = Field(..., gt=0)
    material_id: int = Field(..., gt=0)
    start_date: datetime
    end_date: Optional[datetime] = None
    agreed_price: float = Field(..., gt=0)
    min_quantity: float = Field(1.0, gt=0)
    max_quantity: Optional[float] = Field(None, gt=0)
    status: str = Field(
        "active",
        pattern="^(active|expired|cancelled)$",
    )
    terms: Optional[str] = Field(None, max_length=500)


class ContractCreate(ContractBase):
    """Schema for creating a contract"""

    pass


class ContractUpdate(BaseModel):
    """Schema for updating a contract"""

    end_date: Optional[datetime] = None
    agreed_price: Optional[float] = Field(None, gt=0)
    min_quantity: Optional[float] = Field(None, gt=0)
    max_quantity: Optional[float] = Field(None, gt=0)
    status: Optional[str] = Field(
        None,
        pattern="^(active|expired|cancelled)$",
    )
    terms: Optional[str] = Field(None, max_length=500)


class ContractResponse(ContractBase):
    """Contract response with ID and timestamps"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    contract_number: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class ContractListResponse(BaseModel):
    """Paginated contract list response"""

    items: list[ContractResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
