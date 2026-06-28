"""God View Simulator for multi-process acoustic network simulation.

This package contains the simulator infrastructure for managing
the physical world state and acoustic propagation in a multi-process
simulation environment.
"""

from .protocol import (
    JsonLineBuffer,
    SimulatorInboundHandlers,
    SimulatorMetadataClient,
    build_registration,
    build_transmit,
    send_json_line,
)
from .types import (
    AcousticMessageEvent,
    AcousticTransportConfig,
    GPSUpdateMessage,
    NodeRegistration,
    TransmitMessage,
)

__all__ = [
    "JsonLineBuffer",
    "SimulatorInboundHandlers",
    "SimulatorMetadataClient",
    "build_registration",
    "build_transmit",
    "send_json_line",
    "AcousticMessageEvent",
    "AcousticTransportConfig",
    "GPSUpdateMessage",
    "NodeRegistration",
    "TransmitMessage",
]
