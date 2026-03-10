"""Purchase Order Schemas

Request/response schemas for purchase order operations.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class OrderItemBase(BaseModel):
    """Base order item fields"""

    material_id: int = Field(..., gt=0)
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    discount_percent: float = Field(0.0, ge=0, le=100)


class OrderItemCreate(OrderItemBase):
    """Schema for creating an order item"""

    pass


class OrderItemResponse(OrderItemBase):
    """Order item response"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    subtotal: float
    delivery_status: str


class PurchaseOrderBase(BaseModel):
    """Base purchase order fields"""

    supplier_id: int = Field(..., gt=0)
    status: str = Field(
        "draft",
        pattern="^(draft|pending|confirmed|partial|delivered|cancelled)$",
    )
    delivery_date: Optional[datetime] = None
    payment_terms: str = Field("NET 30", max_length=100)
    shipping_address: Optional[str] = None
    notes: Optional[str] = None


class PurchaseOrderCreate(PurchaseOrderBase):
    """Schema for creating a purchase order"""

    items: List[OrderItemCreate] = Field(..., min_length=1)


class PurchaseOrderUpdate(BaseModel):
    """Schema for updating a purchase order"""

    status: Optional[str] = Field(
        None,
        pattern="^(draft|pending|confirmed|partial|delivered|cancelled)$",
    )
    delivery_date: Optional[datetime] = None
    payment_terms: Optional[str] = Field(None, max_length=100)
    shipping_address: Optional[str] = None
    notes: Optional[str] = None


class PurchaseOrderResponse(PurchaseOrderBase):
    """Purchase order response without items"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    total_amount: float
    order_date: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None


class PurchaseOrderWithItemsResponse(PurchaseOrderResponse):
    """Purchase order response with items"""

    items: List[OrderItemResponse]


class PurchaseOrderListResponse(BaseModel):
    """Paginated purchase order list response"""

    items: list[PurchaseOrderResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
