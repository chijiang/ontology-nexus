"""Supplier API Endpoints

CRUD operations for suppliers.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import Optional
from database import get_db
from models.supplier import Supplier
from schemas.supplier import (
    SupplierCreate,
    SupplierUpdate,
    SupplierResponse,
    SupplierListResponse,
)

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


@router.get("", response_model=SupplierListResponse)
async def list_suppliers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, pattern="^(active|inactive)$"),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all suppliers with pagination and filters"""

    # Build query
    query = select(Supplier)

    # Apply filters
    if status:
        query = query.where(Supplier.status == status)
    if search:
        query = query.where(
            (Supplier.name.ilike(f"%{search}%")) | (Supplier.code.ilike(f"%{search}%"))
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    query = query.order_by(Supplier.id).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    suppliers = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return SupplierListResponse(
        items=[SupplierResponse.model_validate(s) for s in suppliers],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get supplier by ID"""

    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()

    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    return SupplierResponse.model_validate(supplier)


@router.post("", response_model=SupplierResponse, status_code=201)
async def create_supplier(
    supplier_data: SupplierCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new supplier"""

    # Check if code already exists
    existing = await db.execute(
        select(Supplier).where(Supplier.code == supplier_data.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Supplier code already exists")

    supplier = Supplier(**supplier_data.model_dump())
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)

    return SupplierResponse.model_validate(supplier)


@router.put("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: int,
    supplier_data: SupplierUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a supplier"""

    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()

    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Update fields
    update_data = supplier_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(supplier, field, value)

    await db.commit()
    await db.refresh(supplier)

    return SupplierResponse.model_validate(supplier)


@router.delete("/{supplier_id}", status_code=204)
async def delete_supplier(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a supplier"""

    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()

    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    await db.delete(supplier)
    await db.commit()

    return None
