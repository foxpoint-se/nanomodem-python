"""Simulator backend with dynamic serial and network support.

Provides a unified backend that handles both:
1. Serial nodes - connects to PTY pairs for acoustic data, TCP for metadata
2. Network nodes - uses TCP for both acoustic data and metadata
"""

from __future__ import annotations

import base64
import json
import logging
import socket
import threading
from typing import Callable, Optional

import serial
from nanomodem.calculation import calculate_distance_3d
from nanomodem.core.driver import NanomodemV3Driver
from nanomodem.core.transports.in_memory import MOCK_STATUS_VOLTAGE_RAW
from nanomodem.core.wire_types import ReceivedBroadcastEvent
from nanomodem.positioning import BasicPositionCodec
from nanomodem.serial_logger import format_serial_log
from nanomodem.types import Coord, PositionMessage

from nanomodem_demo.scenarios.modem_relay import (
    broadcast_ack,
    broadcast_relay,
    parse_broadcast,
    parse_ping,
    parse_quality_query,
    parse_status_query,
    parse_test_request,
    ping_ack,
    range_response,
    relay_quality_query,
    relay_test_request,
    split_modem_command,
    status_response,
)
from nanomodem_demo.simulator.state import SimulatorState
from nanomodem_demo.simulator.types import AcousticMessageEvent, AcousticTransportConfig, GPSUpdateMessage

logger = logging.getLogger(__name__)

OnMessageCallback = Callable[[str, bytes], None]  # (node_id, data)
OnRegisterCallback = Callable[[str], None]  # (node_id)


class SerialReader:
    """Reads from a single PTY and notifies the backend of incoming bytes."""

    def __init__(
        self,
        node_id: str,
        pty_path: str,
        on_data: Callable[[str, bytes], None],
        on_error: Callable[[str, Exception], None],
    ) -> None:
        self.node_id = node_id
        self.pty_path = pty_path
        self.on_data = on_data
        self.on_error = on_error
        self.running = False
        self.port: Optional[serial.Serial] = None
        self.thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        """Open the PTY and start the reader thread. Returns True if the port opened."""
        try:
            self.port = serial.Serial(self.pty_path, baudrate=9600, timeout=0.1)
            self.running = True
            self.thread = threading.Thread(
                target=self._read_loop,
                daemon=True,
                name=f"serial-{self.node_id}-reader",
            )
            self.thread.start()
            logger.info("Opened PTY for node %s: %s", self.node_id, self.pty_path)
            return True
        except Exception as e:
            logger.error("Failed to open PTY %s for node %s: %s", self.pty_path, self.node_id, e)
            self.on_error(self.node_id, e)
            return False

    def stop(self) -> None:
        """Stop the reader thread and close the PTY."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        if self.port:
            self.port.close()

    def write(self, data: bytes) -> None:
        """Write data to the PTY."""
        if self.port:
            self.port.write(data)
            logger.info(format_serial_log("TX", self.node_id, data))

    def _read_loop(self) -> None:
        """Background thread: read framed commands and line-terminated responses from PTY."""
        buffer = b""
        while self.running and self.port:
            try:
                waiting = self.port.in_waiting
                chunk = self.port.read(waiting or 1)
                if not chunk:
                    continue
                buffer += chunk

                while True:
                    split = split_modem_command(buffer)
                    if split is not None:
                        command, buffer = split
                        logger.info(format_serial_log("RX", self.node_id, command))
                        self.on_data(self.node_id, command)
                        continue

                    if b"\n" not in buffer:
                        break

                    line, _, rest = buffer.partition(b"\n")
                    buffer = rest
                    if line.strip():
                        framed = line + b"\n"
                        logger.info(format_serial_log("RX", self.node_id, framed))
                        self.on_data(self.node_id, framed)

            except serial.SerialException:
                logger.exception("Serial error for node %s", self.node_id)
                break
            except OSError as exc:
                logger.exception("I/O error reading from PTY for node %s", self.node_id)
                self.on_error(self.node_id, exc)
                break


class HybridBackend:
    """Unified backend that handles both Serial and Network nodes.

    Opens a single TCP server for metadata (registration, GPS updates).
    Dynamically opens PTYs for serial nodes or uses the TCP socket for network nodes.
    """

    def __init__(
        self,
        state: SimulatorState,
        host: str = "127.0.0.1",
        port: int = 5555,
    ) -> None:
        self.state = state
        self.host = host
        self.port = port
        self.running = False

        # Single TCP server for ALL metadata
        self.server_socket: Optional[socket.socket] = None

        # Per-node connections
        self.metadata_clients: dict[str, socket.socket] = {}  # node_id -> TCP socket (for metadata)
        self.serial_readers: dict[str, SerialReader] = {}  # node_id -> PTY reader (for serial acoustics)
        self.network_acoustic_clients: set[str] = set()  # node_ids using TCP for acoustics

        # Threads
        self.accept_thread: Optional[threading.Thread] = None
        self.client_threads: list[threading.Thread] = []

        # Driver for parsing acoustic messages (reuse like Controllers do)
        self._codec = BasicPositionCodec()
        self._driver = NanomodemV3Driver()

        self._heard_data_packet: dict[str, bool] = {}

        # Callback for UI updates
        self.on_message: Optional[OnMessageCallback] = None
        self.on_register: Optional[OnRegisterCallback] = None
        self.on_raw_traffic: Optional[Callable[[str, bytes], None]] = None
        self.on_interpreted: Optional[Callable[[str], None]] = None

    def start(self) -> None:
        """Start the TCP server and accept thread."""
        self.running = True

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)

        self.accept_thread = threading.Thread(
            target=self._accept_loop,
            daemon=True,
            name="metadata-accept",
        )
        self.accept_thread.start()

        logger.info("HybridBackend started on %s:%d", self.host, self.port)

    def stop(self) -> None:
        """Stop the backend and clean up all connections."""
        self.running = False

        # Stop all serial readers
        for reader in list(self.serial_readers.values()):
            reader.stop()

        # Close all TCP clients
        for client_socket in list(self.metadata_clients.values()):
            client_socket.close()

        # Close server
        if self.server_socket:
            self.server_socket.close()

    def send_message(self, target_node_id: str, data: bytes) -> None:
        """Send an acoustic message to a specific node."""
        # Serial node: write to its PTY
        if target_node_id in self.serial_readers:
            self.serial_readers[target_node_id].write(data)

        # Network node: send as JSON on its metadata socket
        elif target_node_id in self.network_acoustic_clients:
            if target_node_id not in self.metadata_clients:
                logger.warning("Cannot send to disconnected node %s", target_node_id)
                return

            client_socket = self.metadata_clients[target_node_id]
            encoded = base64.b64encode(data).decode("ascii")
            msg: AcousticMessageEvent = {"type": "acoustic_message", "data": encoded}
            line = json.dumps(msg) + "\n"

            try:
                client_socket.sendall(line.encode("utf-8"))
                logger.debug("Sent acoustic message to %s", target_node_id)
            except Exception as e:
                logger.error("Failed to send to %s: %s", target_node_id, e)
        else:
            logger.warning("Cannot send to unknown node %s", target_node_id)

    def send_gps_update(self, node_id: str, coord: Coord) -> None:
        """Send GPS update to a node via its metadata socket."""
        if node_id not in self.metadata_clients:
            logger.warning("Node %s not connected", node_id)
            return

        client_socket = self.metadata_clients[node_id]
        msg: GPSUpdateMessage = {
            "type": "gps_update",
            "lat": coord.lat,
            "lon": coord.lon,
        }
        line = json.dumps(msg) + "\n"

        try:
            client_socket.sendall(line.encode("utf-8"))
            logger.debug("Sent GPS update to %s", node_id)
        except Exception as e:
            logger.error("Failed to send GPS to %s: %s", node_id, e)

    def _accept_loop(self) -> None:
        """Accept new client connections."""
        if not self.server_socket:
            return

        self.server_socket.settimeout(1.0)
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                logger.info("Client connected from %s", addr)

                thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket,),
                    daemon=True,
                    name=f"client-{addr}",
                )
                thread.start()
                self.client_threads.append(thread)

            except socket.timeout:
                continue
            except Exception:
                if self.running:
                    logger.exception("Error accepting client")

    def _handle_client(self, client_socket: socket.socket) -> None:
        """Handle messages from a connected client."""
        client_socket.settimeout(0.1)
        buffer = b""
        node_id: Optional[str] = None

        while self.running:
            try:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break

                buffer += chunk

                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if line:
                        obj = json.loads(line.decode("utf-8"))
                        msg_type = obj.get("type")

                        if msg_type == "register":
                            node_id = obj["node_id"]
                            acoustic_config = obj.get("acoustic_transport", {})
                            self._handle_registration(node_id, client_socket, acoustic_config)

                        elif msg_type == "transmit" and node_id:
                            # Network-mode acoustic data
                            data = base64.b64decode(obj["data"])

                            # Notify simulator UI
                            if self.on_message:
                                self.on_message(node_id, data)

                            # Broker the message
                            self._broker_message(node_id, data)

            except socket.timeout:
                continue
            except Exception:
                logger.exception("Error handling client %s", node_id)
                break

        # Cleanup
        if node_id:
            self._cleanup_node(node_id)

        client_socket.close()

    def _handle_registration(
        self,
        node_id: str,
        client_socket: socket.socket,
        acoustic_config: AcousticTransportConfig,
    ) -> None:
        """Handle node registration and set up acoustic connection."""
        # Store metadata socket
        self.metadata_clients[node_id] = client_socket
        self.state.register_node(node_id)

        transport_type = acoustic_config.get("type", "network")

        if transport_type == "serial":
            pty_path = acoustic_config.get("pty_path")
            if pty_path:
                if node_id in self.serial_readers:
                    logger.info("Node %s already has serial reader on %s", node_id, pty_path)
                else:
                    reader = SerialReader(
                        node_id=node_id,
                        pty_path=pty_path,
                        on_data=self._handle_serial_data,
                        on_error=self._handle_serial_error,
                    )
                    if reader.start():
                        self.serial_readers[node_id] = reader
                        logger.info("Node %s registered with Serial transport on %s", node_id, pty_path)
            else:
                logger.warning("Node %s registered as serial but no pty_path provided", node_id)

        elif transport_type == "network":
            # Acoustic data will come via the same TCP socket as metadata
            self.network_acoustic_clients.add(node_id)
            logger.info("Node %s registered with Network transport", node_id)

        else:
            logger.warning("Unknown transport type for node %s: %s", node_id, transport_type)

        if self.on_register:
            self.on_register(node_id)

    def _cleanup_node(self, node_id: str) -> None:
        """Clean up resources for a disconnected node."""
        if node_id in self.serial_readers:
            self.serial_readers[node_id].stop()
            del self.serial_readers[node_id]

        if node_id in self.network_acoustic_clients:
            self.network_acoustic_clients.remove(node_id)

        if node_id in self.metadata_clients:
            del self.metadata_clients[node_id]

        logger.info("Cleaned up node %s", node_id)

    def _handle_serial_data(self, node_id: str, data: bytes) -> None:
        """Callback when SerialReader receives data from a PTY."""
        # Notify simulator UI
        if self.on_message:
            self.on_message(node_id, data)

        # Broker the message
        self._broker_message(node_id, data)

    def _handle_serial_error(self, node_id: str, error: Exception) -> None:
        """Callback when SerialReader encounters an error."""
        logger.error("Serial error for node %s: %s", node_id, error)
        self._cleanup_node(node_id)

    def _apply_belief_update(self, msg: PositionMessage) -> None:
        self.state.set_belief_position(msg.node_id, msg.coord, msg.depth)
        if self.on_interpreted:
            self.on_interpreted(
                f"Belief update: {msg.node_id} at ({msg.coord.lat:.4f}, {msg.coord.lon:.4f}, {msg.depth:.1f}m)"
            )

    def _broker_message(self, sender_id: str, data: bytes) -> None:
        """Broker acoustic message routing based on physical positions."""
        if self.on_raw_traffic:
            self.on_raw_traffic(sender_id, data)

        line = data.decode("ascii", errors="replace").strip()
        parsed = self._driver.parse_line(line)
        if isinstance(parsed, ReceivedBroadcastEvent):
            belief_msg = self._codec.decode(parsed.data)
            if isinstance(belief_msg, PositionMessage):
                self._apply_belief_update(belief_msg)

        if parse_status_query(data):
            self.send_message(
                sender_id,
                status_response(sender_id, MOCK_STATUS_VOLTAGE_RAW),
            )
            return

        broadcast = parse_broadcast(data)
        if broadcast is not None:
            nn, body = broadcast
            belief_msg = self._codec.decode(body)
            if isinstance(belief_msg, PositionMessage):
                self._apply_belief_update(belief_msg)
            self.send_message(sender_id, broadcast_ack(nn))
            sender_pos = self.state.get_physical_position(sender_id)
            if sender_pos is None:
                logger.warning("No physical position for sender %s, dropping broadcast", sender_id)
                return
            for target_id in self.state.get_all_node_ids():
                if target_id == sender_id:
                    continue
                if self.state.get_physical_position(target_id) is None:
                    continue
                self.send_message(target_id, broadcast_relay(sender_id, nn, body))
            return

        ping_target = parse_ping(data)
        if ping_target is not None:
            self.send_message(sender_id, ping_ack(ping_target))
            sender_pos = self.state.get_physical_position(sender_id)
            target_pos = self.state.get_physical_position(ping_target)
            if sender_pos is None or target_pos is None:
                logger.warning("Missing positions for range %s -> %s", sender_id, ping_target)
                return
            sender_coord, sender_depth = sender_pos
            target_coord, target_depth = target_pos
            dist = calculate_distance_3d(sender_coord, sender_depth, target_coord, target_depth)
            self.send_message(
                sender_id,
                range_response(ping_target, dist, self.state.sound_speed),
            )
            return

        test_target = parse_test_request(data)
        if test_target is not None:
            relay_test_request(
                sender_id,
                test_target,
                send_message=self.send_message,
                get_listener_ids=self.state.get_all_node_ids,
                known_node_ids=set(self.state.get_all_node_ids()),
                heard_data_packet=self._heard_data_packet,
            )
            return

        if parse_quality_query(data):
            relay_quality_query(
                sender_id,
                send_message=self.send_message,
                heard_data_packet=self._heard_data_packet,
            )
