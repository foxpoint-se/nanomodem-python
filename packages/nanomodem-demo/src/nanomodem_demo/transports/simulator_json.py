"""SimulatorJsonTransport — TCP/JSON client for the God View Simulator.

Connects to a God View Simulator over TCP and uses a JSON protocol
to send/receive acoustic messages. Enables multi-terminal testing
without real hardware or shared memory.
"""

from __future__ import annotations

import logging
import socket
import threading
from typing import Optional

from nanomodem.core.driver import NanomodemV3Driver
from nanomodem.core.protocols import OnModemEventCallback
from nanomodem.core.wire_types import ModemCommand
from nanomodem.types import Coord

from ..simulator.protocol import (
    JsonLineBuffer,
    OnGpsUpdateCallback,
    SimulatorInboundHandlers,
    build_registration,
    build_transmit,
    dispatch_simulator_line,
    send_json_line,
)

logger = logging.getLogger(__name__)


class SimulatorJsonTransport:
    """WireTransport that communicates with a God View Simulator via TCP/JSON.

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
        self._callback: Optional[OnModemEventCallback] = None
        self._gps_callback: Optional[OnGpsUpdateCallback] = None
        self._running = False
        self._lock = threading.Lock()

        self._driver = NanomodemV3Driver()

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
            name=f"simulator-json-{node_id}-reader",
        )
        self._reader_started = False
        self._stopped = False

    def send_command(self, command: ModemCommand) -> None:
        """Send a modem command via the simulator acoustic channel."""
        data = self._driver.format_command(command)
        self._transmit(data)

    def on_event(self, callback: OnModemEventCallback) -> None:
        """Register a callback for parsed modem events."""
        self._callback = callback

    def start(self) -> None:
        """Start the background reader thread."""
        if self._reader_started:
            return
        self._running = True
        self._reader_thread.start()
        self._reader_started = True

    def stop(self) -> None:
        """Stop the background reader and close the socket."""
        if self._stopped:
            return
        self._stopped = True
        self._running = False
        with self._lock:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self._socket.close()
        if self._reader_started:
            self._reader_thread.join(timeout=2.0)

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
                logger.exception("Error in simulator JSON reader thread")
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
        event = self._driver.parse_line(line)
        if self._callback is not None:
            self._callback(event)
