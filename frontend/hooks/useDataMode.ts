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
        { name: "execute_inference(raw_input)", desc: "Runs neural network inference on the preprocessed input image/tensor using the loaded compiled model." },
        { name: "get_hardware_info()", desc: "Returns a dictionary containing details of the auto-detected or configured edge hardware (e.g., hailo8, rpi_ai_cam)." },
        { name: "get_last_inference()", desc: "Fetches the most recent cached inference output dictionary from the device runtime." },
        { name: "load_model(model_path, hardware_type)", desc: "Loads a compiled model (e.g. .hef, .zip, .tflite) from MinIO to the target hardware accelerator." },
        { name: "unload_model()", desc: "Safely unloads the active neural network from the hardware context to free resources." },
        { name: "DeviceManager(config_path)", desc: "Instantiates the hardware manager. Methods: open_all(), close_all(), get_device(id), list_components()." }
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
        nodes: ['Node-Cluster-01']
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
        nodes: []
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
        hardware_type: 'hailo8',
        created_at: new Date().toISOString(),
        content: "import aura\n\ndef run():\n    frame = aura.capture()\n    results = aura.process(frame)\n    if results.has_defect:\n        aura.actuate('relay', True)"
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