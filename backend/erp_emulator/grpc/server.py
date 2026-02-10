"""ERP Emulator gRPC Server

Async gRPC server implementation for all ERP services.
"""

import asyncio
import time
from datetime import datetime
from typing import Optional
import grpc
from grpc.aio import ServicerContext
from grpc_reflection.v1alpha import reflection
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete
from sqlalchemy.orm import joinedload

from erp_emulator.database import async_session_maker
from erp_emulator.models import (
    Supplier,
    Material,
    PurchaseOrder,
    OrderItem,
    Payment,
    Contract,
)

# Import generated protobuf classes
from erp_emulator.grpc import (
    supplier_pb2,
    supplier_pb2_grpc,
    material_pb2,
    material_pb2_grpc,
    order_pb2,
    order_pb2_grpc,
    payment_pb2,
    payment_pb2_grpc,
    contract_pb2,
    contract_pb2_grpc,
    admin_pb2,
    admin_pb2_grpc,
    common_pb2,
)


# Utility functions for conversions
def datetime_to_timestamp(dt: Optional[datetime]) -> int:
    """Convert datetime to Unix timestamp"""
    if dt is None:
        return 0
    return int(dt.timestamp())


def map_credit_rating(rating: str) -> int:
    """Map string credit rating to enum value"""
    mapping = {"A": 1, "B": 2, "C": 3, "D": 4}
    return mapping.get(rating, 0)


def map_status(status: str) -> int:
    """Map string status to enum value"""
    mapping = {"active": 1, "inactive": 2}
    return mapping.get(status, 0)


def str_to_status(status: int) -> str:
    """Map enum value to string status"""
    mapping = {0: "", 1: "active", 2: "inactive"}
    return mapping.get(status, "")


def str_to_credit_rating(rating: int) -> str:
    """Map enum value to string credit rating"""
    mapping = {0: "", 1: "A", 2: "B", 3: "C", 4: "D"}
    return mapping.get(rating, "")


def map_order_status(status: str) -> int:
    """Map order status to enum value"""
    mapping = {
        "draft": 1,
        "pending": 2,
        "confirmed": 3,
        "partial": 4,
        "delivered": 5,
        "cancelled": 6,
    }
    return mapping.get(status, 0)


def str_to_order_status(status: int) -> str:
    """Map enum value to order status"""
    mapping = {
        0: "",
        1: "draft",
        2: "pending",
        3: "confirmed",
        4: "partial",
        5: "delivered",
        6: "cancelled",
    }
    return mapping.get(status, "")


def map_payment_status(status: str) -> int:
    """Map payment status to enum value"""
    mapping = {
        "pending": 1,
        "processing": 2,
        "completed": 3,
        "failed": 4,
        "cancelled": 5,
    }
    return mapping.get(status, 0)


def str_to_payment_status(status: int) -> str:
    """Map enum value to payment status"""
    mapping = {
        0: "",
        1: "pending",
        2: "processing",
        3: "completed",
        4: "failed",
        5: "cancelled",
    }
    return mapping.get(status, "")


def map_payment_method(method: str) -> int:
    """Map payment method to enum value"""
    mapping = {
        "bank_transfer": 1,
        "check": 2,
        "credit_card": 3,
        "cash": 4,
    }
    return mapping.get(method, 0)


def str_to_payment_method(method: int) -> str:
    """Map enum value to payment method"""
    mapping = {0: "", 1: "bank_transfer", 2: "check", 3: "credit_card", 4: "cash"}
    return mapping.get(method, "")


def map_contract_status(status: str) -> int:
    """Map contract status to enum value"""
    mapping = {
        "active": 1,
        "expired": 2,
        "cancelled": 3,
    }
    return mapping.get(status, 0)


def str_to_contract_status(status: int) -> str:
    """Map enum value to contract status"""
    mapping = {0: "", 1: "active", 2: "expired", 3: "cancelled"}
    return mapping.get(status, "")


def map_delivery_status(status: str) -> int:
    """Map delivery status to enum value"""
    mapping = {
        "pending": 1,
        "partial": 2,
        "complete": 3,
    }
    return mapping.get(status, 0)


def str_to_delivery_status(status: int) -> str:
    """Map enum value to delivery status"""
    mapping = {0: "", 1: "pending", 2: "partial", 3: "complete"}
    return mapping.get(status, "")


# ============================================================================
# Supplier Service
# ============================================================================


class SupplierServicer(supplier_pb2_grpc.SupplierServiceServicer):
    """Supplier service implementation"""

    async def GetSupplier(self, request, context: ServicerContext):
        """Get supplier by ID or code"""
        async with async_session_maker() as db:
            if request.HasField("id"):
                result = await db.execute(
                    select(Supplier).where(Supplier.id == request.id)
                )
            else:
                result = await db.execute(
                    select(Supplier).where(Supplier.code == request.code)
                )

            supplier = result.scalar_one_or_none()
            if not supplier:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Supplier not found")

            return supplier_pb2.Supplier(
                id=supplier.id,
                name=supplier.name,
                code=supplier.code,
                contact_person=supplier.contact_person or "",
                email=supplier.email or "",
                phone=supplier.phone or "",
                address=supplier.address or "",
                credit_rating=map_credit_rating(supplier.credit_rating),
                status=map_status(supplier.status),
                created_at=datetime_to_timestamp(supplier.created_at),
                updated_at=datetime_to_timestamp(supplier.updated_at),
            )

    async def CreateSupplier(self, request, context: ServicerContext):
        """Create a new supplier"""
        async with async_session_maker() as db:
            # Check if code exists
            existing = await db.execute(
                select(Supplier).where(Supplier.code == request.code)
            )
            if existing.scalar_one_or_none():
                await context.abort(
                    grpc.StatusCode.ALREADY_EXISTS, "Supplier code already exists"
                )

            supplier = Supplier(
                name=request.name,
                code=request.code,
                contact_person=request.contact_person or None,
                email=request.email or None,
                phone=request.phone or None,
                address=request.address or None,
                credit_rating=str_to_credit_rating(request.credit_rating),
                status=str_to_status(request.status),
            )
            db.add(supplier)
            await db.commit()
            await db.refresh(supplier)

            return supplier_pb2.Supplier(
                id=supplier.id,
                name=supplier.name,
                code=supplier.code,
                contact_person=supplier.contact_person or "",
                email=supplier.email or "",
                phone=supplier.phone or "",
                address=supplier.address or "",
                credit_rating=map_credit_rating(supplier.credit_rating),
                status=map_status(supplier.status),
                created_at=datetime_to_timestamp(supplier.created_at),
                updated_at=datetime_to_timestamp(supplier.updated_at),
            )

    async def UpdateSupplier(self, request, context: ServicerContext):
        """Update supplier"""
        async with async_session_maker() as db:
            result = await db.execute(select(Supplier).where(Supplier.id == request.id))
            supplier = result.scalar_one_or_none()

            if not supplier:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Supplier not found")

            if request.name:
                supplier.name = request.name
            if request.contact_person:
                supplier.contact_person = request.contact_person
            if request.email:
                supplier.email = request.email
            if request.phone:
                supplier.phone = request.phone
            if request.address:
                supplier.address = request.address
            if request.credit_rating:
                supplier.credit_rating = str_to_credit_rating(request.credit_rating)
            if request.status:
                supplier.status = str_to_status(request.status)

            await db.commit()
            await db.refresh(supplier)

            return supplier_pb2.Supplier(
                id=supplier.id,
                name=supplier.name,
                code=supplier.code,
                contact_person=supplier.contact_person or "",
                email=supplier.email or "",
                phone=supplier.phone or "",
                address=supplier.address or "",
                credit_rating=map_credit_rating(supplier.credit_rating),
                status=map_status(supplier.status),
                created_at=datetime_to_timestamp(supplier.created_at),
                updated_at=datetime_to_timestamp(supplier.updated_at),
            )

    async def DeleteSupplier(self, request, context: ServicerContext):
        """Delete supplier"""
        async with async_session_maker() as db:
            if request.HasField("id"):
                result = await db.execute(
                    select(Supplier).where(Supplier.id == request.id)
                )
            else:
                result = await db.execute(
                    select(Supplier).where(Supplier.code == request.code)
                )

            supplier = result.scalar_one_or_none()
            if not supplier:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Supplier not found")

            await db.delete(supplier)
            await db.commit()

            return common_pb2.Empty()

    async def ListSuppliers(self, request, context: ServicerContext):
        """List suppliers with pagination"""
        async with async_session_maker() as db:
            query = select(Supplier)

            # Apply filters
            if request.status:
                query = query.where(Supplier.status == str_to_status(request.status))
            if request.search:
                query = query.where(
                    (Supplier.name.ilike(f"%{request.search}%"))
                    | (Supplier.code.ilike(f"%{request.search}%"))
                )

            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar()

            # Apply pagination
            page = request.pagination.page if request.HasField("pagination") else 1
            page_size = (
                request.pagination.page_size if request.HasField("pagination") else 20
            )

            query = (
                query.order_by(Supplier.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            result = await db.execute(query)
            suppliers = result.scalars().all()

            items = []
            for supplier in suppliers:
                items.append(
                    supplier_pb2.Supplier(
                        id=supplier.id,
                        name=supplier.name,
                        code=supplier.code,
                        contact_person=supplier.contact_person or "",
                        email=supplier.email or "",
                        phone=supplier.phone or "",
                        address=supplier.address or "",
                        credit_rating=map_credit_rating(supplier.credit_rating),
                        status=map_status(supplier.status),
                        created_at=datetime_to_timestamp(supplier.created_at),
                        updated_at=datetime_to_timestamp(supplier.updated_at),
                    )
                )

            total_pages = (total + page_size - 1) // page_size if total > 0 else 0

            return supplier_pb2.ListSuppliersResponse(
                items=items,
                pagination=common_pb2.PaginationResponse(
                    total=total,
                    page=page,
                    page_size=page_size,
                    total_pages=total_pages,
                ),
            )


# ============================================================================
# Material Service
# ============================================================================


class MaterialServicer(material_pb2_grpc.MaterialServiceServicer):
    """Material service implementation"""

    async def GetMaterial(self, request, context: ServicerContext):
        """Get material by ID or code"""
        async with async_session_maker() as db:
            if request.HasField("id"):
                result = await db.execute(
                    select(Material).where(Material.id == request.id)
                )
            else:
                result = await db.execute(
                    select(Material).where(Material.code == request.code)
                )

            material = result.scalar_one_or_none()
            if not material:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Material not found")

            return material_pb2.Material(
                id=material.id,
                name=material.name,
                code=material.code,
                category=material.category or "",
                unit=material.unit,
                standard_price=material.standard_price,
                lead_time_days=material.lead_time_days,
                min_order_quantity=material.min_order_quantity,
                description=material.description or "",
                created_at=datetime_to_timestamp(material.created_at),
                updated_at=datetime_to_timestamp(material.updated_at),
            )

    async def CreateMaterial(self, request, context: ServicerContext):
        """Create a new material"""
        async with async_session_maker() as db:
            # Check if code exists
            existing = await db.execute(
                select(Material).where(Material.code == request.code)
            )
            if existing.scalar_one_or_none():
                await context.abort(
                    grpc.StatusCode.ALREADY_EXISTS, "Material code already exists"
                )

            material = Material(
                name=request.name,
                code=request.code,
                category=request.category or None,
                unit=request.unit,
                standard_price=request.standard_price,
                lead_time_days=request.lead_time_days,
                min_order_quantity=request.min_order_quantity,
                description=request.description or None,
            )
            db.add(material)
            await db.commit()
            await db.refresh(material)

            return material_pb2.Material(
                id=material.id,
                name=material.name,
                code=material.code,
                category=material.category or "",
                unit=material.unit,
                standard_price=material.standard_price,
                lead_time_days=material.lead_time_days,
                min_order_quantity=material.min_order_quantity,
                description=material.description or "",
                created_at=datetime_to_timestamp(material.created_at),
                updated_at=datetime_to_timestamp(material.updated_at),
            )

    async def UpdateMaterial(self, request, context: ServicerContext):
        """Update material"""
        async with async_session_maker() as db:
            result = await db.execute(select(Material).where(Material.id == request.id))
            material = result.scalar_one_or_none()

            if not material:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Material not found")

            if request.name:
                material.name = request.name
            if request.category:
                material.category = request.category
            if request.unit:
                material.unit = request.unit
            if request.standard_price:
                material.standard_price = request.standard_price
            if request.lead_time_days:
                material.lead_time_days = request.lead_time_days
            if request.min_order_quantity:
                material.min_order_quantity = request.min_order_quantity
            if request.description:
                material.description = request.description

            await db.commit()
            await db.refresh(material)

            return material_pb2.Material(
                id=material.id,
                name=material.name,
                code=material.code,
                category=material.category or "",
                unit=material.unit,
                standard_price=material.standard_price,
                lead_time_days=material.lead_time_days,
                min_order_quantity=material.min_order_quantity,
                description=material.description or "",
                created_at=datetime_to_timestamp(material.created_at),
                updated_at=datetime_to_timestamp(material.updated_at),
            )

    async def DeleteMaterial(self, request, context: ServicerContext):
        """Delete material"""
        async with async_session_maker() as db:
            if request.HasField("id"):
                result = await db.execute(
                    select(Material).where(Material.id == request.id)
                )
            else:
                result = await db.execute(
                    select(Material).where(Material.code == request.code)
                )

            material = result.scalar_one_or_none()
            if not material:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Material not found")

            await db.delete(material)
            await db.commit()

            return common_pb2.Empty()

    async def ListMaterials(self, request, context: ServicerContext):
        """List materials with pagination"""
        async with async_session_maker() as db:
            query = select(Material)

            # Apply filters
            if request.category:
                query = query.where(Material.category == request.category)
            if request.search:
                query = query.where(
                    (Material.name.ilike(f"%{request.search}%"))
                    | (Material.code.ilike(f"%{request.search}%"))
                )

            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar()

            # Apply pagination
            page = request.pagination.page if request.HasField("pagination") else 1
            page_size = (
                request.pagination.page_size if request.HasField("pagination") else 20
            )

            query = (
                query.order_by(Material.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            result = await db.execute(query)
            materials = result.scalars().all()

            items = []
            for material in materials:
                items.append(
                    material_pb2.Material(
                        id=material.id,
                        name=material.name,
                        code=material.code,
                        category=material.category or "",
                        unit=material.unit,
                        standard_price=material.standard_price,
                        lead_time_days=material.lead_time_days,
                        min_order_quantity=material.min_order_quantity,
                        description=material.description or "",
                        created_at=datetime_to_timestamp(material.created_at),
                        updated_at=datetime_to_timestamp(material.updated_at),
                    )
                )

            total_pages = (total + page_size - 1) // page_size if total > 0 else 0

            return material_pb2.ListMaterialsResponse(
                items=items,
                pagination=common_pb2.PaginationResponse(
                    total=total,
                    page=page,
                    page_size=page_size,
                    total_pages=total_pages,
                ),
            )


# ============================================================================
# Payment Service (needed by OrderService for streaming)
# ============================================================================


class PaymentServicer(payment_pb2_grpc.PaymentServiceServicer):
    """Payment service implementation"""

    async def GetPayment(self, request, context: ServicerContext):
        """Get payment by ID"""
        async with async_session_maker() as db:
            result = await db.execute(select(Payment).where(Payment.id == request.id))
            payment = result.scalar_one_or_none()
            if not payment:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Payment not found")

            return payment_pb2.Payment(
                id=payment.id,
                order_id=payment.order_id,
                payment_date=datetime_to_timestamp(payment.payment_date),
                amount=payment.amount,
                method=map_payment_method(payment.payment_method),
                status=map_payment_status(payment.status),
                reference=payment.reference or "",
                notes=payment.notes or "",
                created_at=datetime_to_timestamp(payment.created_at),
            )

    async def CreatePayment(self, request, context: ServicerContext):
        """Create a new payment"""
        async with async_session_maker() as db:
            from erp_emulator.models.purchase_order import PurchaseOrder

            # Verify order exists
            order_result = await db.execute(
                select(PurchaseOrder).where(PurchaseOrder.id == request.order_id)
            )
            if not order_result.scalar_one_or_none():
                await context.abort(grpc.StatusCode.NOT_FOUND, "Order not found")

            payment = Payment(
                order_id=request.order_id,
                payment_date=(
                    datetime.fromtimestamp(request.payment_date)
                    if request.payment_date
                    else None
                ),
                amount=request.amount,
                payment_method=str_to_payment_method(request.method),
                status=str_to_payment_status(request.status),
                reference=request.reference or None,
                notes=request.notes or None,
            )
            db.add(payment)
            await db.commit()
            await db.refresh(payment)

            return payment_pb2.Payment(
                id=payment.id,
                order_id=payment.order_id,
                payment_date=datetime_to_timestamp(payment.payment_date),
                amount=payment.amount,
                method=map_payment_method(payment.payment_method),
                status=map_payment_status(payment.status),
                reference=payment.reference or "",
                notes=payment.notes or "",
                created_at=datetime_to_timestamp(payment.created_at),
            )

    async def UpdatePayment(self, request, context: ServicerContext):
        """Update payment"""
        async with async_session_maker() as db:
            result = await db.execute(select(Payment).where(Payment.id == request.id))
            payment = result.scalar_one_or_none()

            if not payment:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Payment not found")

            if request.amount:
                payment.amount = request.amount
            if request.method:
                payment.payment_method = str_to_payment_method(request.method)
            if request.status:
                payment.status = str_to_payment_status(request.status)
            if request.reference:
                payment.reference = request.reference
            if request.notes:
                payment.notes = request.notes

            await db.commit()
            await db.refresh(payment)

            return payment_pb2.Payment(
                id=payment.id,
                order_id=payment.order_id,
                payment_date=datetime_to_timestamp(payment.payment_date),
                amount=payment.amount,
                method=map_payment_method(payment.payment_method),
                status=map_payment_status(payment.status),
                reference=payment.reference or "",
                notes=payment.notes or "",
                created_at=datetime_to_timestamp(payment.created_at),
            )

    async def DeletePayment(self, request, context: ServicerContext):
        """Delete payment"""
        async with async_session_maker() as db:
            result = await db.execute(select(Payment).where(Payment.id == request.id))
            payment = result.scalar_one_or_none()
            if not payment:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Payment not found")

            await db.delete(payment)
            await db.commit()

            return common_pb2.Empty()

    async def ListPayments(self, request, context: ServicerContext):
        """List payments with pagination"""
        async with async_session_maker() as db:
            query = select(Payment)

            # Apply filters
            if request.order_id:
                query = query.where(Payment.order_id == request.order_id)
            if request.status:
                query = query.where(
                    Payment.status == str_to_payment_status(request.status)
                )
            if request.method:
                query = query.where(
                    Payment.payment_method == str_to_payment_method(request.method)
                )

            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar()

            # Apply pagination
            page = request.pagination.page if request.HasField("pagination") else 1
            page_size = (
                request.pagination.page_size if request.HasField("pagination") else 20
            )

            query = (
                query.order_by(Payment.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            result = await db.execute(query)
            payments = result.scalars().all()

            items = []
            for payment in payments:
                items.append(
                    payment_pb2.Payment(
                        id=payment.id,
                        order_id=payment.order_id,
                        payment_date=datetime_to_timestamp(payment.payment_date),
                        amount=payment.amount,
                        method=map_payment_method(payment.payment_method),
                        status=map_payment_status(payment.status),
                        reference=payment.reference or "",
                        notes=payment.notes or "",
                        created_at=datetime_to_timestamp(payment.created_at),
                    )
                )

            total_pages = (total + page_size - 1) // page_size if total > 0 else 0

            return payment_pb2.ListPaymentsResponse(
                items=items,
                pagination=common_pb2.PaginationResponse(
                    total=total,
                    page=page,
                    page_size=page_size,
                    total_pages=total_pages,
                ),
            )


# ============================================================================
# Order Service
# ============================================================================


class OrderServicer(order_pb2_grpc.OrderServiceServicer):
    """Order service implementation"""

    async def GetOrder(self, request, context: ServicerContext):
        """Get order by ID or number"""
        async with async_session_maker() as db:
            from sqlalchemy.orm import selectinload

            if request.HasField("id"):
                result = await db.execute(
                    select(PurchaseOrder)
                    .options(selectinload(PurchaseOrder.order_items))
                    .where(PurchaseOrder.id == request.id)
                )
            else:
                result = await db.execute(
                    select(PurchaseOrder)
                    .options(selectinload(PurchaseOrder.order_items))
                    .where(PurchaseOrder.order_number == request.order_number)
                )

            order = result.scalar_one_or_none()
            if not order:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Order not found")

            items = []
            for item in order.order_items:
                items.append(
                    order_pb2.OrderItem(
                        id=item.id,
                        order_id=item.order_id,
                        material_id=item.material_id,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        subtotal=item.subtotal,
                        discount_percent=item.discount_percent,
                        delivery_status=map_delivery_status(item.delivery_status),
                    )
                )

            return order_pb2.PurchaseOrder(
                id=order.id,
                order_number=order.order_number,
                supplier_id=order.supplier_id,
                status=map_order_status(order.status),
                order_date=datetime_to_timestamp(order.order_date),
                delivery_date=datetime_to_timestamp(order.delivery_date),
                total_amount=order.total_amount,
                payment_terms=order.payment_terms,
                shipping_address=order.shipping_address or "",
                notes=order.notes or "",
                created_at=datetime_to_timestamp(order.created_at),
                updated_at=datetime_to_timestamp(order.updated_at),
                items=items,
                contract_id=order.contract_id,
                material_id=order.material_id,
            )

    async def CreateOrder(self, request, context: ServicerContext):
        """Create a new order"""
        async with async_session_maker() as db:
            from erp_emulator.models.supplier import Supplier
            import time

            # Verify supplier exists
            supplier_result = await db.execute(
                select(Supplier).where(Supplier.id == request.supplier_id)
            )
            if not supplier_result.scalar_one_or_none():
                await context.abort(grpc.StatusCode.NOT_FOUND, "Supplier not found")

            # Generate order number
            order_number = f"PO-{int(time.time())}"

            # Create order
            order = PurchaseOrder(
                supplier_id=request.supplier_id,
                contract_id=(
                    request.contract_id if request.HasField("contract_id") else None
                ),
                material_id=(
                    request.material_id if request.HasField("material_id") else None
                ),
                order_number=order_number,
                status=str_to_order_status(request.status),
                delivery_date=(
                    datetime.fromtimestamp(request.delivery_date)
                    if request.delivery_date
                    else None
                ),
                payment_terms=request.payment_terms,
                shipping_address=request.shipping_address or None,
                notes=request.notes or None,
            )
            db.add(order)
            await db.flush()

            # Create items and calculate total
            total_amount = 0.0
            for item_req in request.items:
                # Verify material exists
                material_result = await db.execute(
                    select(Material).where(Material.id == item_req.material_id)
                )
                if not material_result.scalar_one_or_none():
                    await context.abort(
                        grpc.StatusCode.NOT_FOUND,
                        f"Material {item_req.material_id} not found",
                    )

                subtotal = (
                    item_req.quantity
                    * item_req.unit_price
                    * (1 - item_req.discount_percent / 100)
                )
                total_amount += subtotal

                item = OrderItem(
                    order_id=order.id,
                    material_id=item_req.material_id,
                    quantity=item_req.quantity,
                    unit_price=item_req.unit_price,
                    subtotal=subtotal,
                    discount_percent=item_req.discount_percent,
                )
                db.add(item)

            order.total_amount = total_amount
            await db.commit()
            await db.refresh(order)

            # Reload with items
            from sqlalchemy.orm import selectinload

            result = await db.execute(
                select(PurchaseOrder)
                .options(selectinload(PurchaseOrder.order_items))
                .where(PurchaseOrder.id == order.id)
            )
            order = result.scalar_one()

            items = []
            for item in order.order_items:
                items.append(
                    order_pb2.OrderItem(
                        id=item.id,
                        order_id=item.order_id,
                        material_id=item.material_id,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        subtotal=item.subtotal,
                        discount_percent=item.discount_percent,
                        delivery_status=map_delivery_status(item.delivery_status),
                    )
                )

            return order_pb2.PurchaseOrder(
                id=order.id,
                order_number=order.order_number,
                supplier_id=order.supplier_id,
                status=map_order_status(order.status),
                order_date=datetime_to_timestamp(order.order_date),
                delivery_date=datetime_to_timestamp(order.delivery_date),
                total_amount=order.total_amount,
                payment_terms=order.payment_terms,
                shipping_address=order.shipping_address or "",
                notes=order.notes or "",
                created_at=datetime_to_timestamp(order.created_at),
                updated_at=datetime_to_timestamp(order.updated_at),
                items=items,
                contract_id=order.contract_id,
                material_id=order.material_id,
            )

    async def UpdateOrder(self, request, context: ServicerContext):
        """Update order"""
        async with async_session_maker() as db:
            result = await db.execute(
                select(PurchaseOrder).where(PurchaseOrder.id == request.id)
            )
            order = result.scalar_one_or_none()

            if not order:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Order not found")

            if request.status:
                order.status = str_to_order_status(request.status)
            if request.delivery_date:
                order.delivery_date = datetime.fromtimestamp(request.delivery_date)
            if request.payment_terms:
                order.payment_terms = request.payment_terms
            if request.shipping_address:
                order.shipping_address = request.shipping_address
            if request.notes:
                order.notes = request.notes

            await db.commit()
            await db.refresh(order)

            from sqlalchemy.orm import selectinload

            result = await db.execute(
                select(PurchaseOrder)
                .options(selectinload(PurchaseOrder.order_items))
                .where(PurchaseOrder.id == order.id)
            )
            order = result.scalar_one()

            items = []
            for item in order.order_items:
                items.append(
                    order_pb2.OrderItem(
                        id=item.id,
                        order_id=item.order_id,
                        material_id=item.material_id,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        subtotal=item.subtotal,
                        discount_percent=item.discount_percent,
                        delivery_status=map_delivery_status(item.delivery_status),
                    )
                )

            return order_pb2.PurchaseOrder(
                id=order.id,
                order_number=order.order_number,
                supplier_id=order.supplier_id,
                status=map_order_status(order.status),
                order_date=datetime_to_timestamp(order.order_date),
                delivery_date=datetime_to_timestamp(order.delivery_date),
                total_amount=order.total_amount,
                payment_terms=order.payment_terms,
                shipping_address=order.shipping_address or "",
                notes=order.notes or "",
                created_at=datetime_to_timestamp(order.created_at),
                updated_at=datetime_to_timestamp(order.updated_at),
                items=items,
                contract_id=order.contract_id,
                material_id=order.material_id,
            )

    async def DeleteOrder(self, request, context: ServicerContext):
        """Delete order"""
        async with async_session_maker() as db:
            if request.HasField("id"):
                result = await db.execute(
                    select(PurchaseOrder).where(PurchaseOrder.id == request.id)
                )
            else:
                result = await db.execute(
                    select(PurchaseOrder).where(
                        PurchaseOrder.order_number == request.order_number
                    )
                )

            order = result.scalar_one_or_none()
            if not order:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Order not found")

            await db.delete(order)
            await db.commit()

            return common_pb2.Empty()

    async def ListOrders(self, request, context: ServicerContext):
        """List orders with pagination"""
        async with async_session_maker() as db:
            query = select(PurchaseOrder)

            # Apply filters
            if request.supplier_id:
                query = query.where(PurchaseOrder.supplier_id == request.supplier_id)
            if request.status:
                query = query.where(
                    PurchaseOrder.status == str_to_order_status(request.status)
                )
            if request.order_date_from:
                query = query.where(
                    PurchaseOrder.order_date
                    >= datetime.fromtimestamp(request.order_date_from)
                )
            if request.order_date_to:
                query = query.where(
                    PurchaseOrder.order_date
                    <= datetime.fromtimestamp(request.order_date_to)
                )

            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar()

            # Apply pagination
            page = request.pagination.page if request.HasField("pagination") else 1
            page_size = (
                request.pagination.page_size if request.HasField("pagination") else 20
            )

            query = (
                query.order_by(PurchaseOrder.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            result = await db.execute(query)
            orders = result.scalars().all()

            items = []
            for order in orders:
                items.append(
                    order_pb2.PurchaseOrder(
                        id=order.id,
                        order_number=order.order_number,
                        supplier_id=order.supplier_id,
                        status=map_order_status(order.status),
                        order_date=datetime_to_timestamp(order.order_date),
                        delivery_date=datetime_to_timestamp(order.delivery_date),
                        total_amount=order.total_amount,
                        payment_terms=order.payment_terms,
                        shipping_address=order.shipping_address or "",
                        notes=order.notes or "",
                        created_at=datetime_to_timestamp(order.created_at),
                        updated_at=datetime_to_timestamp(order.updated_at),
                        items=[],  # Empty unless requested
                        contract_id=order.contract_id,
                        material_id=order.material_id,
                    )
                )

            total_pages = (total + page_size - 1) // page_size if total > 0 else 0

            return order_pb2.ListOrdersResponse(
                items=items,
                pagination=common_pb2.PaginationResponse(
                    total=total,
                    page=page,
                    page_size=page_size,
                    total_pages=total_pages,
                ),
            )

    async def GetOrderPayments(self, request, context: ServicerContext):
        """Stream payments for an order"""
        async with async_session_maker() as db:
            # Verify order exists
            result = await db.execute(
                select(PurchaseOrder).where(PurchaseOrder.id == request.order_id)
            )
            if not result.scalar_one_or_none():
                await context.abort(grpc.StatusCode.NOT_FOUND, "Order not found")

            # Get payments
            result = await db.execute(
                select(Payment)
                .where(Payment.order_id == request.order_id)
                .order_by(Payment.payment_date)
            )
            payments = result.scalars().all()

            # Stream payments
            for payment in payments:
                yield payment_pb2.Payment(
                    id=payment.id,
                    order_id=payment.order_id,
                    payment_date=datetime_to_timestamp(payment.payment_date),
                    amount=payment.amount,
                    method=map_payment_method(payment.payment_method),
                    status=map_payment_status(payment.status),
                    reference=payment.reference or "",
                    notes=payment.notes or "",
                    created_at=datetime_to_timestamp(payment.created_at),
                )


# ============================================================================
# Contract Service
# ============================================================================


class ContractServicer(contract_pb2_grpc.ContractServiceServicer):
    """Contract service implementation"""

    async def GetContract(self, request, context: ServicerContext):
        """Get contract by ID or number"""
        async with async_session_maker() as db:
            if request.HasField("id"):
                result = await db.execute(
                    select(Contract).where(Contract.id == request.id)
                )
            else:
                result = await db.execute(
                    select(Contract).where(
                        Contract.contract_number == request.contract_number
                    )
                )

            contract = result.scalar_one_or_none()
            if not contract:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Contract not found")

            return contract_pb2.Contract(
                id=contract.id,
                contract_number=contract.contract_number,
                supplier_id=contract.supplier_id,
                material_id=contract.material_id,
                start_date=datetime_to_timestamp(contract.start_date),
                end_date=datetime_to_timestamp(contract.end_date),
                agreed_price=contract.agreed_price,
                min_quantity=contract.min_quantity,
                max_quantity=contract.max_quantity or 0.0,
                status=map_contract_status(contract.status),
                terms=contract.terms or "",
                created_at=datetime_to_timestamp(contract.created_at),
                updated_at=datetime_to_timestamp(contract.updated_at),
            )

    async def CreateContract(self, request, context: ServicerContext):
        """Create a new contract"""
        async with async_session_maker() as db:
            from erp_emulator.models.supplier import Supplier
            import time

            # Verify supplier exists
            supplier_result = await db.execute(
                select(Supplier).where(Supplier.id == request.supplier_id)
            )
            if not supplier_result.scalar_one_or_none():
                await context.abort(grpc.StatusCode.NOT_FOUND, "Supplier not found")

            # Verify material exists
            material_result = await db.execute(
                select(Material).where(Material.id == request.material_id)
            )
            if not material_result.scalar_one_or_none():
                await context.abort(grpc.StatusCode.NOT_FOUND, "Material not found")

            # Validate dates
            if request.end_date and request.end_date <= request.start_date:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "End date must be after start date",
                )

            # Generate contract number
            contract_number = f"CTR-{int(time.time())}"

            contract = Contract(
                supplier_id=request.supplier_id,
                material_id=request.material_id,
                contract_number=contract_number,
                start_date=datetime.fromtimestamp(request.start_date),
                end_date=(
                    datetime.fromtimestamp(request.end_date)
                    if request.end_date
                    else None
                ),
                agreed_price=request.agreed_price,
                min_quantity=request.min_quantity,
                max_quantity=request.max_quantity if request.max_quantity > 0 else None,
                status=str_to_contract_status(request.status),
                terms=request.terms or None,
            )
            db.add(contract)
            await db.commit()
            await db.refresh(contract)

            return contract_pb2.Contract(
                id=contract.id,
                contract_number=contract.contract_number,
                supplier_id=contract.supplier_id,
                material_id=contract.material_id,
                start_date=datetime_to_timestamp(contract.start_date),
                end_date=datetime_to_timestamp(contract.end_date),
                agreed_price=contract.agreed_price,
                min_quantity=contract.min_quantity,
                max_quantity=contract.max_quantity or 0.0,
                status=map_contract_status(contract.status),
                terms=contract.terms or "",
                created_at=datetime_to_timestamp(contract.created_at),
                updated_at=datetime_to_timestamp(contract.updated_at),
            )

    async def UpdateContract(self, request, context: ServicerContext):
        """Update contract"""
        async with async_session_maker() as db:
            result = await db.execute(select(Contract).where(Contract.id == request.id))
            contract = result.scalar_one_or_none()

            if not contract:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Contract not found")

            if request.end_date:
                if request.end_date <= datetime_to_timestamp(contract.start_date):
                    await context.abort(
                        grpc.StatusCode.INVALID_ARGUMENT,
                        "End date must be after start date",
                    )
                contract.end_date = datetime.fromtimestamp(request.end_date)
            if request.agreed_price:
                contract.agreed_price = request.agreed_price
            if request.min_quantity:
                contract.min_quantity = request.min_quantity
            if request.max_quantity:
                contract.max_quantity = (
                    request.max_quantity if request.max_quantity > 0 else None
                )
            if request.status:
                contract.status = str_to_contract_status(request.status)
            if request.terms:
                contract.terms = request.terms

            await db.commit()
            await db.refresh(contract)

            return contract_pb2.Contract(
                id=contract.id,
                contract_number=contract.contract_number,
                supplier_id=contract.supplier_id,
                material_id=contract.material_id,
                start_date=datetime_to_timestamp(contract.start_date),
                end_date=datetime_to_timestamp(contract.end_date),
                agreed_price=contract.agreed_price,
                min_quantity=contract.min_quantity,
                max_quantity=contract.max_quantity or 0.0,
                status=map_contract_status(contract.status),
                terms=contract.terms or "",
                created_at=datetime_to_timestamp(contract.created_at),
                updated_at=datetime_to_timestamp(contract.updated_at),
            )

    async def DeleteContract(self, request, context: ServicerContext):
        """Delete contract"""
        async with async_session_maker() as db:
            if request.HasField("id"):
                result = await db.execute(
                    select(Contract).where(Contract.id == request.id)
                )
            else:
                result = await db.execute(
                    select(Contract).where(
                        Contract.contract_number == request.contract_number
                    )
                )

            contract = result.scalar_one_or_none()
            if not contract:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Contract not found")

            await db.delete(contract)
            await db.commit()

            return common_pb2.Empty()

    async def ListContracts(self, request, context: ServicerContext):
        """List contracts with pagination"""
        async with async_session_maker() as db:
            query = select(Contract)

            # Apply filters
            if request.supplier_id:
                query = query.where(Contract.supplier_id == request.supplier_id)
            if request.material_id:
                query = query.where(Contract.material_id == request.material_id)
            if request.status:
                query = query.where(
                    Contract.status == str_to_contract_status(request.status)
                )

            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar()

            # Apply pagination
            page = request.pagination.page if request.HasField("pagination") else 1
            page_size = (
                request.pagination.page_size if request.HasField("pagination") else 20
            )

            query = (
                query.order_by(Contract.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            result = await db.execute(query)
            contracts = result.scalars().all()

            items = []
            for contract in contracts:
                items.append(
                    contract_pb2.Contract(
                        id=contract.id,
                        contract_number=contract.contract_number,
                        supplier_id=contract.supplier_id,
                        material_id=contract.material_id,
                        start_date=datetime_to_timestamp(contract.start_date),
                        end_date=datetime_to_timestamp(contract.end_date),
                        agreed_price=contract.agreed_price,
                        min_quantity=contract.min_quantity,
                        max_quantity=contract.max_quantity or 0.0,
                        status=map_contract_status(contract.status),
                        terms=contract.terms or "",
                        created_at=datetime_to_timestamp(contract.created_at),
                        updated_at=datetime_to_timestamp(contract.updated_at),
                    )
                )

            total_pages = (total + page_size - 1) // page_size if total > 0 else 0

            return contract_pb2.ListContractsResponse(
                items=items,
                pagination=common_pb2.PaginationResponse(
                    total=total,
                    page=page,
                    page_size=page_size,
                    total_pages=total_pages,
                ),
            )


# ============================================================================
# Admin Service
# ============================================================================


class AdminServicer(admin_pb2_grpc.AdminServiceServicer):
    """Admin service implementation"""

    async def SeedDatabase(self, request, context: ServicerContext):
        """Seed database with test data"""
        from erp_emulator.api.admin import seed_data

        async with async_session_maker() as db:
            try:
                stats_response = await seed_data(
                    db,
                    suppliers_count=request.suppliers_count or 18,
                    materials_count=request.materials_count or 24,
                    contracts_count=request.contracts_count or 35,
                    orders_count=request.orders_count or 220,
                )
            except ValueError as e:
                await context.abort(grpc.StatusCode.ALREADY_EXISTS, str(e))
                return

            return admin_pb2.SeedResponse(
                stats=admin_pb2.SeedStats(
                    suppliers=stats_response.suppliers,
                    materials=stats_response.materials,
                    contracts=stats_response.contracts,
                    orders=stats_response.orders,
                    order_items=stats_response.order_items,
                    payments=stats_response.payments,
                )
            )

    async def ResetDatabase(self, request, context: ServicerContext):
        """Reset database"""
        from erp_emulator.database import drop_all, init_db

        await drop_all()
        await init_db()

        return admin_pb2.ResetResponse(
            message="Database reset successfully. Use SeedDatabase to populate with data.",
            success=True,
        )

    async def GetDatabaseStats(self, request, context: ServicerContext):
        """Get database statistics"""
        async with async_session_maker() as db:
            suppliers_count = await db.execute(
                select(func.count()).select_from(Supplier)
            )
            materials_count = await db.execute(
                select(func.count()).select_from(Material)
            )
            contracts_count = await db.execute(
                select(func.count()).select_from(Contract)
            )
            orders_count = await db.execute(
                select(func.count()).select_from(PurchaseOrder)
            )
            order_items_count = await db.execute(
                select(func.count()).select_from(OrderItem)
            )
            payments_count = await db.execute(select(func.count()).select_from(Payment))

            stats = admin_pb2.SeedStats(
                suppliers=suppliers_count.scalar(),
                materials=materials_count.scalar(),
                contracts=contracts_count.scalar(),
                orders=orders_count.scalar(),
                order_items=order_items_count.scalar(),
                payments=payments_count.scalar(),
            )

            return admin_pb2.GetStatsResponse(stats=stats)


# ============================================================================
# Server
# ============================================================================


async def serve():
    """Start gRPC server"""
    server = grpc.aio.server()

    # Add servicers
    supplier_pb2_grpc.add_SupplierServiceServicer_to_server(SupplierServicer(), server)
    material_pb2_grpc.add_MaterialServiceServicer_to_server(MaterialServicer(), server)
    order_pb2_grpc.add_OrderServiceServicer_to_server(OrderServicer(), server)
    payment_pb2_grpc.add_PaymentServiceServicer_to_server(PaymentServicer(), server)
    contract_pb2_grpc.add_ContractServiceServicer_to_server(ContractServicer(), server)
    admin_pb2_grpc.add_AdminServiceServicer_to_server(AdminServicer(), server)

    # Enable reflection
    SERVICE_NAMES = (
        supplier_pb2.DESCRIPTOR.services_by_name["SupplierService"].full_name,
        material_pb2.DESCRIPTOR.services_by_name["MaterialService"].full_name,
        order_pb2.DESCRIPTOR.services_by_name["OrderService"].full_name,
        payment_pb2.DESCRIPTOR.services_by_name["PaymentService"].full_name,
        contract_pb2.DESCRIPTOR.services_by_name["ContractService"].full_name,
        admin_pb2.DESCRIPTOR.services_by_name["AdminService"].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)

    # Listen on port 6689
    server.add_insecure_port("[::]:6689")
    print("ERP gRPC server started on port 6689")

    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
