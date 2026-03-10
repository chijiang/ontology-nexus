import os
import subprocess
import glob
import sys


def run_protoc():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    proto_files = glob.glob(os.path.join(base_dir, "*.proto"))

    # Run protoc
    cmd = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"-I{base_dir}",
        f"--python_out={base_dir}",
        f"--grpc_python_out={base_dir}",
        f"--pyi_out={base_dir}",
    ] + proto_files

    print("Running protoc...")
    subprocess.run(cmd, check=True)


def fix_imports():
    """Fix relative imports in generated Python files"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    pb2_files = glob.glob(os.path.join(base_dir, "*_pb2*.py"))

    # Get base names of generated modules (without _pb2.py)
    # E.g. work_ticket_pb2.py -> work_ticket
    modules = set()
    for f in pb2_files:
        basename = os.path.basename(f)
        if basename.endswith("_pb2.py"):
            modules.add(basename.replace("_pb2.py", ""))

    print(f"Fixing imports for modules: {modules}")

    for f in pb2_files:
        with open(f, "r") as file:
            content = file.read()

        modified = False
        for mod in modules:
            # Fix imports like `import common_pb2 as common__pb2`
            target = f"import {mod}_pb2"
            replacement = f"from . import {mod}_pb2"
            if target in content:
                content = content.replace(target, replacement)
                modified = True

        if modified:
            with open(f, "w") as file:
                file.write(content)
            print(f"Fixed imports in {os.path.basename(f)}")


if __name__ == "__main__":
    run_protoc()
    fix_imports()
    print("Protobuf code generation completed successfully.")
