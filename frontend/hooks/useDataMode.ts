import { create } from 'zustand';

interface DataStore {
  mode: 'real' | 'demo';
  toggleMode: () => void;
  demoData: {
    // --- Catalogs & UI Mocks ---
    datasets: string[];
    yoloVersions: { value: string; label: string }[];
    architectures: string[];
    sensors: string[];
    actuators: string[];
    nodes: string[];
    
    // --- Docs & Aggregated Stats ---
    monitoring: any;
    halDocs: any;
    
    // --- Core API Entities ---
    devices: any[];
    models: any[];
    scripts: any[];
    deployments: any[];
    monitoringStates: any[];
  };
}

export const useDataMode = create<DataStore>((set) => ({
  mode: 'real',
  toggleMode: () => set((state) => ({ mode: state.mode === 'real' ? 'demo' : 'real' })),
  demoData: {
    
    // ==========================================
    // 1. CATALOGS & UI MOCKS
    // ==========================================
    datasets: ['Agriculture v1', 'Drone Imagery 2026', 'Factory Defect Vision'],
    yoloVersions: [
      { value: 'yolo8n', label: 'YOLOv8 Nano' },
      { value: 'yolo8s', label: 'YOLOv8 Small' }
    ],
    architectures: ['RPi 5', 'Hailo 8 M.2', 'Jetson Orin Nano', 'Coral TPU'],
    sensors: ['camera/rpi_camera_module_3', 'temperature/dht22_temperature', 'distance/ultrasonic_hcsr04', 'imu/imu_6dof'],
    actuators: ['relay/relay_5v_module', 'servo/servo_sg90', 'buzzer/buzzer_alarm', 'led/led_status_rgb'],
    nodes: ['Gateway-ZoneA', 'Node-Cluster-01', 'Factory-Floor-Hub'],

    // ==========================================
    // 2. DOCS & AGGREGATED STATS
    // ==========================================
    monitoring: {
      activeNodes: "2 / 2",
      avgLatency: "14 ms",
      alerts: 0,
      cpuLoad: 42,
      memory: 78,
      bandwidth: 65,
      storage: 92
    },
    halDocs: {
      python: [
        // --- Generic Inference API (aura_hw) ---
        { name: "from aura_hw import execute_inference, get_hardware_info, get_last_inference, load_model, unload_model", desc: "Imports the generic inference runtime functions." },
        { name: "execute_inference(raw_input) -> dict", desc: "Runs neural network inference on the preprocessed input image/tensor using the loaded compiled model." },
        { name: "get_hardware_info() -> dict", desc: "Returns a dictionary containing details of the auto-detected or configured edge hardware (e.g., hailo8, rpi_cpu)." },
        { name: "get_last_inference() -> dict", desc: "Fetches the most recent cached inference output dictionary from the device runtime." },
        { name: "load_model(model_path, hardware_type) -> None", desc: "Loads a compiled model (e.g. .hef, .onnx) from MinIO to the target hardware accelerator." },
        { name: "unload_model() -> None", desc: "Safely unloads the active neural network from the hardware context to free resources." },
        
        // --- Generic Camera Library ---
        { name: "from hardware.sensors.camera.library import Camera, take_photo, initialize, close", desc: "Imports the generic camera library functions and class." },
        { name: "camera = Camera(**kwargs)", desc: "Instantiates a generic Camera client. Automatically loads the configured camera driver (e.g., RPi Camera Module 3)." },
        { name: "camera.initialize() -> bool", desc: "Initializes the configured camera. Returns True if successful, False otherwise." },
        { name: "camera.take_photo() -> np.ndarray", desc: "Captures a single RGB frame from the camera." },
        { name: "camera.close() -> None", desc: "Releases and stops the camera resources." },
        
        // --- Generic Template Sensor Library ---
        { name: "from hardware.sensors.template.library import TemplateSensor, read_value, initialize", desc: "Imports the generic template sensor library functions and class." },
        { name: "sensor = TemplateSensor(**kwargs)", desc: "Instantiates a generic TemplateSensor client. Automatically loads the configured template driver." },
        { name: "sensor.initialize() -> bool", desc: "Initializes the sensor. Returns True if successful, False otherwise." },
        { name: "sensor.read_value() -> dict", desc: "Reads value from the template sensor." },
        
        // --- Generic Template Actuator Library ---
        { name: "from hardware.actuators.template.library import TemplateActuator, write_value, initialize", desc: "Imports the generic template actuator library functions and class." },
        { name: "actuator = TemplateActuator(**kwargs)", desc: "Instantiates a generic TemplateActuator client. Automatically loads the configured template driver." },
        { name: "actuator.initialize() -> bool", desc: "Initializes the actuator. Returns True if successful, False otherwise." },
        { name: "actuator.write_value(value) -> None", desc: "Writes a value / state change command to the actuator." },
        
        // --- Generic Template Other Library ---
        { name: "from hardware.others.template.library import TemplateOther, run_action, initialize", desc: "Imports the generic template other library functions and class." },
        { name: "other = TemplateOther(**kwargs)", desc: "Instantiates a generic TemplateOther client. Automatically loads the configured template driver." },
        { name: "other.initialize() -> bool", desc: "Initializes the device. Returns True if successful, False otherwise." },
        { name: "other.run_action() -> None", desc: "Executes the main action of the other device." }
      ],
      cpp: [
        { name: "void* aura_load_model(const char* path, const char* hw_type)", desc: "Initializes the native context and loads the model into accelerator memory." },
        { name: "void aura_unload_model()", desc: "Frees accelerator assets and releases native hardware context." },
        { name: "int aura_execute_inference(void* input, void* output)", desc: "Performs high-performance zero-copy inference execution directly in C++." },
        { name: "const char* aura_get_hardware_info()", desc: "Returns a JSON string containing detected hardware specifications." }
      ],
      java: [
        { name: "AuraRuntime.loadModel(String path, String hwType)", desc: "Invokes the native JNI wrapper to load the model on the edge device accelerator." },
        { name: "AuraRuntime.unloadModel()", desc: "Closes JNI runtime session and unloads model." },
        { name: "List<Detection> AuraRuntime.executeInference(Object input)", desc: "Executes inference and returns a list of Detection objects." },
        { name: "Map<String, Object> AuraRuntime.getHardwareInfo()", desc: "Queries JNI runtime for a Map representing hardware details." }
      ]
    },

    // ==========================================
    // 3. CORE API ENTITIES
    // ==========================================
    devices: [
      { 
        id: 'dev-001', 
        name: 'Factory-Line-A', 
        hardware_type: 'hailo8', 
        status: 'online', 
        created_at: new Date().toISOString(),
        architecture: ['Hailo 8 M.2'],
        sensors: ['RPi Camera Module 3'],
        actuators: ['Relay Module 5V'],
        nodes: ['Node-Cluster-01'],
        others: ['Custom heatsink', 'DIN Rail Mount']
      },
      { 
        id: 'dev-002', 
        name: 'Warehouse-Drone-Hub', 
        hardware_type: 'jetson_orin_nano', 
        status: 'online', 
        created_at: new Date().toISOString(),
        architecture: ['Jetson Orin Nano'],
        sensors: ['Stereo Vision Cam'],
        actuators: [],
        nodes: [],
        others: ['High-gain WiFi antenna']
      }
    ],
    models: [
      {
        id: 'mod-101',
        name: 'Defect-Detection-v2.pt',
        hardware_type: 'hailo8',
        compile_status: 'ready',
        created_at: new Date().toISOString(),
        base_architecture: 'yolov8n.yaml',
        epochs: 100,
        input_size: '640x640',
        batch_size: 16
      },
      {
        id: 'mod-102',
        name: 'Forklift-Tracker.pt',
        hardware_type: 'jetson_orin_nano',
        compile_status: 'training',
        created_at: new Date().toISOString(),
        base_architecture: 'yolov8s.yaml',
        epochs: 50,
        input_size: '640x640',
        batch_size: 32
      }
    ],
    scripts: [
      {
        id: 'scr-201',
        name: 'conveyor_belt_infer.py',
        language: 'python',
        created_at: new Date().toISOString(),
        content: "from aura_hw import execute_inference\nfrom hardware.sensors.camera.library import take_photo\nfrom hardware.actuators.template.library import write_value\n\ndef run(raw_input=None):\n    frame = raw_input if raw_input is not None else take_photo()\n    raw_output = execute_inference(frame)\n    \n    has_defect = False\n    if raw_output:\n        has_defect = True  # example trigger logic\n        \n    if has_defect:\n        write_value(True)\n        \n    return {'defect_detected': has_defect}"
      }
    ],
    deployments: [
      {
        id: 'dep-301',
        device_id: 'dev-001',
        model_id: 'mod-101',
        script_id: 'scr-201',
        status: 'running',
        created_at: new Date().toISOString()
      },
      {
        id: 'dep-302',
        device_id: 'dev-002',
        model_id: 'mod-101',
        script_id: 'scr-201',
        status: 'failed',
        error_msg: "OTA deploy failed: No module named 'onnxruntime' inside custom inference runtime loading stage.",
        created_at: new Date(Date.now() - 3600000).toISOString()
      }
    ],
    monitoringStates: [
      {
        device_id: 'dev-001',
        status: 'online',
        cpu_percent: 45,
        ram_percent: 60,
        ram_used_mb: 2048,
        last_seen_at: new Date().toISOString(),
        coordinates: [-3.7038, 40.4168] // Madrid
      },
      {
        device_id: 'dev-002',
        status: 'online',
        cpu_percent: 82,
        ram_percent: 85,
        ram_used_mb: 4096,
        last_seen_at: new Date().toISOString(),
        coordinates: [-74.0060, 40.7128] // New York
      }
    ]
  }
}));