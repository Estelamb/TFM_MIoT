"""
MongoDB collections para monitoring.
No usamos ORM — documentos directos via motor.

Collections:
  device_states     — estado actual por device_id (upsert)
  inference_results  — resultados de inferencia (append-only, TTL opcional)
"""
DEVICE_STATES_COL = "device_states"
INFERENCE_RESULTS_COL = "inference_results"
