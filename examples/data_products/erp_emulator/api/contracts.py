"""Contract API Endpoints

CRUD operations for procurement contracts.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional
from datetime import datetime
from database import get_db
from models.contract import Contract
from models.supplier import Supplier
from models.material import Material
from schemas.contract import (
    ContractCreate,
    ContractUpdate,
    ContractResponse,
    ContractListResponse,
)

router = APIRouter(prefix="/api/contracts", tags=["contracts"])


@router.get("", response_model=ContractListResponse)
async def list_contracts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    supplier_id: Optional[int] = None,
    material_id: Optional[int] = None,
    status: Optional[str] = Query(None, pattern="^(active|expired|cancelled)$"),
    db: AsyncSession = Depends(get_db),
):
    """List all contracts with pagination and filters"""

    # Build query
    query = select(Contract)

    # Apply filters
    if supplier_id:
        query = query.where(Contract.supplier_id == supplier_id)
    if material_id:
        query = query.where(Contract.material_id == material_id)
    if status:
        query = query.where(Contract.status == status)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    query = query.order_by(Contract.id).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    contracts = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return ContractListResponse(
        items=[ContractResponse.model_validate(c) for c in contracts],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get contract by ID"""

    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    return ContractResponse.model_validate(contract)


@router.post("", response_model=ContractResponse, status_code=201)
async def create_contract(
    contract_data: ContractCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new contract"""

    # Verify supplier exists
    supplier_result = await db.execute(
        select(Supplier).where(Supplier.id == contract_data.supplier_id)
    )
    if not supplier_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Supplier not found")

    # Verify material exists
    material_result = await db.execute(
        select(Material).where(Material.id == contract_data.material_id)
    )
    if not material_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Material not found")

    # Validate dates
    if contract_data.end_date and contract_data.end_date <= contract_data.start_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")

    # Generate contract number
    contract_number = f"CTR-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    contract = Contract(**contract_data.model_dump(), contract_number=contract_number)
    db.add(contract)
    await db.commit()
    await db.refresh(contract)

    return ContractResponse.model_validate(contract)


@router.put("/{contract_id}", response_model=ContractResponse)
async def update_contract(
    contract_id: int,
    contract_data: ContractUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a contract"""

    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    # Update fields
    update_data = contract_data.model_dump(exclude_unset=True)

    # Validate dates if both are provided
    if "end_date" in update_data and update_data["end_date"]:
        if update_data["end_date"] <= contract.start_date:
            raise HTTPException(
                status_code=400, detail="End date must be after start date"
            )

    for field, value in update_data.items():
        setattr(contract, field, value)

    await db.commit()
    await db.refresh(contract)

    return ContractResponse.model_validate(contract)


@router.delete("/{contract_id}", status_code=204)
async def delete_contract(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a contract"""

    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    await db.delete(contract)
    await db.commit()

    return None
