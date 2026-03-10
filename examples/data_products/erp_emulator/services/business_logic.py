"""Business Logic Services

Business operations for order processing and related activities.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from typing import Optional
import random

from models.purchase_order import PurchaseOrder, OrderItem
from models.payment import Payment
from models.contract import Contract
from models.supplier import Supplier
from models.material import Material


class OrderService:
    """Service for purchase order business operations"""

    @staticmethod
    async def get_contract_price(
        db: AsyncSession,
        supplier_id: int,
        material_id: int,
    ) -> Optional[float]:
        """Get agreed price from active contract if available"""

        result = await db.execute(
            select(Contract)
            .where(
                and_(
                    Contract.supplier_id == supplier_id,
                    Contract.material_id == material_id,
                    Contract.status == "active",
                    Contract.start_date <= datetime.now(),
                )
            )
            .order_by(Contract.agreed_price.asc())
        )
        contract = result.first()

        if contract:
            return contract[0].agreed_price
        return None

    @staticmethod
    async def validate_order_items(
        db: AsyncSession,
        items: list[dict],
    ) -> tuple[bool, Optional[str]]:
        """Validate order items for material existence and pricing"""

        for item in items:
            result = await db.execute(
                select(Material).where(Material.id == item["material_id"])
            )
            material = result.scalar_one_or_none()

            if not material:
                return False, f"Material with ID {item['material_id']} not found"

            if item["quantity"] < material.min_order_quantity:
                return (
                    False,
                    f"Quantity for {material.name} is below minimum order quantity of {material.min_order_quantity}",
                )

        return True, None

    @staticmethod
    async def calculate_order_total(
        db: AsyncSession,
        items: list[dict],
    ) -> float:
        """Calculate total amount for order items"""

        total = 0.0
        for item in items:
            subtotal = (
                item["quantity"]
                * item["unit_price"]
                * (1 - item.get("discount_percent", 0) / 100)
            )
            total += subtotal

        return round(total, 2)

    @staticmethod
    async def get_outstanding_balance(
        db: AsyncSession,
        order_id: int,
    ) -> float:
        """Calculate outstanding balance for an order"""

        # Get order total
        result = await db.execute(
            select(PurchaseOrder).where(PurchaseOrder.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            return 0.0

        # Get completed payments
        payments_result = await db.execute(
            select(Payment).where(
                and_(
                    Payment.order_id == order_id,
                    Payment.status == "completed",
                )
            )
        )
        payments = payments_result.scalars().all()

        paid_amount = sum(p.amount for p in payments)
        return round(order.total_amount - paid_amount, 2)

    @staticmethod
    async def get_supplier_performance(
        db: AsyncSession,
        supplier_id: int,
    ) -> dict:
        """Get performance metrics for a supplier"""

        # Get all orders for supplier
        result = await db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.supplier_id == supplier_id)
            .options(selectinload(PurchaseOrder.payments))
        )
        orders = result.scalars().all()

        if not orders:
            return {
                "total_orders": 0,
                "delivered_orders": 0,
                "on_time_deliveries": 0,
                "total_amount": 0.0,
                "average_order_value": 0.0,
            }

        delivered = sum(1 for o in orders if o.status == "delivered")
        total_amount = sum(o.total_amount for o in orders)

        # Calculate on-time deliveries (delivered before or on delivery_date)
        on_time = sum(
            1
            for o in orders
            if o.status == "delivered"
            and o.delivery_date
            and o.updated_at <= o.delivery_date
        )

        return {
            "total_orders": len(orders),
            "delivered_orders": delivered,
            "on_time_deliveries": on_time,
            "total_amount": round(total_amount, 2),
            "average_order_value": round(total_amount / len(orders), 2),
        }
