"""JSON line protocol between God View Simulator and controllers.

Shared inbound dispatch and outbound message encoding. No GUI or transport logic.
"""

from __future__ import annotations

import base64
import json
import logging
import socket
import threading
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .sim_types import AcousticMessageEvent, AcousticTransportConfig, GPSUpdateMessage
from .types import Coord

logger = logging.getLogger(__name__)

OnAcousticDataCallback = Callable[[bytes], None]
OnGpsUpdateCallback = Callable[[Coord], None]


@dataclass(frozen=True)
class SimulatorInboundHandlers:
    """Callbacks for messages sent simulator → controller."""

    on_acoustic_data: Optional[OnAcousticDataCallback] = None
    on_gps_update: Optional[OnGpsUpdateCallback] = None


class JsonLineBuffer:
    """Split a byte stream into newline-delimited text lines."""

    def __init__(self) -> None:
        self._buffer = b""

    def feed(self, chunk: bytes) -> list[str]:
        self._buffer += chunk
        lines: list[str] = []
        while b"\n" in self._buffer:
            line, self._buffer = self._buffer.split(b"\n", 1)
            if line:
                lines.append(line.decode("utf-8"))
        return lines


def parse_gps_update(obj: dict[str, Any]) -> Coord:
    msg: GPSUpdateMessage = {
        "type": "gps_update",
        "lat": float(obj["lat"]),
        "lon": float(obj["lon"]),
    }
    return Coord(lat=msg["lat"], lon=msg["lon"])


def dispatch_simulator_inbound(obj: dict[str, Any], handlers: SimulatorInboundHandlers) -> None:
    """Route one parsed JSON object from the simulator to the right handler."""
    msg_type = obj.get("type")

    if msg_type == "acoustic_message":
        if handlers.on_acoustic_data is None:
            return
        acoustic: AcousticMessageEvent = {
            "type": "acoustic_message",
            "data": str(obj["data"]),
        }
        handlers.on_acoustic_data(base64.b64decode(acoustic["data"]))
        return

    if msg_type == "gps_update":
        if handlers.on_gps_update is None:
            return
        coord = parse_gps_update(obj)
        logger.info("GPS update from simulator: %s", coord)
        handlers.on_gps_update(coord)
        return

    logger.warning("Unknown message type from simulator: %s", msg_type)


def dispatch_simulator_line(line: str, handlers: SimulatorInboundHandlers) -> None:
    """Parse one JSON line and dispatch, logging decode errors."""
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON from simulator: %s", line)
        return
    try:
        dispatch_simulator_inbound(obj, handlers)
    except Exception:
        logger.exception("Error handling message from simulator")


def build_registration(
    node_id: str,
    acoustic_transport: AcousticTransportConfig,
) -> dict[str, Any]:
    return {
        "type": "register",
        "node_id": node_id,
        "acoustic_transport": acoustic_transport,
    }


def build_transmit(node_id: str, data: bytes) -> dict[str, Any]:
    return {
        "type": "transmit",
        "node_id": node_id,
        "data": base64.b64encode(data).decode("ascii"),
    }


def send_json_line(sock: socket.socket, obj: dict[str, Any], lock: Optional[threading.Lock] = None) -> None:
    line = json.dumps(obj) + "\n"
    payload = line.encode("utf-8")
    if lock is not None:
        with lock:
            sock.sendall(payload)
    else:
        sock.sendall(payload)


class SimulatorMetadataClient:
    """TCP client for simulator metadata (registration + inbound GPS, etc.)."""

    def __init__(
        self,
        node_id: str,
        host: str,
        port: int,
        acoustic_transport: AcousticTransportConfig,
        handlers: SimulatorInboundHandlers,
        timeout: float = 0.1,
    ) -> None:
        self._node_id = node_id
        self._host = host
        self._port = port
        self._acoustic_transport = acoustic_transport
        self._handlers = handlers
        self._timeout = timeout
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stopped = False

    def start(self) -> None:
        if self._thread is not None:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name=f"sim-meta-{self._node_id}")
        self._thread.start()

    def stop(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self._timeout)
                sock.connect((self._host, self._port))

                reg = build_registration(self._node_id, self._acoustic_transport)
                send_json_line(sock, reg)
                logger.info("Connected to simulator metadata at %s:%d", self._host, self._port)

                line_buffer = JsonLineBuffer()
                while self._running:
                    try:
                        chunk = sock.recv(4096)
                    except socket.timeout:
                        continue
                    if not chunk:
                        break
                    for line in line_buffer.feed(chunk):
                        dispatch_simulator_line(line, self._handlers)
        except Exception:
            logger.exception("Simulator metadata client error")
