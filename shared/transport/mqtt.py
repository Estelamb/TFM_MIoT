"""
MQTT implementation of :class:`TransportBase`.

Uses ``aiomqtt`` (an asyncio wrapper around ``paho-mqtt``) to connect
to a Mosquitto broker without TLS or authentication, as required for
the AURA PoC.
"""
import json
import logging
from typing import AsyncIterator

import aiomqtt

from shared.transport.base import TransportBase, MessageEnvelope

logger = logging.getLogger(__name__)


class MQTTTransport(TransportBase):
    """Async MQTT transport backed by ``aiomqtt``.

    Args:
        host: MQTT broker hostname, e.g. ``"mosquitto"`` or ``"localhost"``.
        port: MQTT broker port. Defaults to ``1883`` (plain TCP, no TLS).

    Example:
        >>> transport = MQTTTransport("localhost", 1883)
        >>> await transport.connect()
        >>> await transport.publish("device/abc/commands", {"command": "deploy"})
    """

    def __init__(self, host: str, port: int = 1883) -> None:
        self.host = host
        self.port = port
        self._client: aiomqtt.Client | None = None

    async def connect(self) -> None:
        """Connect to the MQTT broker."""
        self._client = aiomqtt.Client(hostname=self.host, port=self.port)
        await self._client.__aenter__()
        logger.info(f"MQTT connected to {self.host}:{self.port}")

    async def disconnect(self) -> None:
        """Disconnect from the MQTT broker and release the client."""
        if self._client:
            await self._client.__aexit__(None, None, None)

    async def publish(self, topic: str, payload: dict) -> None:
        """Publish a JSON-serialised payload to a topic.

        Args:
            topic:   MQTT topic string, e.g. ``"device/abc/commands"``.
            payload: Python dict serialised to JSON before publishing.

        Raises:
            RuntimeError: If :meth:`connect` has not been called.
        """
        if not self._client:
            raise RuntimeError("MQTTTransport not connected. Call connect() first.")
        await self._client.publish(topic, json.dumps(payload))
        logger.debug(f"MQTT published to {topic}")

    async def subscribe(self, topic_filter: str) -> AsyncIterator[MessageEnvelope]:
        """Subscribe and yield decoded messages.

        Args:
            topic_filter: MQTT topic or wildcard, e.g. ``"device/+/events"``.

        Yields:
            :class:`~shared.transport.base.MessageEnvelope` for each
            successfully decoded message. Malformed JSON is silently skipped.

        Raises:
            RuntimeError: If :meth:`connect` has not been called.
        """
        if not self._client:
            raise RuntimeError("MQTTTransport not connected. Call connect() first.")
        async with self._client.messages() as messages:
            await self._client.subscribe(topic_filter)
            async for msg in messages:
                try:
                    yield MessageEnvelope(
                        topic=str(msg.topic),
                        payload=json.loads(msg.payload),
                    )
                except Exception as exc:
                    logger.warning(f"Skipping malformed MQTT message on {msg.topic}: {exc}")
