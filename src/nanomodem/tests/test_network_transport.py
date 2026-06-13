"""Tests for NetworkMockTransport."""

from __future__ import annotations

import base64
import json
import socket
import threading
from typing import Any

from nanomodem.transports.network import NetworkMockTransport
from nanomodem.types import Coord, PositionMessage


class MockSimulatorServer:
    """Minimal mock simulator server for testing."""

    def __init__(self, port: int = 5555) -> None:
        self.port = port
        self.server_socket: socket.socket | None = None
        self.client_socket: socket.socket | None = None
        self.running = False
        self.received_messages: list[dict[str, Any]] = []
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("127.0.0.1", self.port))
        self.server_socket.listen(1)
        self.running = True
        self.thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        if self.client_socket:
            self.client_socket.close()
        if self.server_socket:
            self.server_socket.close()

    def _accept_loop(self) -> None:
        if not self.server_socket:
            return
        self.server_socket.settimeout(1.0)
        try:
            self.client_socket, _ = self.server_socket.accept()
            self._handle_client()
        except socket.timeout:
            pass

    def _handle_client(self) -> None:
        if not self.client_socket:
            return
        self.client_socket.settimeout(0.1)
        buffer = b""
        while self.running:
            try:
                chunk = self.client_socket.recv(4096)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if line:
                        msg = json.loads(line.decode("utf-8"))
                        self.received_messages.append(msg)
            except socket.timeout:
                continue
            except Exception:
                break

    def send_acoustic_message(self, data: bytes) -> None:
        """Send an acoustic message to the connected client."""
        if not self.client_socket:
            return
        encoded = base64.b64encode(data).decode("ascii")
        msg = {"type": "acoustic_message", "data": encoded}
        line = json.dumps(msg) + "\n"
        self.client_socket.sendall(line.encode("utf-8"))

    def send_gps_update(self, lat: float, lon: float) -> None:
        """Send a virtual GPS update to the connected client."""
        if not self.client_socket:
            return
        msg = {"type": "gps_update", "lat": lat, "lon": lon}
        line = json.dumps(msg) + "\n"
        self.client_socket.sendall(line.encode("utf-8"))


def test_network_transport_registers_on_connect() -> None:
    """Should send NodeRegistration message on connect."""
    server = MockSimulatorServer(port=5556)
    server.start()

    try:
        transport = NetworkMockTransport(node_id="001", port=5556)
        transport.start()

        # Wait for registration to be received
        import time

        time.sleep(0.2)

        assert len(server.received_messages) == 1
        reg = server.received_messages[0]
        assert reg["type"] == "register"
        assert reg["node_id"] == "001"

        transport.stop()
    finally:
        server.stop()


def test_network_transport_broadcast_position() -> None:
    """Should send TransmitMessage when broadcasting position."""
    server = MockSimulatorServer(port=5557)
    server.start()

    try:
        transport = NetworkMockTransport(node_id="001", port=5557)
        transport.start()

        # Clear registration message
        import time

        time.sleep(0.2)
        server.received_messages.clear()

        # Broadcast position
        coord = Coord(lat=59.31, lon=17.98)
        transport.broadcast_position(coord, depth=10.0)

        time.sleep(0.2)

        assert len(server.received_messages) == 1
        msg = server.received_messages[0]
        assert msg["type"] == "transmit"
        assert msg["node_id"] == "001"
        assert "data" in msg

        # Verify it's base64-encoded bytes
        data = base64.b64decode(msg["data"])
        assert isinstance(data, bytes)
        assert len(data) > 0

        transport.stop()
    finally:
        server.stop()


def test_network_transport_receives_acoustic_message() -> None:
    """Should receive and parse acoustic messages from simulator."""
    server = MockSimulatorServer(port=5558)
    server.start()

    try:
        transport = NetworkMockTransport(node_id="001", port=5558)
        transport.start()

        # Register callback
        received_messages = []
        transport.on_message(lambda msg: received_messages.append(msg))

        # Wait for connection
        import time

        time.sleep(0.2)

        # Simulate incoming acoustic message (position broadcast)
        # Format: #Bxxxnnddd... (per v3 protocol)
        # Example: #B00232P002+59.310000+017.975000010.000
        fake_response = b"#B00232P002+59.310000+017.975000010.000\r\n"
        server.send_acoustic_message(fake_response)

        time.sleep(0.2)

        assert len(received_messages) == 1
        msg = received_messages[0]
        assert isinstance(msg, PositionMessage)
        assert msg.node_id == "002"

        transport.stop()
    finally:
        server.stop()


def test__should_invoke_gps_callback_when_simulator_sends_gps_update() -> None:
    """Virtual GPS from simulator should reach the registered callback."""
    server = MockSimulatorServer(port=5560)
    server.start()

    try:
        transport = NetworkMockTransport(node_id="001", port=5560)
        transport.start()

        received: list[Coord] = []
        transport.on_gps_update(received.append)

        import time

        time.sleep(0.2)
        server.send_gps_update(59.31, 17.98)
        time.sleep(0.2)

        assert len(received) == 1
        assert received[0].lat == 59.31
        assert received[0].lon == 17.98

        transport.stop()
    finally:
        server.stop()


def test_network_transport_request_range() -> None:
    """Should send TransmitMessage when requesting range."""
    server = MockSimulatorServer(port=5559)
    server.start()

    try:
        transport = NetworkMockTransport(node_id="001", port=5559)
        transport.start()

        # Clear registration message
        import time

        time.sleep(0.2)
        server.received_messages.clear()

        # Request range
        transport.request_range(target_id="002")

        time.sleep(0.2)

        assert len(server.received_messages) == 1
        msg = server.received_messages[0]
        assert msg["type"] == "transmit"
        assert msg["node_id"] == "001"

        # Verify it's a ping command
        data = base64.b64decode(msg["data"])
        assert b"PING" in data or b"002" in data

        transport.stop()
    finally:
        server.stop()


def test__should_stop_safely_when_reader_was_never_started() -> None:
    """stop() before start() must not raise when the reader thread was never started."""
    server = MockSimulatorServer(port=5561)
    server.start()

    try:
        transport = NetworkMockTransport(node_id="001", port=5561)
        transport.stop()
    finally:
        server.stop()
