"""TypedDict definitions for JSON protocol between SimulatorJsonTransport and Simulator.

This module defines the message schemas for communication between:
- Controllers using SimulatorJsonTransport
- The God View Simulator

These types are used for JSON serialization/deserialization in the network layer.
"""

from __future__ import annotations

from typing import TypedDict


class AcousticTransportConfig(TypedDict, total=False):
    """Configuration for how the controller sends acoustic data.

    Tells the simulator how to listen for this node's acoustic messages.
    """

    type: str  # "serial" | "network"
    pty_path: str  # Only for serial: the PTY path the Simulator should open


class NodeRegistration(TypedDict):
    """Initial handshake from controller to simulator.

    Sent when a controller first connects to the simulator.
    The acoustic_transport field tells the simulator how to receive
    this node's acoustic messages (via PTY or via the same TCP connection).
    """

    type: str  # "register"
    node_id: str
    acoustic_transport: AcousticTransportConfig


class TransmitMessage(TypedDict):
    """Acoustic message transmission from controller to simulator.

    Sent when a controller transmits a message via SimulatorJsonTransport.
    The simulator will then deliver it to the appropriate recipients
    based on physical positions and acoustic propagation.
    """

    type: str  # "transmit"
    node_id: str
    data: str  # Base64-encoded bytes


class AcousticMessageEvent(TypedDict):
    """Acoustic message reception from simulator to controller.

    Sent by the simulator when a message arrives at a controller's
    physical position, accounting for delays and attenuation.
    """

    type: str  # "acoustic_message"
    data: str  # Base64-encoded bytes


class GPSUpdateMessage(TypedDict):
    """Virtual GPS update from simulator to controller.

    Sent by the simulator to provide position updates to a controller,
    mimicking a real GPS unit's output.
    """

    type: str  # "gps_update"
    lat: float
    lon: float
