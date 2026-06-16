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
    print(f"{CYAN}{BOLD}1. ENTIDADES PRINCIPALES (POSTGRESQL & ORM){RESET}")
    print("-" * 70)
    
    entities = [
        {
            "name": "devices (IoT Edge Nodes)",
            "desc": "Representa los nodos hardware que ejecutan inferencia y monitorización.",
            "orm": "registry-service/app/models/orm.py -> Device",
            "fields": [
                ("id", "UUID (PK)", "Identificador único del dispositivo"),
                ("name", "TEXT", "Nombre descriptivo del dispositivo"),
                ("hardware_type", "TEXT", "Tipo de hardware (hailo8, hailo8l, rpi_ai_cam, rpi, jetson_orin_nano)"),
                ("description", "TEXT (Null)", "Detalles adicionales del dispositivo"),
                ("status", "TEXT", "Estado actual ('online' | 'offline')"),
                ("sensors", "ARRAY(String)", "Sensores configurados en el dispositivo"),
                ("actuators", "ARRAY(String)", "Actuadores configurados en el dispositivo"),
                ("others", "ARRAY(String)", "Otros parámetros o metadatos de hardware"),
                ("last_seen_at", "TIMESTAMPTZ", "Última vez que reportó actividad"),
                ("created_at", "TIMESTAMPTZ", "Fecha de creación del registro"),
            ]
        },
        {
            "name": "datasets (Conjuntos de Datos)",
            "desc": "Almacena información sobre los conjuntos de datos subidos para entrenamiento.",
            "orm": "registry-service/app/models/orm.py -> Dataset",
            "fields": [
                ("id", "UUID (PK)", "Identificador único"),
                ("name", "TEXT", "Nombre del dataset"),
                ("description", "TEXT (Null)", "Descripción o notas"),
                ("object_key", "TEXT", "Ruta en MinIO de la carpeta o archivo principal"),
                ("sha256", "TEXT", "Hash de validación"),
                ("size_bytes", "BIGINT", "Tamaño del archivo"),
                ("meta_info", "JSON (Null)", "Metadatos adicionales del dataset"),
                ("created_at", "TIMESTAMPTZ", "Fecha de creación"),
            ]
        },
        {
            "name": "models (Modelos de IA)",
            "desc": "Contiene metadatos tanto de modelos PyTorch originales (.pt) como de los compilados (.hef).",
            "orm": "registry-service/app/models/orm.py -> Model",
            "fields": [
                ("id", "UUID (PK)", "Identificador único del modelo"),
                ("name", "TEXT", "Nombre descriptivo del modelo"),
                ("description", "TEXT (Null)", "Notas del modelo"),
                ("source_key", "TEXT", "Ruta del modelo original en MinIO (models/<id>/source.pt)"),
                ("source_sha256", "TEXT", "SHA256 del modelo original"),
                ("compiled_key", "TEXT (Null)", "Ruta del binario compilado en MinIO (compiled/<id>/model.hef)"),
                ("compiled_sha256", "TEXT (Null)", "SHA256 del binario compilado"),
                ("hardware_type", "TEXT (Null)", "Arquitectura para la que está compilado"),
                ("compile_status", "TEXT", "Estado ('pending' | 'compiling' | 'ready' | 'failed')"),
                ("compile_error", "TEXT (Null)", "Mensaje de error si la compilación falla"),
                ("dataset_id", "UUID (FK, Null)", "Dataset asociado para el entrenamiento/compilación"),
                ("base_architecture", "TEXT (Null)", "Arquitectura YOLO base utilizada (ej. 'yolov8n')"),
                ("epochs", "INT (Null)", "Número de épocas entrenadas"),
                ("input_size", "TEXT (Null)", "Resolución de entrada (ej. '640x640')"),
                ("batch_size", "INT (Null)", "Tamaño de lote utilizado"),
                ("created_at", "TIMESTAMPTZ", "Fecha de registro"),
            ]
        },
        {
            "name": "scripts (Scripts de Inferencia)",
            "desc": "Scripts de procesamiento de inferencia.",
            "orm": "registry-service/app/models/orm.py -> Script",
            "fields": [
                ("id", "UUID (PK)", "Identificador único"),
                ("name", "TEXT", "Nombre del script"),
                ("description", "TEXT (Null)", "Notas o detalles del script"),
                ("script_key", "TEXT", "Ruta del script en MinIO (scripts/<id>/script.py)"),
                ("script_sha256", "TEXT", "SHA256 de verificación del script"),
                ("language", "TEXT", "Lenguaje del script (python, c++, java)"),
                ("created_at", "TIMESTAMPTZ", "Fecha de creación"),
            ]
        },
        {
            "name": "deployments (Despliegues)",
            "desc": "Tabla de unión que orquesta el despliegue de un modelo y un script en un dispositivo edge.",
            "orm": "edge-connector-service/app/models/orm.py -> Deployment",
            "fields": [
                ("id", "UUID (PK)", "Identificador único del despliegue"),
                ("device_id", "UUID (FK)", "Dispositivo de destino (CASCADE)"),
                ("model_id", "UUID (FK)", "Modelo de IA a desplegar (CASCADE)"),
                ("script_id", "UUID (FK)", "Script a ejecutar (CASCADE)"),
                ("status", "TEXT", "Estado del despliegue ('pending' | 'sent' | 'running' | 'failed')"),
                ("sent_at", "TIMESTAMPTZ (Null)", "Marca de tiempo del envío MQTT al dispositivo"),
                ("running_at", "TIMESTAMPTZ (Null)", "Confirmación de ejecución del Edge"),
                ("error_msg", "TEXT (Null)", "Error reportado por el dispositivo"),
                ("created_at", "TIMESTAMPTZ", "Fecha de creación del despliegue"),
            ]
        }
    ]

    for ent in entities:
        print(f"\n{GREEN}{BOLD}■ {ent['name']}{RESET}")
        print(f"  {BOLD}Descripción:{RESET} {ent['desc']}")
        print(f"  {BOLD}Definición ORM:{RESET} {BLUE}{ent['orm']}{RESET}")
        print(f"  {BOLD}Atributos / Columnas:{RESET}")
        for field, ftype, fdesc in ent["fields"]:
            print(f"    - {YELLOW}{field:<20}{RESET} {ftype:<18} | {fdesc}")
        print("-" * 70)

def print_minio_mapping():
    print(f"\n{CYAN}{BOLD}2. ALMACENAMIENTO DE FICHEROS (MINIO OBJECT STORAGE){RESET}")
    print("-" * 70)
    mappings = [
        ("Datasets originales/versionados", "datasets/<dataset_id>/<version>/<file>"),
        ("Modelos originales PyTorch (.pt)", "models/<model_id>/source.pt"),
        ("Modelos compilados (.hef, etc.)", "compiled/<model_id>/model.hef"),
        ("Scripts de inferencia (.py)", "scripts/<script_id>/script.py")
    ]
    for key, path in mappings:
        print(f"  * {BOLD}{key:<35}{RESET} -> {GREEN}{path}{RESET}")
    print("-" * 70)

def print_grpc_contracts():
    print(f"\n{CYAN}{BOLD}3. CONTRATOS gRPC (COMUNICACIÓN ENTRE SERVICIOS){RESET}")
    print("-" * 70)
    protos = [
        ("device.proto", "Maneja registro y monitorización básica de dispositivos edge.", "aura.device.v1.DeviceService"),
        ("ai.proto", "Maneja el registro, subida y asociación de modelos y datasets.", "aura.ai.v1.AIService"),
        ("script.proto", "CRUD de scripts de pre/postprocesamiento en edge.", "aura.script.v1.ScriptService"),
        ("deployment.proto", "Gestión y orquestación de despliegues a dispositivos edge.", "aura.deployment.v1.DeploymentService"),
        ("compilation.proto", "Lanza tareas de compilación y entrenamiento de modelos YOLO.", "aura.compilation.v1.CompilationService"),
        ("monitoring.proto", "Recupera métricas de CPU/RAM y resultados de inferencia en tiempo real.", "aura.monitoring.v1.MonitoringService")
    ]
    for file, desc, package in protos:
        print(f"  * {YELLOW}{file:<20}{RESET} [{BLUE}{package}{RESET}]")
        print(f"    {desc}")
    print("-" * 70)

def print_raw_sql():
    root = get_project_root()
    sql_path = root / "infra" / "postgres" / "init.sql"
    
    print(f"\n{CYAN}{BOLD}4. ESQUEMA SQL DETALLADO (infra/postgres/init.sql){RESET}")
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
            print(f"{RED}Error leyendo el archivo SQL: {e}{RESET}")
    else:
        print(f"{RED}Archivo SQL no encontrado en {sql_path}{RESET}")
    print("-" * 70)

def download_diagram_png(output_path: Path):
    """Downloads the Mermaid diagram as a PNG using the mermaid.ink API."""
    print(f"\n{CYAN}{BOLD}GENERANDO IMAGEN DEL DIAGRAMA (via mermaid.ink)...{RESET}")
    print("-" * 70)
    
    try:
        # URL-safe Base64 encode the mermaid code
        graph_bytes = MERMAID_DIAGRAM_CODE.encode("utf-8")
        base64_bytes = base64.urlsafe_b64encode(graph_bytes)
        base64_string = base64_bytes.decode("ascii")
        
        url = f"https://mermaid.ink/img/{base64_string}"
        
        print(f"Estableciendo conexión con la API de Mermaid y descargando imagen...")
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            with open(output_path, "wb") as f:
                f.write(response.read())
        print(f"{GREEN}{BOLD}¡Éxito! Imagen del diagrama guardada en:{RESET} {output_path.resolve()}")
    except urllib.error.URLError as e:
        print(f"{RED}Error de red al intentar descargar la imagen: {e.reason}{RESET}")
        print("Asegúrate de tener conexión a Internet para usar el generador de imágenes.")
    except Exception as e:
        print(f"{RED}Error inesperado generando la imagen PNG: {e}{RESET}")
    print("-" * 70)

def print_diagram():
    print(f"{CYAN}{BOLD}DIAGRAMA DE ENTIDAD-RELACIÓN (ASCII & MERMAID){RESET}")
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
    print(f"{YELLOW}{BOLD}Diagrama de Relaciones Conceptual:{RESET}")
    print(ascii_diagram)
    print("-" * 70)

    print(f"{GREEN}{BOLD}Código Mermaid.js (Copiar para Markdown/Mermaid Live Editor):{RESET}")
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
        print(f"{BLUE}Diagrama exportado correctamente a:{RESET} {diagram_path.resolve()}")
    except Exception as e:
        print(f"{RED}No se pudo escribir el diagrama .mermaid en disco: {e}{RESET}")
    
    # Save .png using mermaid.ink
    png_path = docs_dir / "model_diagram.png"
    download_diagram_png(png_path)

def main():
    # En Windows, puede que necesitemos activar los códigos de escape ANSI
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
            print(f"Uso: python {sys.argv[0]} [opción]")
            print("Opciones:")
            print("  --entities  Imprime sólo las tablas relacionales y su mapeo ORM")
            print("  --minio     Imprime sólo la estructura de claves de MinIO")
            print("  --grpc      Imprime sólo las definiciones de servicios gRPC")
            print("  --sql       Imprime el archivo SQL de inicialización crudo")
            print("  --diagram   Muestra el diagrama ASCII, código Mermaid y genera/descarga la imagen PNG")
            print("  --png       Descarga la imagen del diagrama como PNG en docs/")
            print("  (sin args)  Imprime todo el modelo de información y genera los diagramas (.mermaid y .png)")
        else:
            print(f"{RED}Opción no reconocida: {sys.argv[1]}{RESET}")
            print("Usa --help para ver las opciones disponibles.")
    else:
        print_entities()
        print_minio_mapping()
        print_grpc_contracts()
        print_raw_sql()
        print_diagram()

if __name__ == "__main__":
    main()
