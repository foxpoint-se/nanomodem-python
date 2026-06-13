"""NetworkMockTransport -- TCP-based transport for multi-process simulation.

Connects to a God View Simulator over TCP and uses a JSON protocol
to send/receive acoustic messages. Enables multi-terminal testing
without real hardware or shared memory.
"""

from __future__ import annotations

import logging
import socket
import threading
from typing import Optional

from ..codecs.v3 import Codec
from ..demo.simulator_protocol import (
    JsonLineBuffer,
    OnGpsUpdateCallback,
    SimulatorInboundHandlers,
    build_registration,
    build_transmit,
    dispatch_simulator_line,
    send_json_line,
)
from ..drivers.v3 import NanomodemV3Driver
from ..protocols import OnMessageCallback
from ..types import Coord

logger = logging.getLogger(__name__)


class NetworkMockTransport:
    """Transport that communicates with a God View Simulator via TCP/JSON.

    This enables multi-process simulation where each controller runs in
    its own terminal, and the Simulator manages the physical world state,
    acoustic propagation, and position updates.
    """

    def __init__(
        self,
        node_id: str,
        host: str = "127.0.0.1",
        port: int = 5555,
        timeout: float = 0.1,
    ) -> None:
        self.node_id = node_id
        self._host = host
        self._port = port
        self._callback: Optional[OnMessageCallback] = None
        self._gps_callback: Optional[OnGpsUpdateCallback] = None
        self._running = False
        self._lock = threading.Lock()

        self._codec = Codec()
        self._driver = NanomodemV3Driver(self._codec)

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(timeout)
        self._socket.connect((host, port))

        reg = build_registration(node_id, {"type": "network"})
        send_json_line(self._socket, reg, self._lock)

        self._inbound_handlers = SimulatorInboundHandlers(
            on_acoustic_data=self._on_acoustic_data,
            on_gps_update=self._on_gps_from_simulator,
        )

        self._reader_thread = threading.Thread(
            target=self._read_loop,
            daemon=True,
            name=f"network-{node_id}-reader",
        )
        self._reader_started = False

    def start(self) -> None:
        """Start the background reader thread."""
        self._running = True
        self._reader_thread.start()
        self._reader_started = True

    def stop(self) -> None:
        """Stop the background reader and close the socket."""
        self._running = False
        with self._lock:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self._socket.close()
        if self._reader_started:
            self._reader_thread.join(timeout=2.0)

    def broadcast_position(self, coord: Coord, depth: float) -> None:
        """Broadcast position via the simulator (encodes as modem command)."""
        cmd = self._driver.format_broadcast(self.node_id, coord, depth)
        self._transmit(cmd)

    def request_range(self, target_id: str) -> None:
        """Request range via the simulator (encodes as modem command)."""
        cmd = self._driver.format_ping(target_id)
        self._transmit(cmd)

    def request_test(self, target_id: str) -> None:
        """Request a test transmission from target via the simulator."""
        cmd = self._driver.format_test_request(target_id)
        self._transmit(cmd)

    def query_quality(self) -> None:
        """Query link quality on last data packet via the simulator."""
        cmd = self._driver.format_quality_query()
        self._transmit(cmd)

    def query_modem_status(self) -> None:
        """Query modem address and supply voltage via the simulator."""
        cmd = self._driver.format_status_query()
        self._transmit(cmd)

    def on_message(self, callback: OnMessageCallback) -> None:
        """Register a callback for received messages."""
        self._callback = callback

    def on_gps_update(self, callback: OnGpsUpdateCallback) -> None:
        """Register a callback for virtual GPS updates from the simulator."""
        self._gps_callback = callback

    def _transmit(self, data: bytes) -> None:
        """Send acoustic data to simulator for propagation."""
        msg = build_transmit(self.node_id, data)
        send_json_line(self._socket, msg, self._lock)
        logger.debug("TX [%s]: %s", self.node_id, data)

    def _read_loop(self) -> None:
        """Background thread: read JSON lines from simulator and dispatch."""
        line_buffer = JsonLineBuffer()
        while self._running:
            try:
                chunk = self._socket.recv(4096)
                if not chunk:
                    logger.warning("Simulator closed connection")
                    break
                for line in line_buffer.feed(chunk):
                    dispatch_simulator_line(line, self._inbound_handlers)
            except socket.timeout:
                continue
            except Exception:
                logger.exception("Error in network reader thread")
                break

    def _on_gps_from_simulator(self, coord: Coord) -> None:
        logger.info("GPS update [%s]: %s", self.node_id, coord)
        if self._gps_callback is not None:
            self._gps_callback(coord)

    def _on_acoustic_data(self, data: bytes) -> None:
        logger.debug("RX [%s]: %s", self.node_id, data)
        line = data.decode("ascii", errors="replace").strip()
        if not line:
            return
        msg = self._driver.parse_line(line)
        if self._callback is not None:
            self._callback(msg)
