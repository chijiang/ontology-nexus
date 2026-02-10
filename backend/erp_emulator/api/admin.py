"""Admin API Endpoints

Database management and seed data operations.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from datetime import datetime, timedelta
import random
from erp_emulator.database import get_db, drop_all, init_db
from erp_emulator.models.supplier import Supplier
from erp_emulator.models.material import Material
from erp_emulator.models.purchase_order import PurchaseOrder, OrderItem
from erp_emulator.models.payment import Payment
from erp_emulator.models.contract import Contract
from erp_emulator.schemas.common import MessageResponse, SeedStatsResponse
from erp_emulator.config import settings

router = APIRouter(prefix="/api/admin", tags=["admin"])


# Seed data templates
SUPPLIER_TEMPLATES = [
    {"name": "TechSupply Corp", "credit_rating": "A", "category": "electronics"},
    {"name": "Global Materials Inc", "credit_rating": "B", "category": "materials"},
    {"name": "OfficePro Supplies", "credit_rating": "A", "category": "office"},
    {"name": "Industrial Parts Co", "credit_rating": "B", "category": "industrial"},
    {"name": "QuickShip Logistics", "credit_rating": "C", "category": "logistics"},
    {"name": "Premium Components", "credit_rating": "A", "category": "electronics"},
    {"name": "Budget Supplies Ltd", "credit_rating": "C", "category": "general"},
    {"name": "MegaSource International", "credit_rating": "B", "category": "general"},
    {"name": "Local Vendor Partners", "credit_rating": "B", "category": "local"},
    {"name": "ElectroTech Solutions", "credit_rating": "A", "category": "electronics"},
    {"name": "RawMaterials Direct", "credit_rating": "B", "category": "materials"},
    {"name": "FastTrack Components", "credit_rating": "C", "category": "electronics"},
    {"name": "ValueAdded Supplies", "credit_rating": "B", "category": "general"},
    {"name": "QualityFirst Distributors", "credit_rating": "A", "category": "general"},
    {"name": "Essential Materials Co", "credit_rating": "B", "category": "materials"},
    {"name": "ProEquipment Supplies", "credit_rating": "A", "category": "industrial"},
    {"name": "SmartSource Partners", "credit_rating": "B", "category": "general"},
    {"name": "Dependable Goods Inc", "credit_rating": "A", "category": "general"},
]

MATERIAL_TEMPLATES = [
    {
        "name": "LED Display 5 inch",
        "category": "electronics",
        "unit": "pcs",
        "price": 25.00,
    },
    {
        "name": "Microcontroller Arduino",
        "category": "electronics",
        "unit": "pcs",
        "price": 35.00,
    },
    {
        "name": "Power Adapter 12V",
        "category": "electronics",
        "unit": "pcs",
        "price": 15.00,
    },
    {
        "name": "USB Type-C Cable",
        "category": "electronics",
        "unit": "pcs",
        "price": 5.00,
    },
    {
        "name": "PCB Board 10x10cm",
        "category": "electronics",
        "unit": "pcs",
        "price": 8.00,
    },
    {"name": "Steel Sheet 2mm", "category": "materials", "unit": "pcs", "price": 45.00},
    {
        "name": "Aluminum Extrusion",
        "category": "materials",
        "unit": "m",
        "price": 12.00,
    },
    {"name": "Copper Wire 1mm", "category": "materials", "unit": "m", "price": 0.50},
    {
        "name": "Plastic Pellets ABS",
        "category": "materials",
        "unit": "kg",
        "price": 3.50,
    },
    {
        "name": "Rubber Sheet 5mm",
        "category": "materials",
        "unit": "pcs",
        "price": 22.00,
    },
    {"name": "Office Paper A4", "category": "office", "unit": "ream", "price": 6.00},
    {
        "name": "Ink Cartridge Black",
        "category": "office",
        "unit": "pcs",
        "price": 45.00,
    },
    {"name": "Filing Cabinet", "category": "office", "unit": "pcs", "price": 120.00},
    {"name": "Desk Lamp LED", "category": "office", "unit": "pcs", "price": 35.00},
    {"name": "Notebook Spiral", "category": "office", "unit": "pcs", "price": 3.00},
    {"name": "Ballpoint Pens Box", "category": "office", "unit": "box", "price": 12.00},
    {
        "name": "Industrial Motor 1HP",
        "category": "industrial",
        "unit": "pcs",
        "price": 250.00,
    },
    {
        "name": "Hydraulic Cylinder",
        "category": "industrial",
        "unit": "pcs",
        "price": 180.00,
    },
    {"name": "Conveyor Belt 1m", "category": "industrial", "unit": "m", "price": 85.00},
    {"name": "Safety Gloves", "category": "industrial", "unit": "pair", "price": 8.00},
    {
        "name": "Welding Electrodes",
        "category": "industrial",
        "unit": "kg",
        "price": 15.00,
    },
    {"name": "Cardboard Boxes", "category": "logistics", "unit": "pcs", "price": 2.50},
    {
        "name": "Bubble Wrap 100m",
        "category": "logistics",
        "unit": "roll",
        "price": 35.00,
    },
    {"name": "Packing Tape", "category": "logistics", "unit": "roll", "price": 4.00},
    {"name": "Wooden Pallet", "category": "logistics", "unit": "pcs", "price": 25.00},
]

ORDER_STATUSES = ["draft", "pending", "confirmed", "partial", "delivered", "cancelled"]
PAYMENT_STATUSES = ["pending", "processing", "completed", "failed", "cancelled"]
PAYMENT_METHODS = ["bank_transfer", "check", "credit_card", "cash"]
PAYMENT_TERMS = ["NET 15", "NET 30", "NET 45", "NET 60", "Immediate"]


def generate_code(prefix: str, id: int) -> str:
    """Generate a unique code"""
    return f"{prefix}-{str(id).zfill(4)}"


async def seed_data(
    db: AsyncSession,
    suppliers_count: int = 18,
    materials_count: int = 24,
    contracts_count: int = 35,
    orders_count: int = 220,
) -> SeedStatsResponse:
    """Generate and insert seed data into the database"""

    # Check if data already exists
    existing_suppliers = await db.execute(select(func.count()).select_from(Supplier))
    if existing_suppliers.scalar() > 0:
        raise ValueError("Database already contains data")

    stats = SeedStatsResponse()

    # Create suppliers
    suppliers = []
    # Use template length if count is small, otherwise cycle through templates
    items_to_create = (
        SUPPLIER_TEMPLATES[:suppliers_count]
        if suppliers_count <= len(SUPPLIER_TEMPLATES)
        else (SUPPLIER_TEMPLATES * (suppliers_count // len(SUPPLIER_TEMPLATES) + 1))[
            :suppliers_count
        ]
    )

    for i, template in enumerate(items_to_create, 1):
        supplier = Supplier(
            name=template["name"],
            code=generate_code("SUP", i),
            contact_person=f"Contact {i}",
            email=f"contact{i}@{template['name'].lower().replace(' ', '')}.com",
            phone=f"+1-555-{1000 + i:04d}",
            address=f"{i} Business Street, City, State",
            credit_rating=template["credit_rating"],
            status="active",
        )
        suppliers.append(supplier)
        db.add(supplier)

    await db.flush()
    stats.suppliers = len(suppliers)

    # Create materials
    materials = []
    items_to_create = (
        MATERIAL_TEMPLATES[:materials_count]
        if materials_count <= len(MATERIAL_TEMPLATES)
        else (MATERIAL_TEMPLATES * (materials_count // len(MATERIAL_TEMPLATES) + 1))[
            :materials_count
        ]
    )

    for i, template in enumerate(items_to_create, 1):
        material = Material(
            name=template["name"],
            code=generate_code("MAT", i),
            category=template["category"],
            unit=template["unit"],
            standard_price=template["price"],
            lead_time_days=random.randint(3, 21),
            min_order_quantity=random.choice([1, 10, 50, 100]),
            description=f"High quality {template['name'].lower()} for various applications.",
        )
        materials.append(material)
        db.add(material)

    await db.flush()
    stats.materials = len(materials)

    # Create contracts
    contracts = []
    for _ in range(contracts_count):
        supplier = random.choice(suppliers)
        material = random.choice(materials)
        start_date = datetime.now() - timedelta(days=random.randint(30, 365))
        end_date = start_date + timedelta(days=random.randint(180, 730))

        contract = Contract(
            supplier_id=supplier.id,
            material_id=material.id,
            contract_number=generate_code("CTR", len(contracts) + 1),
            start_date=start_date,
            end_date=end_date,
            agreed_price=material.standard_price * random.uniform(0.85, 0.95),
            min_quantity=random.randint(100, 1000),
            max_quantity=random.randint(5000, 20000),
            status="active" if end_date > datetime.now() else "expired",
            terms=f"Annual supply agreement with delivery within {material.lead_time_days} days",
        )
        contracts.append(contract)
        db.add(contract)

    await db.flush()
    stats.contracts = len(contracts)

    # Create purchase orders
    orders = []
    base_date = datetime.now() - timedelta(days=365)

    # Create material lookup map
    material_map = {m.id: m for m in materials}

    for i in range(orders_count):
        # Link order to a contract
        contract = random.choice(contracts)
        supplier_id = contract.supplier_id
        material_id = contract.material_id

        order_date = base_date + timedelta(days=random.randint(0, 365))

        order = PurchaseOrder(
            supplier_id=supplier_id,
            contract_id=contract.id,
            material_id=material_id,
            order_number=generate_code("PO", i + 1),
            status=random.choices(
                ORDER_STATUSES,
                weights=[15, 20, 30, 15, 15, 5],
                k=1,
            )[0],
            order_date=order_date,
            delivery_date=order_date + timedelta(days=random.randint(7, 60)),
            payment_terms=random.choice(PAYMENT_TERMS),
            shipping_address=f"Company Warehouse, Building {random.randint(1, 5)}",
            notes=random.choice(["", "Urgent delivery", "Quality check required", ""]),
        )
        orders.append(order)
        db.add(order)

    await db.flush()
    stats.orders = len(orders)

    # Create order items
    order_items = []
    for order in orders:
        # Order is tied to a specific material via contract
        material = material_map[order.material_id]

        # Generate 1 item for the contract material
        quantity = random.randint(10, 500)
        unit_price = material.standard_price * random.uniform(0.9, 1.1)
        discount = random.uniform(0, 15)

        item = OrderItem(
            order_id=order.id,
            material_id=material.id,
            quantity=quantity,
            unit_price=round(unit_price, 2),
            subtotal=round(quantity * unit_price * (1 - discount / 100), 2),
            discount_percent=round(discount, 2),
            delivery_status=random.choices(
                ["pending", "partial", "complete"],
                weights=[40, 30, 30],
                k=1,
            )[0],
        )
        order_items.append(item)
        db.add(item)

        # Update order total
        order.total_amount += item.subtotal

    await db.flush()
    stats.order_items = len(order_items)

    # Create payments
    payments = []
    for order in orders:
        # Number of payments per order (0-3)
        num_payments = random.choices([0, 1, 2, 3], weights=[10, 50, 30, 10], k=1)[0]

        for j in range(num_payments):
            payment_amount = min(
                order.total_amount * random.uniform(0.3, 1.0),
                order.total_amount,
            )
            payment_date = order.order_date + timedelta(days=random.randint(0, 90))

            payment = Payment(
                order_id=order.id,
                payment_date=payment_date,
                amount=round(payment_amount, 2),
                payment_method=random.choice(PAYMENT_METHODS),
                status=random.choices(
                    PAYMENT_STATUSES,
                    weights=[25, 15, 50, 5, 5],
                    k=1,
                )[0],
                reference=f"TXN-{random.randint(100000, 999999)}",
            )
            payments.append(payment)
            db.add(payment)

    await db.flush()
    stats.payments = len(payments)

    await db.commit()

    return stats


@router.post("/seed", response_model=SeedStatsResponse)
async def seed_database(db: AsyncSession = Depends(get_db)):
    """Generate and insert seed data into the database"""
    try:
        return await seed_data(
            db,
            settings.SEED_SUPPLIERS_COUNT,
            settings.SEED_MATERIALS_COUNT,
            settings.SEED_CONTRACTS_COUNT,
            settings.SEED_ORDERS_COUNT,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/reset", response_model=MessageResponse)
async def reset_database(db: AsyncSession = Depends(get_db)):
    """Reset the database by dropping and recreating all tables"""

    await drop_all()
    await init_db()

    return MessageResponse(
        message="Database reset successfully. Use /seed to populate with data.",
        success=True,
    )


@router.get("/stats", response_model=SeedStatsResponse)
async def get_database_stats(db: AsyncSession = Depends(get_db)):
    """Get current database statistics"""

    suppliers_count = await db.execute(select(func.count()).select_from(Supplier))
    materials_count = await db.execute(select(func.count()).select_from(Material))
    contracts_count = await db.execute(select(func.count()).select_from(Contract))
    orders_count = await db.execute(select(func.count()).select_from(PurchaseOrder))
    order_items_count = await db.execute(select(func.count()).select_from(OrderItem))
    payments_count = await db.execute(select(func.count()).select_from(Payment))

    return SeedStatsResponse(
        suppliers=suppliers_count.scalar(),
        materials=materials_count.scalar(),
        contracts=contracts_count.scalar(),
        orders=orders_count.scalar(),
        order_items=order_items_count.scalar(),
        payments=payments_count.scalar(),
    )
