"""Common Schemas

Shared schemas for pagination and common responses.
"""

from pydantic import BaseModel, Field
from typing import Generic, TypeVar, Optional
from datetime import datetime

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pagination parameters"""

    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(cls, items: list[T], total: int, page: int, page_size: int):
        """Create a paginated response"""
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class MessageResponse(BaseModel):
    """Simple message response"""

    message: str
    success: bool = True


class SeedStatsResponse(BaseModel):
    """Seed data statistics"""

    suppliers: int = 0
    materials: int = 0
    contracts: int = 0
    orders: int = 0
    order_items: int = 0
    payments: int = 0
