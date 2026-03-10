"""Payment API Endpoints

CRUD operations for payments.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime
from database import get_db
from models.payment import Payment
from models.purchase_order import PurchaseOrder
from schemas.payment import (
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
    PaymentListResponse,
)

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.get("", response_model=PaymentListResponse)
async def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    order_id: Optional[int] = None,
    status: Optional[str] = Query(
        None, pattern="^(pending|processing|completed|failed|cancelled)$"
    ),
    payment_method: Optional[str] = Query(
        None, pattern="^(bank_transfer|check|credit_card|cash)$"
    ),
    db: AsyncSession = Depends(get_db),
):
    """List all payments with pagination and filters"""

    # Build query
    query = select(Payment)

    # Apply filters
    if order_id:
        query = query.where(Payment.order_id == order_id)
    if status:
        query = query.where(Payment.status == status)
    if payment_method:
        query = query.where(Payment.payment_method == payment_method)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    query = query.order_by(Payment.id).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    payments = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return PaymentListResponse(
        items=[PaymentResponse.model_validate(p) for p in payments],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get payment by ID"""

    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return PaymentResponse.model_validate(payment)


@router.post("", response_model=PaymentResponse, status_code=201)
async def create_payment(
    payment_data: PaymentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new payment"""

    # Verify order exists
    order_result = await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == payment_data.order_id)
    )
    if not order_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Order not found")

    payment = Payment(**payment_data.model_dump())
    if payment_data.payment_date:
        payment.payment_date = payment_data.payment_date
    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    return PaymentResponse.model_validate(payment)


@router.put("/{payment_id}", response_model=PaymentResponse)
async def update_payment(
    payment_id: int,
    payment_data: PaymentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a payment"""

    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Update fields
    update_data = payment_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(payment, field, value)

    await db.commit()
    await db.refresh(payment)

    return PaymentResponse.model_validate(payment)


@router.delete("/{payment_id}", status_code=204)
async def delete_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a payment"""

    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    await db.delete(payment)
    await db.commit()

    return None
