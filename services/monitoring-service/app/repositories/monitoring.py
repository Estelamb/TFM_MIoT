from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.mongo import DEVICE_STATES_COL, INFERENCE_RESULTS_COL

class MonitoringRepository:
    def __init__(self, db: AsyncIOMotorDatabase): self._db = db

    async def upsert_device_state(self, device_id: str, state: dict) -> None:
        state["device_id"] = device_id
        state["last_seen_at"] = datetime.now(timezone.utc).isoformat()
        await self._db[DEVICE_STATES_COL].update_one(
            {"device_id": device_id}, {"$set": state}, upsert=True
        )

    async def get_device_state(self, device_id: str) -> dict | None:
        return await self._db[DEVICE_STATES_COL].find_one(
            {"device_id": device_id}, {"_id": 0}
        )

    async def list_device_states(self) -> list[dict]:
        cursor = self._db[DEVICE_STATES_COL].find({}, {"_id": 0})
        return await cursor.to_list(length=None)

    async def insert_inference_result(self, device_id: str, deployment_id: str, result_json: str) -> None:
        await self._db[INFERENCE_RESULTS_COL].insert_one({
            "device_id": device_id,
            "deployment_id": deployment_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "result_json": result_json,
        })

    async def get_inference_results(self, device_id: str, limit: int = 20) -> list[dict]:
        cursor = self._db[INFERENCE_RESULTS_COL].find(
            {"device_id": device_id}, {"_id": 0}
        ).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=None)
