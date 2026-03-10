"""Purchase Order API Endpoints

CRUD operations for purchase orders and order items.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime
from database import get_db
from models.purchase_order import PurchaseOrder, OrderItem
from models.supplier import Supplier
from schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderUpdate,
    PurchaseOrderResponse,
    PurchaseOrderWithItemsResponse,
    PurchaseOrderListResponse,
    OrderItemCreate,
    OrderItemResponse,
)
from schemas.payment import PaymentResponse
from models.payment import Payment

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("", response_model=PurchaseOrderListResponse)
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    supplier_id: Optional[int] = None,
    status: Optional[str] = Query(
        None, pattern="^(draft|pending|confirmed|partial|delivered|cancelled)$"
    ),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all purchase orders with pagination and filters"""

    # Build query
    query = select(PurchaseOrder)

    # Apply filters
    if supplier_id:
        query = query.where(PurchaseOrder.supplier_id == supplier_id)
    if status:
        query = query.where(PurchaseOrder.status == status)
    if date_from:
        query = query.where(PurchaseOrder.order_date >= date_from)
    if date_to:
        query = query.where(PurchaseOrder.order_date <= date_to)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    query = (
        query.order_by(PurchaseOrder.id).offset((page - 1) * page_size).limit(page_size)
    )
    result = await db.execute(query)
    orders = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return PurchaseOrderListResponse(
        items=[PurchaseOrderResponse.model_validate(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{order_id}", response_model=PurchaseOrderWithItemsResponse)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get order by ID with items"""

    result = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.order_items))
        .where(PurchaseOrder.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    items = [OrderItemResponse.model_validate(item) for item in order.order_items]
    order_dict = PurchaseOrderResponse.model_validate(order).model_dump()

    return PurchaseOrderWithItemsResponse(**order_dict, items=items)


@router.get("/{order_id}/payments", response_model=list[PaymentResponse])
async def get_order_payments(
    order_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get all payments for an order"""

    # Verify order exists
    order_result = await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == order_id)
    )
    if not order_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Order not found")

    result = await db.execute(
        select(Payment)
        .where(Payment.order_id == order_id)
        .order_by(Payment.payment_date)
    )
    payments = result.scalars().all()

    return [PaymentResponse.model_validate(p) for p in payments]


@router.post("", response_model=PurchaseOrderWithItemsResponse, status_code=201)
async def create_order(
    order_data: PurchaseOrderCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new purchase order with items"""

    # Verify supplier exists
    supplier_result = await db.execute(
        select(Supplier).where(Supplier.id == order_data.supplier_id)
    )
    if not supplier_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Supplier not found")

    # Generate order number
    order_number = f"PO-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Create order
    order_dict = order_data.model_dump(exclude={"items"})
    order = PurchaseOrder(**order_dict, order_number=order_number)
    db.add(order)
    await db.flush()  # Get the order ID

    # Calculate total amount and create items
    total_amount = 0.0
    for item_data in order_data.items:
        subtotal = (
            item_data.quantity
            * item_data.unit_price
            * (1 - item_data.discount_percent / 100)
        )
        total_amount += subtotal

        item = OrderItem(
            order_id=order.id,
            material_id=item_data.material_id,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            subtotal=subtotal,
            discount_percent=item_data.discount_percent,
        )
        db.add(item)

    order.total_amount = total_amount
    await db.commit()
    await db.refresh(order)

    # Reload with items
    result = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.order_items))
        .where(PurchaseOrder.id == order.id)
    )
    order = result.scalar_one()

    items = [OrderItemResponse.model_validate(item) for item in order.order_items]
    order_dict = PurchaseOrderResponse.model_validate(order).model_dump()

    return PurchaseOrderWithItemsResponse(**order_dict, items=items)


@router.put("/{order_id}", response_model=PurchaseOrderResponse)
async def update_order(
    order_id: int,
    order_data: PurchaseOrderUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a purchase order"""

    result = await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == order_id))
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Update fields
    update_data = order_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)

    await db.commit()
    await db.refresh(order)

    return PurchaseOrderResponse.model_validate(order)


@router.delete("/{order_id}", status_code=204)
async def delete_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a purchase order"""

    result = await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == order_id))
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    await db.delete(order)
    await db.commit()

    return None
