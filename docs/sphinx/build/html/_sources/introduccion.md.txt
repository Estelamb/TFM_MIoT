# Introducción al Proyecto AURA

Bienvenido a la documentación oficial de **AURA Platform**, una plataforma integral y de extremo a extremo diseñada para simplificar y automatizar el ciclo de vida del despliegue de modelos de Inteligencia Artificial y Visión por Computador en dispositivos del Internet de las Cosas (IoT) y dispositivos perimetrales (Edge).

## ¿Qué es AURA?

AURA proporciona una infraestructura robusta y escalable que permite a ingenieros de ML, desarrolladores e integradores gestionar y orquestar flujos de trabajo de Edge AI con total facilidad. La plataforma cubre las siguientes fases clave:

1. **Carga y Registro**: Registro centralizado de modelos de aprendizaje automático (formatos estándar como PyTorch `.pt`) y scripts personalizados de inferencia en Python.
2. **Compilación y Optimización**: Compilación automática de los modelos para arquitecturas de hardware específicas (como Hailo-8, IMX500, TFLite o TensorRT) utilizando el servicio de MLOps.
3. **Despliegue Remoto (Over-the-Air)**: Distribución del modelo optimizado y su correspondiente script de inferencia a múltiples dispositivos perimetrales a través de una red segura basada en el protocolo MQTT.
4. **Monitorización y Telemetría**: Seguimiento continuo del rendimiento del hardware (uso de CPU, RAM, temperatura) y de los resultados de inferencia en tiempo real a través de paneles visuales.

---

## Arquitectura General

El ecosistema de AURA se divide en dos grandes bloques: la **Plataforma en la Nube/Servidor** y el **Runtime de Edge**.

```
                           +--------------------------------------+
                           |          Interfaz Frontend           |
                           |            (Next.js App)             |
                           +------------------+-------------------+
                                              | HTTP / JWT
                                              v
                           +------------------+-------------------+
                           |           API Gateway                |
                           |            (FastAPI)                 |
                           +--------+---------+---------+---------+
                                    |         |         |
                                    | gRPC    | gRPC    | gRPC
                                    v         v         v
+------------------------+  +-------+---+ +---+-------+ +---------+--+
|    registry-service    |  | mlops-service   | |  edge-connector-   |
| (Modelos/Scripts/Db)   |  | (Compilación)   | |      service       |
+-----------+------------+  +-------+---+ +---+-------+ +----+----+--+
            |                       |         |              |
            | MinIO / PG            | Docker  | MQTT         | Mongo / Prom
            v                       v         v              v
+-----------+------------+  +-------+---+ +---+-------+ +----+----+--+
| Almacenamiento y DBs   |  | Docker    | | Broker    | | Métricas   |
| (PostgreSQL y MinIO)   |  | Socket    | | MQTT      | | y Telemetría |
+------------------------+  +-----------+ +-----------+ +------------+
                                               ^
                                               | MQTT (Comandos, Telemetría)
                                               v
                                    +---------+---------+
                                    |   Dispositivo     |
                                    |   Edge Agent      |
                                    +-------------------+
```

### Componentes Clave

* **Frontend (Next.js)**: Una interfaz moderna e intuitiva para administrar dispositivos, subir archivos de modelos/scripts, ver logs en vivo y visualizar métricas de rendimiento.
* **API Gateway (FastAPI)**: Centraliza las solicitudes del Frontend, proporciona autenticación JWT y expone una interfaz REST hacia el exterior mientras redirige el tráfico internamente usando gRPC.
* **Microservicios (gRPC)**:
  * `registry-service`: Gestiona el catálogo de dispositivos, modelos y scripts.
  * `mlops-service`: Se encarga del entorno de compilación de modelos interactuando con sockets de Docker para aislar las tareas pesadas.
  * `edge-connector-service`: Gestiona las conexiones con los agentes perimetrales vía MQTT, almacena logs de inferencia en MongoDB y expone telemetría para Prometheus.
* **Edge Runtime**: Agente en Python optimizado para ejecutarse en el dispositivo físico, encargándose de descargar los modelos, validarlos con sumas SHA-256 y delegar la inferencia al hardware a través de la librería `aura_hw`.

---

## Hardware Soportado

AURA abstrae la complejidad del hardware subyacente. Los desarrolladores escriben scripts genéricos y la plataforma se encarga de adaptarlos a la tarjeta aceleradora disponible en el dispositivo:

| Dispositivo de Hardware | Formato de Modelo compatible | Nivel de Soporte |
|---|---|---|
| **Raspberry Pi 5 + Hailo-8** | `.hef` (Hailo Executable Format) | Completo (Producción) |
| **Raspberry Pi 5 + Hailo-8L** | `.hef` | Completo (Producción) |
| **Raspberry Pi 5 + AI Camera (IMX500)** | `packerOut.zip` | Completo (Producción) |
| **Raspberry Pi 5 (CPU)** | `.tflite` | Integración base (CPU Fallback) |
| **NVIDIA Jetson Orin Nano** | `.engine` (TensorRT) | Integración base (Soporte preliminar) |

Para comenzar a desplegar tus propios modelos, consulta nuestra sección de [Tutoriales de Ejecución](tutorials/run_platform) y aprende a poner en marcha el sistema.
