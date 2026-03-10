"""Material API Endpoints

CRUD operations for materials.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from database import get_db
from models.material import Material
from schemas.material import (
    MaterialCreate,
    MaterialUpdate,
    MaterialResponse,
    MaterialListResponse,
)

router = APIRouter(prefix="/api/materials", tags=["materials"])


@router.get("", response_model=MaterialListResponse)
async def list_materials(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all materials with pagination and filters"""

    # Build query
    query = select(Material)

    # Apply filters
    if category:
        query = query.where(Material.category == category)
    if search:
        query = query.where(
            (Material.name.ilike(f"%{search}%")) | (Material.code.ilike(f"%{search}%"))
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    query = query.order_by(Material.id).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    materials = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return MaterialListResponse(
        items=[MaterialResponse.model_validate(m) for m in materials],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{material_id}", response_model=MaterialResponse)
async def get_material(
    material_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get material by ID"""

    result = await db.execute(select(Material).where(Material.id == material_id))
    material = result.scalar_one_or_none()

    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    return MaterialResponse.model_validate(material)


@router.post("", response_model=MaterialResponse, status_code=201)
async def create_material(
    material_data: MaterialCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new material"""

    # Check if code already exists
    existing = await db.execute(
        select(Material).where(Material.code == material_data.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Material code already exists")

    material = Material(**material_data.model_dump())
    db.add(material)
    await db.commit()
    await db.refresh(material)

    return MaterialResponse.model_validate(material)


@router.put("/{material_id}", response_model=MaterialResponse)
async def update_material(
    material_id: int,
    material_data: MaterialUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a material"""

    result = await db.execute(select(Material).where(Material.id == material_id))
    material = result.scalar_one_or_none()

    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    # Update fields
    update_data = material_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(material, field, value)

    await db.commit()
    await db.refresh(material)

    return MaterialResponse.model_validate(material)


@router.delete("/{material_id}", status_code=204)
async def delete_material(
    material_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a material"""

    result = await db.execute(select(Material).where(Material.id == material_id))
    material = result.scalar_one_or_none()

    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    await db.delete(material)
    await db.commit()

    return None
