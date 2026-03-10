"""Payment Schemas

Request/response schemas for payment operations.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class PaymentBase(BaseModel):
    """Base payment fields"""

    order_id: int = Field(..., gt=0)
    payment_date: Optional[datetime] = None
    amount: float = Field(..., gt=0)
    payment_method: str = Field(
        "bank_transfer",
        pattern="^(bank_transfer|check|credit_card|cash)$",
    )
    reference: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)


class PaymentCreate(PaymentBase):
    """Schema for creating a payment"""

    status: str = Field(
        "pending",
        pattern="^(pending|processing|completed|failed|cancelled)$",
    )


class PaymentUpdate(BaseModel):
    """Schema for updating a payment"""

    amount: Optional[float] = Field(None, gt=0)
    payment_method: Optional[str] = Field(
        None,
        pattern="^(bank_transfer|check|credit_card|cash)$",
    )
    status: Optional[str] = Field(
        None,
        pattern="^(pending|processing|completed|failed|cancelled)$",
    )
    reference: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)


class PaymentResponse(PaymentBase):
    """Payment response with ID and timestamps"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    payment_date: datetime
    created_at: datetime


class PaymentListResponse(BaseModel):
    """Paginated payment list response"""

    items: list[PaymentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
