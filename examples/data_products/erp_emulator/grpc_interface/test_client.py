#!/usr/bin/env python3
"""Simple test client for ERP gRPC server"""

import grpc
from datetime import datetime

# Import generated protobuf classes
from grpc import (
    admin_pb2,
    admin_pb2_grpc,
    supplier_pb2,
    supplier_pb2_grpc,
    common_pb2,
)


def test_admin_get_stats():
    """Test getting database statistics via gRPC"""
    with grpc.insecure_channel("localhost:6689") as channel:
        stub = admin_pb2_grpc.AdminServiceStub(channel)

        # Get stats
        response = stub.GetDatabaseStats(common_pb2.Empty())
        print("Database Stats:")
        print(f"  Suppliers: {response.stats.suppliers}")
        print(f"  Materials: {response.stats.materials}")
        print(f"  Contracts: {response.stats.contracts}")
        print(f"  Orders: {response.stats.orders}")
        print(f"  Order Items: {response.stats.order_items}")
        print(f"  Payments: {response.stats.payments}")


def test_supplier_list():
    """Test listing suppliers via gRPC"""
    with grpc.insecure_channel("localhost:6689") as channel:
        stub = supplier_pb2_grpc.SupplierServiceStub(channel)

        # List suppliers
        pagination = common_pb2.PaginationRequest(page=1, page_size=5)
        request = supplier_pb2.ListSuppliersRequest(pagination=pagination)

        response = stub.ListSuppliers(request)
        print("\nSuppliers:")
        print(f"  Total: {response.pagination.total}")
        print(f"  Page: {response.pagination.page}/{response.pagination.total_pages}")
        for supplier in response.items[:3]:  # Show first 3
            print(f"  - [{supplier.code}] {supplier.name}")


def test_supplier_get():
    """Test getting a specific supplier via gRPC"""
    with grpc.insecure_channel("localhost:6689") as channel:
        stub = supplier_pb2_grpc.SupplierServiceStub(channel)

        # Get supplier by ID
        request = supplier_pb2.GetSupplierRequest(id=1)
        supplier = stub.GetSupplier(request)

        print("\nSupplier Details:")
        print(f"  ID: {supplier.id}")
        print(f"  Name: {supplier.name}")
        print(f"  Code: {supplier.code}")
        print(f"  Email: {supplier.email}")
        print(f"  Phone: {supplier.phone}")


def test_supplier_create():
    """Test creating a supplier via gRPC"""
    with grpc.insecure_channel("localhost:6689") as channel:
        stub = supplier_pb2_grpc.SupplierServiceStub(channel)

        # Create supplier
        request = supplier_pb2.CreateSupplierRequest(
            name="gRPC Test Supplier",
            code="GRPC-002",
            contact_person="Test Contact",
            email="test@grpc.com",
            phone="+1-555-0000",
            credit_rating=common_pb2.CREDIT_RATING_A,
            status=common_pb2.STATUS_ACTIVE,
        )

        supplier = stub.CreateSupplier(request)

        print("\nCreated Supplier:")
        print(f"  ID: {supplier.id}")
        print(f"  Name: {supplier.name}")
        print(f"  Code: {supplier.code}")


if __name__ == "__main__":
    print("Testing ERP gRPC Server on localhost:6689\n")
    print("=" * 50)

    try:
        test_admin_get_stats()
        test_supplier_list()
        test_supplier_get()
        test_supplier_create()

        print("\n" + "=" * 50)
        print("All tests passed!")
    except grpc.RpcError as e:
        print(f"\ngRPC Error: {e.code()} - {e.details()}")
    except Exception as e:
        print(f"\nError: {e}")
