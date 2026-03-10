"""ERP Emulator gRPC Service

gRPC protocol buffers and server implementation.
"""

# Import generated protobuf modules
from grpc_interface import (
    common_pb2,
    common_pb2_grpc,
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
)

__all__ = [
    "common_pb2",
    "common_pb2_grpc",
    "supplier_pb2",
    "supplier_pb2_grpc",
    "material_pb2",
    "material_pb2_grpc",
    "order_pb2",
    "order_pb2_grpc",
    "payment_pb2",
    "payment_pb2_grpc",
    "contract_pb2",
    "contract_pb2_grpc",
    "admin_pb2",
    "admin_pb2_grpc",
]
