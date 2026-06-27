"""
Abstract transport layer.
Implemented over MQTT. Designed to be interchangeable (WebSocket, AMQP, etc.)
"""
from shared.transport.base import TransportBase, MessageEnvelope
from shared.transport.mqtt import MQTTTransport

_transport: TransportBase | None = None

def init_transport(t: TransportBase) -> None:
    global _transport; _transport = t

def get_transport() -> TransportBase:
    if _transport is None:
        raise RuntimeError("Transport not initialized")
    return _transport

__all__ = ["TransportBase", "MessageEnvelope", "MQTTTransport", "init_transport", "get_transport"]
