#!/usr/bin/env python3
"""Fix imports in generated protobuf files"""

import re
from pathlib import Path

# Get the grpc directory
grpc_dir = Path(__file__).parent

# Fix import statements in generated _pb2.py files
for pb2_file in grpc_dir.glob("*_pb2.py"):
    content = pb2_file.read_text()

    # Fix imports to use the module prefix
    content = re.sub(
        r'^import (\w+_pb2) as',
        r'from erp_emulator.grpc import \1 as',
        content,
        flags=re.MULTILINE
    )

    pb2_file.write_text(content)
    print(f"Fixed imports in {pb2_file.name}")

# Fix import statements in generated _pb2_grpc.py files
for pb2_grpc_file in grpc_dir.glob("*_pb2_grpc.py"):
    content = pb2_grpc_file.read_text()

    # Fix imports to use the module prefix
    content = re.sub(
        r'^import (\w+_pb2) as',
        r'from erp_emulator.grpc import \1 as',
        content,
        flags=re.MULTILINE
    )

    pb2_grpc_file.write_text(content)
    print(f"Fixed imports in {pb2_grpc_file.name}")

print("All imports fixed!")
