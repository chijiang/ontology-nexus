#!/usr/bin/env python3
"""Generate Python protobuf code from .proto files"""

import subprocess
import sys
from pathlib import Path

# Get the grpc directory
grpc_dir = Path(__file__).parent
proto_files = list(grpc_dir.glob("*.proto"))

print(f"Found {len(proto_files)} proto files:")
for proto in proto_files:
    print(f"  - {proto.name}")

# Generate command
# For grpcio-tools >= 1.0
command = [
    sys.executable,
    "-m",
    "grpc_tools.protoc",
    f"--proto_path={grpc_dir}",
    f"--python_out={grpc_dir}",
    f"--grpc_python_out={grpc_dir}",
] + [str(p) for p in proto_files]

print("\nRunning command:")
print(" ".join(command))

try:
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    print("\n✓ Protobuf code generated successfully!")
    print("\nGenerated files:")
    for py_file in grpc_dir.glob("*_pb2*.py"):
        print(f"  - {py_file.name}")
except subprocess.CalledProcessError as e:
    print(f"\n✗ Error generating protobuf code:")
    print(f"  Return code: {e.returncode}")
    print(f"  Stdout: {e.stdout}")
    print(f"  Stderr: {e.stderr}")
    sys.exit(1)
except FileNotFoundError:
    print("\n✗ grpcio-tools not installed.")
    print("  Install with: uv add grpcio-tools")
    sys.exit(1)
