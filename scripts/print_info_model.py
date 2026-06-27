#!/usr/bin/env python3
import os
import sys
import base64
import urllib.request
import urllib.error
from pathlib import Path

# ANSI colors for styling
BLUE = "\033[38;5;39m"
CYAN = "\033[38;5;86m"
GREEN = "\033[38;5;78m"
YELLOW = "\033[38;5;221m"
MAGENTA = "\033[38;5;213m"
RED = "\033[38;5;196m"
BOLD = "\033[1m"
RESET = "\033[0m"

MERMAID_DIAGRAM_CODE = """%%{init: {
  "theme": "neutral",
  "themeVariables": {
    "fontFamily": "Segoe UI, system-ui, sans-serif",
    "fontSize": "13px"
  }
}}%%
erDiagram
    devices {
        uuid id PK
        string name
        string hardware_type
        string description
        string status
        string_array sensors
        string_array actuators
        string_array others
        timestamp last_seen_at
        timestamp created_at
    }
    datasets {
        uuid id PK
        string name
        string description
        string object_key
        string sha256
        int size_bytes
        json meta_info
        timestamp created_at
    }
    models {
        uuid id PK
        string name
        string description
        string source_key
        string source_sha256
        string compiled_key
        string compiled_sha256
        string hardware_type
        string compile_status
        string compile_error
        uuid dataset_id FK
        string base_architecture
        int epochs
        string input_size
        int batch_size
        timestamp created_at
    }
    scripts {
        uuid id PK
        string name
        string description
        string script_key
        string script_sha256
        string language
        timestamp created_at
    }
    deployments {
        uuid id PK
        uuid device_id FK
        uuid model_id FK
        uuid script_id FK
        string status
        timestamp sent_at
        timestamp running_at
        string error_msg
        timestamp created_at
    }

    datasets ||--o{ models : "used by"
    devices ||--o{ deployments : "target"
    models ||--o{ deployments : "deployed"
    scripts ||--o{ deployments : "executed by"
"""

def get_project_root() -> Path:
    # This script is located in root/scripts/print_info_model.py
    return Path(__file__).resolve().parent.parent

def print_header():
    try:
        # Try to reconfigure stdout to UTF-8 to handle block characters on Windows
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    
    # Simple header as requested (no large ASCII art)
    print(f"\n{BLUE}{BOLD}=== AURA PLATFORM - INFORMATION MODEL ==={RESET}\n")

def print_entities():
    print(f"{CYAN}{BOLD}1. MAIN ENTITIES (POSTGRESQL & ORM){RESET}")
    print("-" * 70)
    
    entities = [
        {
            "name": "devices (IoT Edge Nodes)",
            "desc": "Represents hardware nodes executing inference and monitoring.",
            "orm": "registry-service/app/models/orm.py -> Device",
            "fields": [
                ("id", "UUID (PK)", "Unique device identifier"),
                ("name", "TEXT", "Descriptive name of the device"),
                ("hardware_type", "TEXT", "Hardware type (hailo8, hailo8l, rpi_ai_cam, rpi, jetson_orin_nano)"),
                ("description", "TEXT (Null)", "Additional details of the device"),
                ("status", "TEXT", "Current status ('online' | 'offline')"),
                ("sensors", "ARRAY(String)", "Sensors configured on the device"),
                ("actuators", "ARRAY(String)", "Actuators configured on the device"),
                ("others", "ARRAY(String)", "Other hardware parameters or metadata"),
                ("last_seen_at", "TIMESTAMPTZ", "Last time activity was reported"),
                ("created_at", "TIMESTAMPTZ", "Creation date of the record"),
            ]
        },
        {
            "name": "datasets (Datasets)",
            "desc": "Stores information about uploaded datasets for training.",
            "orm": "registry-service/app/models/orm.py -> Dataset",
            "fields": [
                ("id", "UUID (PK)", "Unique identifier"),
                ("name", "TEXT", "Dataset name"),
                ("description", "TEXT (Null)", "Description or notes"),
                ("object_key", "TEXT", "MinIO path of the main folder or file"),
                ("sha256", "TEXT", "Validation hash"),
                ("size_bytes", "BIGINT", "File size"),
                ("meta_info", "JSON (Null)", "Additional dataset metadata"),
                ("created_at", "TIMESTAMPTZ", "Creation date"),
            ]
        },
        {
            "name": "models (AI Models)",
            "desc": "Contains metadata of both original PyTorch models (.pt) and compiled models (.hef).",
            "orm": "registry-service/app/models/orm.py -> Model",
            "fields": [
                ("id", "UUID (PK)", "Unique model identifier"),
                ("name", "TEXT", "Descriptive name of the model"),
                ("description", "TEXT (Null)", "Model notes"),
                ("source_key", "TEXT", "Path of the original model in MinIO (models/<id>/source.pt)"),
                ("source_sha256", "TEXT", "SHA256 of the original model"),
                ("compiled_key", "TEXT (Null)", "Path of the compiled binary in MinIO (compiled/<id>/model.hef)"),
                ("compiled_sha256", "TEXT (Null)", "SHA256 of the compiled binary"),
                ("hardware_type", "TEXT (Null)", "Architecture for which it is compiled"),
                ("compile_status", "TEXT", "Status ('pending' | 'compiling' | 'ready' | 'failed')"),
                ("compile_error", "TEXT (Null)", "Error message if compilation fails"),
                ("dataset_id", "UUID (FK, Null)", "Associated dataset for training/compilation"),
                ("base_architecture", "TEXT (Null)", "Base YOLO architecture used (e.g. 'yolov8n')"),
                ("epochs", "INT (Null)", "Number of trained epochs"),
                ("input_size", "TEXT (Null)", "Input resolution (e.g. '640x640')"),
                ("batch_size", "INT (Null)", "Batch size used"),
                ("created_at", "TIMESTAMPTZ", "Registration date"),
            ]
        },
        {
            "name": "scripts (Inference Scripts)",
            "desc": "Inference processing scripts.",
            "orm": "registry-service/app/models/orm.py -> Script",
            "fields": [
                ("id", "UUID (PK)", "Unique identifier"),
                ("name", "TEXT", "Script name"),
                ("description", "TEXT (Null)", "Script notes or details"),
                ("script_key", "TEXT", "Path of the script in MinIO (scripts/<id>/script.py)"),
                ("script_sha256", "TEXT", "Verification SHA256 of the script"),
                ("language", "TEXT", "Script language (python, c++, java)"),
                ("created_at", "TIMESTAMPTZ", "Creation date"),
            ]
        },
        {
            "name": "deployments (Deployments)",
            "desc": "Join table that orchestrates the deployment of a model and a script on an edge device.",
            "orm": "edge-connector-service/app/models/orm.py -> Deployment",
            "fields": [
                ("id", "UUID (PK)", "Unique deployment identifier"),
                ("device_id", "UUID (FK)", "Target device (CASCADE)"),
                ("model_id", "UUID (FK)", "AI Model to deploy (CASCADE)"),
                ("script_id", "UUID (FK)", "Script to execute (CASCADE)"),
                ("status", "TEXT", "Deployment status ('pending' | 'sent' | 'running' | 'failed')"),
                ("sent_at", "TIMESTAMPTZ (Null)", "Timestamp of MQTT send to device"),
                ("running_at", "TIMESTAMPTZ (Null)", "Edge execution confirmation"),
                ("error_msg", "TEXT (Null)", "Error reported by the device"),
                ("created_at", "TIMESTAMPTZ", "Deployment creation date"),
            ]
        }
    ]

    for ent in entities:
        print(f"\n{GREEN}{BOLD}■ {ent['name']}{RESET}")
        print(f"  {BOLD}Description:{RESET} {ent['desc']}")
        print(f"  {BOLD}ORM Definition:{RESET} {BLUE}{ent['orm']}{RESET}")
        print(f"  {BOLD}Attributes / Columns:{RESET}")
        for field, ftype, fdesc in ent["fields"]:
            print(f"    - {YELLOW}{field:<20}{RESET} {ftype:<18} | {fdesc}")
        print("-" * 70)

def print_minio_mapping():
    print(f"\n{CYAN}{BOLD}2. FILE STORAGE (MINIO OBJECT STORAGE){RESET}")
    print("-" * 70)
    mappings = [
        ("Original/versioned datasets", "datasets/<dataset_id>/<version>/<file>"),
        ("Original PyTorch models (.pt)", "models/<model_id>/source.pt"),
        ("Compiled models (.hef, etc.)", "compiled/<model_id>/model.hef"),
        ("Inference scripts (.py)", "scripts/<script_id>/script.py")
    ]
    for key, path in mappings:
        print(f"  * {BOLD}{key:<35}{RESET} -> {GREEN}{path}{RESET}")
    print("-" * 70)

def print_grpc_contracts():
    print(f"\n{CYAN}{BOLD}3. gRPC CONTRACTS (COMMUNICATION BETWEEN SERVICES){RESET}")
    print("-" * 70)
    protos = [
        ("device.proto", "Manages registration and basic monitoring of edge devices.", "aura.device.v1.DeviceService"),
        ("ai.proto", "Manages registration, upload, and association of models and datasets.", "aura.ai.v1.AIService"),
        ("script.proto", "CRUD of pre/postprocessing scripts on edge.", "aura.script.v1.ScriptService"),
        ("deployment.proto", "Management and orchestration of deployments to edge devices.", "aura.deployment.v1.DeploymentService"),
        ("compilation.proto", "Launches compilation and training tasks for YOLO models.", "aura.compilation.v1.CompilationService"),
        ("monitoring.proto", "Retrieves CPU/RAM metrics and real-time inference results.", "aura.monitoring.v1.MonitoringService")
    ]
    for file, desc, package in protos:
        print(f"  * {YELLOW}{file:<20}{RESET} [{BLUE}{package}{RESET}]")
        print(f"    {desc}")
    print("-" * 70)

def print_raw_sql():
    root = get_project_root()
    sql_path = root / "infra" / "postgres" / "init.sql"
    
    print(f"\n{CYAN}{BOLD}4. DETAILED SQL SCHEMA (infra/postgres/init.sql){RESET}")
    print("-" * 70)
    
    if sql_path.exists():
        try:
            with open(sql_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Highlight comments and SQL statements slightly
            lines = content.splitlines()
            for line in lines:
                if line.strip().startswith("--"):
                    print(f"\033[90m{line}{RESET}")
                elif "CREATE TABLE" in line or "CREATE INDEX" in line:
                    print(f"{BLUE}{BOLD}{line}{RESET}")
                elif "REFERENCES" in line or "PRIMARY KEY" in line or "FOREIGN KEY" in line:
                    print(f"{YELLOW}{line}{RESET}")
                else:
                    print(line)
        except Exception as e:
            print(f"{RED}Error reading SQL file: {e}{RESET}")
    else:
        print(f"{RED}SQL file not found at {sql_path}{RESET}")
    print("-" * 70)

def download_diagram_png(output_path: Path):
    """Downloads the Mermaid diagram as a PNG using the mermaid.ink API."""
    print(f"\n{CYAN}{BOLD}GENERATING DIAGRAM IMAGE (via mermaid.ink)...{RESET}")
    print("-" * 70)
    
    try:
        # URL-safe Base64 encode the mermaid code
        graph_bytes = MERMAID_DIAGRAM_CODE.encode("utf-8")
        base64_bytes = base64.urlsafe_b64encode(graph_bytes)
        base64_string = base64_bytes.decode("ascii")
        
        url = f"https://mermaid.ink/img/{base64_string}"
        
        print(f"Connecting to Mermaid API and downloading image...")
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            with open(output_path, "wb") as f:
                f.write(response.read())
        print(f"{GREEN}{BOLD}Success! Diagram image saved at:{RESET} {output_path.resolve()}")
    except urllib.error.URLError as e:
        print(f"{RED}Network error trying to download image: {e.reason}{RESET}")
        print("Ensure you have an internet connection to use the image generator.")
    except Exception as e:
        print(f"{RED}Unexpected error generating PNG image: {e}{RESET}")
    print("-" * 70)

def print_diagram():
    print(f"{CYAN}{BOLD}ENTITY-RELATIONSHIP DIAGRAM (ASCII & MERMAID){RESET}")
    print("-" * 70)
    
    ascii_diagram = """
  +------------------+  1:N (used by)  +------------------+         +------------------+
  |      models      | <-------------- |     datasets     |         |     scripts      |
  +--------┬---------+                 +------------------+         +--------┬---------+
           |                                                                 |
           |                                                                 | 1:N (executed by)
           |                                                                 v
           |                           +------------------+         +------------------+
           |                           |     devices      | ------> |   deployments    |
           |                           +------------------+   1:N   +----^-------------+
           |                                                        (target) |
           |                                                                 |
           +-----------------------------------------------------------------+ 1:N (deployed)
"""
    print(f"{YELLOW}{BOLD}Conceptual Relationship Diagram:{RESET}")
    print(ascii_diagram)
    print("-" * 70)

    print(f"{GREEN}{BOLD}Mermaid.js Code (Copy for Markdown/Mermaid Live Editor):{RESET}")
    print(MERMAID_DIAGRAM_CODE)
    print("-" * 70)
    
    # Save the diagram code in the docs/ directory
    root = get_project_root()
    docs_dir = root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    # Save .mermaid
    diagram_path = docs_dir / "model_diagram.mermaid"
    try:
        with open(diagram_path, "w", encoding="utf-8") as f:
            f.write(MERMAID_DIAGRAM_CODE)
        print(f"{BLUE}Diagram successfully exported to:{RESET} {diagram_path.resolve()}")
    except Exception as e:
        print(f"{RED}Could not write .mermaid diagram to disk: {e}{RESET}")
    
    # Save .png using mermaid.ink
    png_path = docs_dir / "model_diagram.png"
    download_diagram_png(png_path)

def main():
    # On Windows, we might need to enable ANSI escape codes
    if os.name == 'nt':
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    print_header()
    
    root = get_project_root()
    png_path = root / "docs" / "model_diagram.png"
    
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == "--entities":
            print_entities()
        elif arg == "--minio":
            print_minio_mapping()
        elif arg == "--grpc":
            print_grpc_contracts()
        elif arg == "--sql":
            print_raw_sql()
        elif arg == "--diagram":
            print_diagram()
        elif arg == "--png":
            download_diagram_png(png_path)
        elif arg == "--help":
            print(f"Usage: python {sys.argv[0]} [option]")
            print("Options:")
            print("  --entities  Prints only the relational tables and their ORM mapping")
            print("  --minio     Prints only the MinIO key structure")
            print("  --grpc      Prints only the gRPC service definitions")
            print("  --sql       Prints the raw initialization SQL file")
            print("  --diagram   Shows the ASCII diagram, Mermaid code, and generates/downloads the PNG image")
            print("  --png       Downloads the diagram image as PNG in docs/")
            print("  (without args)  Prints the entire information model and generates the diagrams (.mermaid and .png)")
        else:
            print(f"{RED}Unrecognized option: {sys.argv[1]}{RESET}")
            print("Use --help to see available options.")
    else:
        print_entities()
        print_minio_mapping()
        print_grpc_contracts()
        print_raw_sql()
        print_diagram()

if __name__ == "__main__":
    main()
