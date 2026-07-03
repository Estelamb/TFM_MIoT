"""
PAL — Communication Client
===========================
Async MQTT wrapper that provides a stable publish/subscribe interface
to the rest of the runtime, with automatic reconnection on broker
failures.

All MQTT topic conventions live here so the rest of the codebase never
constructs raw topic strings.

Topics
------
Subscribe:
    device/{device_id}/commands

Publish:
    device/{device_id}/events
    device/{device_id}/telemetry
    device/{device_id}/inference
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Awaitable, Callable

import aiomqtt

logger = logging.getLogger(__name__)

# Type alias for command handler callbacks.
# Receives the parsed JSON payload dict; may be async or sync.
CommandHandler = Callable[[dict], Awaitable[None] | None]


class CommunicationClient:
    """Async MQTT client with automatic reconnection and topic helpers.

    Parameters
    ----------
    device_id:
        Unique device identifier used to build MQTT topics.
    host:
        MQTT broker hostname.
    port:
        MQTT broker port (default 1883).
    reconnect_interval_s:
        Seconds to wait before attempting reconnection after a failure.
    """

    def __init__(
        self,
        device_id: str,
        host: str,
        port: int = 1883,
        reconnect_interval_s: int = 5,
        db_path: Path | None = None,
    ) -> None:
        self._device_id = device_id
        self._host = host
        self._port = port
        self._reconnect_interval = reconnect_interval_s
        self._client: aiomqtt.Client | None = None
        self._command_handlers: dict[str, CommandHandler] = {}
        
        # Resolve db_path or use a default one under /tmp/aura
        if db_path is None:
            self._db_path = Path("/tmp/aura") / f"mqtt_buffer_{device_id}.db"
        else:
            self._db_path = db_path
            
        self._init_db()

    # ── Topic helpers ─────────────────────────────────────────────────────────

    @property
    def topic_commands(self) -> str:
        return f"device/{self._device_id}/commands"

    @property
    def topic_events(self) -> str:
        return f"device/{self._device_id}/events"

    @property
    def topic_telemetry(self) -> str:
        return f"device/{self._device_id}/telemetry"

    @property
    def topic_inference(self) -> str:
        return f"device/{self._device_id}/inference"

    # ── Public API ────────────────────────────────────────────────────────────

    def register_command_handler(self, command: str, handler: CommandHandler) -> None:
        """Register a coroutine (or callable) for a specific command name.

        Parameters
        ----------
        command:
            The value of the ``"command"`` field in the MQTT payload.
        handler:
            Async callable that receives the full parsed payload dict.
        """
        self._command_handlers[command] = handler
        logger.debug(f"Registered handler for command '{command}'")

    async def publish_event(self, event: str, **extra: Any) -> None:
        """Publish an event to ``device/{id}/events``."""
        await self._publish(self.topic_events, {"event": event, **extra})

    async def publish_telemetry(self, payload: dict) -> None:
        """Publish a telemetry snapshot to ``device/{id}/telemetry``."""
        await self._publish(self.topic_telemetry, payload)

    async def publish_inference(self, payload: dict) -> None:
        """Publish an inference result to ``device/{id}/inference``."""
        await self._publish(self.topic_inference, payload)

    async def run(self) -> None:
        """Connect to the broker and start the message loop.

        This coroutine runs indefinitely, reconnecting on errors.
        It must be launched as an :func:`asyncio.create_task`.
        """
        import json
        while True:
            try:
                will = aiomqtt.Will(
                    topic=f"device/{self._device_id}/status",
                    payload=json.dumps({"status": "offline"}),
                    qos=1,
                    retain=True
                )
                async with aiomqtt.Client(
                    hostname=self._host, port=self._port, will=will
                ) as client:
                    self._client = client
                    await client.subscribe(self.topic_commands)
                    
                    # Publish online status immediately on connection
                    await client.publish(
                        f"device/{self._device_id}/status",
                        json.dumps({"status": "online"}),
                        retain=True
                    )
                    
                    logger.info(
                        f"MQTT connected — subscribed to {self.topic_commands}"
                    )
                    
                    # Start background flush of any queued SQLite messages
                    asyncio.create_task(self._flush_buffer())
                    
                    async for msg in client.messages:
                        await self._dispatch(msg)
            except aiomqtt.MqttError as exc:
                self._client = None
                logger.warning(
                    f"MQTT error: {exc} — reconnecting in {self._reconnect_interval}s"
                )
                await asyncio.sleep(self._reconnect_interval)

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _publish(self, topic: str, payload: dict) -> None:
        """Publish *payload* as JSON. Buffers locally in SQLite if not connected."""
        if self._client is None:
            logger.warning(f"MQTT offline: buffering message for topic '{topic}' to SQLite.")
            await asyncio.to_thread(self._buffer_message, topic, payload)
            return
        try:
            await self._client.publish(topic, json.dumps(payload))
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Publish failed on {topic} ({exc}). Buffering message.")
            await asyncio.to_thread(self._buffer_message, topic, payload)

    def _init_db(self) -> None:
        import sqlite3
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS mqtt_buffer (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        topic TEXT NOT NULL,
                        payload TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            logger.info(f"Local SQLite buffer database initialized at: {self._db_path}")
        except Exception as exc:
            logger.error(f"Failed to initialize SQLite buffer: {exc}")

    def _buffer_message(self, topic: str, payload: dict) -> None:
        import sqlite3
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    "INSERT INTO mqtt_buffer (topic, payload) VALUES (?, ?)",
                    (topic, json.dumps(payload))
                )
            logger.debug(f"Message buffered successfully in SQLite: {topic}")
        except Exception as exc:
            logger.error(f"Failed to buffer message to SQLite: {exc}")

    def _get_next_buffered_message(self) -> tuple[int, str, str] | None:
        import sqlite3
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, topic, payload FROM mqtt_buffer ORDER BY id ASC LIMIT 1")
                return cursor.fetchone()
        except Exception as exc:
            logger.error(f"Error reading from SQLite buffer: {exc}")
            return None

    def _delete_buffered_message(self, msg_id: int) -> None:
        import sqlite3
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("DELETE FROM mqtt_buffer WHERE id = ?", (msg_id,))
        except Exception as exc:
            logger.error(f"Error deleting from SQLite buffer: {exc}")

    async def _flush_buffer(self) -> None:
        """Read and publish all buffered messages from SQLite database."""
        logger.info("Checking SQLite buffer for offline-queued messages...")
        
        while True:
            # Check if we are still connected
            if self._client is None:
                logger.info("Flush paused: MQTT disconnected.")
                break
                
            # Get the oldest buffered message
            msg = await asyncio.to_thread(self._get_next_buffered_message)
            if msg is None:
                logger.info("SQLite buffer is empty. Flush completed.")
                break
                
            msg_id, topic, payload_str = msg
            try:
                # Try publishing it
                await self._client.publish(topic, payload_str)
                # If successful, delete it
                await asyncio.to_thread(self._delete_buffered_message, msg_id)
                logger.info(f"Successfully flushed buffered message {msg_id} to {topic}")
                # Brief sleep to avoid flooding
                await asyncio.sleep(0.05)
            except Exception as exc:
                logger.warning(f"Failed to flush buffered message {msg_id}: {exc}. Retrying later.")
                break

    async def _dispatch(self, msg: aiomqtt.Message) -> None:
        """Parse and dispatch an incoming MQTT message to the right handler."""
        try:
            payload = json.loads(msg.payload)
            command = payload.get("command")
            if command is None:
                logger.warning(f"Message without 'command' field: {payload}")
                return
            handler = self._command_handlers.get(command)
            if handler is None:
                logger.warning(f"No handler registered for command '{command}'")
                return
            logger.debug(f"Dispatching command '{command}'")
            result = handler(payload)
            if asyncio.iscoroutine(result):
                asyncio.create_task(result)
        except json.JSONDecodeError as exc:
            logger.error(f"Invalid JSON in MQTT message: {exc}")
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Command dispatch error: {exc}")
