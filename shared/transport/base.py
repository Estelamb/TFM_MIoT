"""
Abstract transport layer for AURA cloud-to-edge communication.

Defines the :class:`TransportBase` interface and :class:`MessageEnvelope`
data class so that MQTT can be swapped for WebSocket, AMQP or any other
broker without changing business logic.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncIterator


@dataclass
class MessageEnvelope:
    """A normalised message independent of the underlying transport.

    Attributes:
        topic:     The topic or routing key the message was sent to / received from.
        payload:   Decoded JSON payload as a Python dict.
        timestamp: ISO 8601 UTC timestamp set at construction time.
    """
    topic: str
    payload: dict
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class TransportBase(ABC):
    """Abstract base class for pluggable transport implementations.

    Concrete implementations must override all four abstract methods.
    The intended usage pattern is::

        transport = MQTTTransport("mosquitto", 1883)
        await transport.connect()
        await transport.publish("device/abc/commands", {"command": "deploy"})
        async for msg in transport.subscribe("device/+/events"):
            print(msg.topic, msg.payload)
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish a connection to the broker."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the connection and release resources."""
        ...

    @abstractmethod
    async def publish(self, topic: str, payload: dict) -> None:
        """Publish a message.

        Args:
            topic:   Destination topic or routing key.
            payload: Python dict that will be serialised to JSON.
        """
        ...

    @abstractmethod
    async def subscribe(self, topic_filter: str) -> AsyncIterator[MessageEnvelope]:
        """Subscribe to a topic filter and yield incoming messages.

        Args:
            topic_filter: Topic or wildcard filter, e.g. ``"device/+/events"``.

        Yields:
            :class:`MessageEnvelope` for each received message.
        """
        ...
