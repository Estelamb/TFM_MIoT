import glob
import os
import re
import subprocess
import sys

def main():
    print("Installing/upgrading grpcio-tools...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "grpcio-tools"])

    print("Compiling proto files...")
    # Find all .proto files in shared/proto
    proto_files = glob.glob("shared/proto/*.proto")
    if not proto_files:
        print("No proto files found!")
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "grpc_tools.protoc",
        "-I", "shared/proto",
        "--python_out=shared/proto_gen",
        "--grpc_python_out=shared/proto_gen"
    ] + proto_files

    print("Running command:", " ".join(cmd))
    subprocess.check_call(cmd)

    print("Fixing generated imports...")
    grpc_files = glob.glob("shared/proto_gen/*_pb2_grpc.py")
    for filepath in grpc_files:
        print(f"Fixing imports in: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Replace 'import xxx_pb2 as xxx__pb2' with 'from shared.proto_gen import xxx_pb2 as xxx__pb2'
        # and 'import xxx_pb2' with 'from shared.proto_gen import xxx_pb2'
        new_content = re.sub(r"^import\s+([a-zA-Z0-9_]+_pb2)", r"from shared.proto_gen import \1", content, flags=re.MULTILINE)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)

    print("Proto compilation successful!")

if __name__ == "__main__":
    main()
