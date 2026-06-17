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
    ) -> None:
        self._device_id = device_id
        self._host = host
        self._port = port
        self._reconnect_interval = reconnect_interval_s
        self._client: aiomqtt.Client | None = None
        self._command_handlers: dict[str, CommandHandler] = {}

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
        """Publish *payload* as JSON. Silently drops if not connected."""
        if self._client is None:
            logger.debug(f"Publish skipped (not connected): {topic}")
            return
        try:
            await self._client.publish(topic, json.dumps(payload))
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Publish failed on {topic}: {exc}")

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
