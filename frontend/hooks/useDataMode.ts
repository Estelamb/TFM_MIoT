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
    sensors: ['RPi Camera Module 3', 'DHT22 Temperature', 'Ultrasonic HC-SR04', 'IMU 6-DOF'],
    actuators: ['Relay Module 5V', 'SG90 Micro Servo', 'Active Buzzer', 'Stepper Motor'],
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
        { name: "aura.capture()", desc: "Initiates capture from the sensor." },
        { name: "aura.process(frame)", desc: "Applies inference to the frame." },
        { name: "aura.actuate(pin, val)", desc: "Sends a signal to an actuator." }
      ],
      cpp: [
        { name: "aura_capture()", desc: "Frame capture in C++." },
        { name: "aura_process(void* ptr)", desc: "High-performance native processing." }
      ],
      java: [
        { name: "Aura.capture()", desc: "Frame capture via JNI." }
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
        created_at: new Date().toISOString()
      },
      {
        id: 'mod-102',
        name: 'Forklift-Tracker.pt',
        hardware_type: 'jetson_orin_nano',
        compile_status: 'compiling',
        created_at: new Date().toISOString()
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