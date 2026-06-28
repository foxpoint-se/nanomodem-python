"""Tests for NetworkMockTransport."""

from __future__ import annotations

import base64
import json
import socket
import threading
import time
from collections.abc import Callable
from typing import TypeVar, cast

from nanomodem.core.wire_types import ModemEvent, ReceivedBroadcastEvent, StatusResponseEvent
from nanomodem.positioning import BasicPositionCodec
from nanomodem.types import Coord
from nanomodem_demo.node_builder import build_positioning_node
from nanomodem_demo.simulator.types import NodeRegistration, TransmitMessage
from nanomodem_demo.transports import NetworkMockTransport

POLL_TIMEOUT_S = 2.0
POLL_INTERVAL_S = 0.01

T = TypeVar("T")

SimulatorOutboundMessage = NodeRegistration | TransmitMessage


def _wait_until(condition: Callable[[], bool], timeout_s: float = POLL_TIMEOUT_S) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(POLL_INTERVAL_S)
    raise AssertionError(f"Condition not met within {timeout_s}s")


def _wait_for_length(items: list[T], expected: int, timeout_s: float = POLL_TIMEOUT_S) -> list[T]:
    _wait_until(lambda: len(items) >= expected, timeout_s)
    return items


class MockSimulatorServer:
    """Minimal mock simulator server for testing."""

    def __init__(self, port: int = 5555) -> None:
        self.port = port
        self.server_socket: socket.socket | None = None
        self.client_socket: socket.socket | None = None
        self.running = False
        self.received_messages: list[SimulatorOutboundMessage] = []
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
        while self.running and self.client_socket is None:
            try:
                self.client_socket, _ = self.server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break
        if self.client_socket and self.running:
            self._handle_client()

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
                        msg = cast(SimulatorOutboundMessage, json.loads(line.decode("utf-8")))
                        self.received_messages.append(msg)
            except socket.timeout:
                continue
            except Exception:
                break

    def send_acoustic_message(self, data: bytes) -> None:
        if not self.client_socket:
            return
        encoded = base64.b64encode(data).decode("ascii")
        msg = {"type": "acoustic_message", "data": encoded}
        line = json.dumps(msg) + "\n"
        self.client_socket.sendall(line.encode("utf-8"))

    def send_gps_update(self, lat: float, lon: float) -> None:
        if not self.client_socket:
            return
        msg = {"type": "gps_update", "lat": lat, "lon": lon}
        line = json.dumps(msg) + "\n"
        self.client_socket.sendall(line.encode("utf-8"))

    def wait_for_client(self, timeout_s: float = POLL_TIMEOUT_S) -> None:
        _wait_until(lambda: self.client_socket is not None, timeout_s)


def test_network_transport_registers_on_connect() -> None:
    server = MockSimulatorServer(port=5556)
    server.start()

    try:
        transport = NetworkMockTransport(node_id="001", port=5556)
        transport.start()

        _wait_for_length(server.received_messages, 1)

        reg = server.received_messages[0]
        assert reg["type"] == "register"
        assert reg["node_id"] == "001"

        transport.stop()
    finally:
        server.stop()


def test_network_transport_broadcast_position() -> None:
    server = MockSimulatorServer(port=5557)
    server.start()

    try:
        transport = NetworkMockTransport(node_id="001", port=5557)
        node = build_positioning_node("001", transport)
        transport.start()

        _wait_for_length(server.received_messages, 1)
        server.received_messages.clear()

        coord = Coord(lat=59.31, lon=17.98)
        node.set_position(coord)
        node.set_depth(10.0)
        node.broadcast_position()

        _wait_for_length(server.received_messages, 1)
        msg = server.received_messages[0]
        assert msg["type"] == "transmit"
        assert msg["node_id"] == "001"
        payload = msg.get("data")
        assert isinstance(payload, str)

        data = base64.b64decode(payload)
        assert isinstance(data, bytes)
        assert len(data) > 0

        transport.stop()
    finally:
        server.stop()


def test_network_transport_receives_acoustic_message() -> None:
    server = MockSimulatorServer(port=5558)
    server.start()

    try:
        transport = NetworkMockTransport(node_id="001", port=5558)
        transport.start()

        received_events: list[ModemEvent] = []
        transport.on_event(received_events.append)

        server.wait_for_client()

        fake_response = b"#B00232P002+59.310000+017.975000010.000\r\n"
        server.send_acoustic_message(fake_response)

        _wait_for_length(received_events, 1)
        event = received_events[0]
        assert isinstance(event, ReceivedBroadcastEvent)
        message = BasicPositionCodec().decode(event.data)
        assert message.node_id == "002"

        transport.stop()
    finally:
        server.stop()


def test__should_invoke_gps_callback_when_simulator_sends_gps_update() -> None:
    server = MockSimulatorServer(port=5560)
    server.start()

    try:
        transport = NetworkMockTransport(node_id="001", port=5560)
        transport.start()

        received: list[Coord] = []
        transport.on_gps_update(received.append)

        server.wait_for_client()
        server.send_gps_update(59.31, 17.98)

        _wait_for_length(received, 1)
        assert received[0].lat == 59.31
        assert received[0].lon == 17.98

        transport.stop()
    finally:
        server.stop()


def test_network_transport_request_range() -> None:
    server = MockSimulatorServer(port=5559)
    server.start()

    try:
        transport = NetworkMockTransport(node_id="001", port=5559)
        node = build_positioning_node("001", transport)
        node.set_known_node_position("002", Coord(lat=59.31, lon=17.98))
        transport.start()

        _wait_for_length(server.received_messages, 1)
        server.received_messages.clear()

        node.request_range("002")

        _wait_for_length(server.received_messages, 1)
        msg = server.received_messages[0]
        assert msg["type"] == "transmit"
        assert msg["node_id"] == "001"
        payload = msg.get("data")
        assert isinstance(payload, str)

        data = base64.b64decode(payload)
        assert data == b"$P002"

        transport.stop()
    finally:
        server.stop()


def test__should_stop_safely_when_reader_was_never_started() -> None:
    server = MockSimulatorServer(port=5561)
    server.start()

    try:
        transport = NetworkMockTransport(node_id="001", port=5561)
        transport.stop()
    finally:
        server.stop()


def test__should_parse_status_response_from_acoustic_message() -> None:
    server = MockSimulatorServer(port=5562)
    server.start()

    try:
        transport = NetworkMockTransport(node_id="001", port=5562)
        transport.start()

        received: list[ModemEvent] = []
        transport.on_event(received.append)

        server.wait_for_client()
        server.send_acoustic_message(b"#A001V48123\r\n")

        _wait_for_length(received, 1)
        assert isinstance(received[0], StatusResponseEvent)

        transport.stop()
    finally:
        server.stop()
