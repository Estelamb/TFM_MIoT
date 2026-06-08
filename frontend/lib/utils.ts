import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }

export function fmtDate(iso?: string): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("es-ES", { dateStyle: "short", timeStyle: "short" }).format(new Date(iso));
}

export function fmtRelative(iso?: string): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `hace ${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `hace ${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `hace ${h}h`;
  return fmtDate(iso);
}

export const HW_LABELS: Record<string, string> = {
  hailo8: "Hailo-8", hailo8l: "Hailo-8L",
  rpi_ai_cam: "RPi AI Cam", aicam: "RPi AI Cam", rpi: "RPi (CPU)", jetson_orin_nano: "Jetson Orin",
  template: "Template Arch",
  
  // Peripherals
  rpi_camera_module_3: "RPi Camera Module 3",
  "camera/rpi_camera_module_3": "RPi Camera Module 3",
  dht22_temperature: "DHT22 Temperature",
  "temperature/dht22_temperature": "DHT22 Temperature",
  ultrasonic_hcsr04: "Ultrasonic HC-SR04",
  "distance/ultrasonic_hcsr04": "Ultrasonic HC-SR04",
  imu_6dof: "IMU 6-DOF",
  "imu/imu_6dof": "IMU 6-DOF",
  relay_5v_module: "5V Relay Module",
  "relay/relay_5v_module": "5V Relay Module",
  servo_sg90: "Standard Servo SG90",
  "servo/servo_sg90": "Standard Servo SG90",
  buzzer_alarm: "Buzzer Alarm Active",
  "buzzer/buzzer_alarm": "Buzzer Alarm Active",
  led_status_rgb: "LED Status RGB",
  "led/led_status_rgb": "LED Status RGB",

  // Peripheral Categories
  camera: "Camera",
  temperature: "Temperature / Environment",
  distance: "Distance",
  imu: "Inertial (IMU)",
  relay: "Relay / Switch",
  servo: "Servo / Motor",
  buzzer: "Buzzer / Alarm",
  led: "LED / Indicator",
};

export const STATUS_COLORS: Record<string, string> = {
  online: "text-aura-success", offline: "text-aura-dim",
  running: "text-aura-accent", compiling: "text-aura-warning",
  failed: "text-aura-danger", pending: "text-aura-dim", sent: "text-aura-info",
  ready: "text-aura-success",
};
