"""In-memory wire transport for fast modem simulation without serial I/O."""

from __future__ import annotations

import logging
from typing import Callable, Optional

from nanomodem.calculation import calculate_distance_3d
from nanomodem.constants import SOUND_SPEED_WATER_M_S, validate_sound_speed
from nanomodem.types import Coord

from ..protocols import OnModemEventCallback
from ..spec import distance_to_timestamp
from ..wire_types import (
    AddressSetEvent,
    BroadcastCommand,
    BroadcastCommandAckEvent,
    EchoCommand,
    EchoCommandAckEvent,
    ModemCommand,
    ModemEvent,
    PingCommand,
    PingCommandAckEvent,
    PingTimeoutEvent,
    QualityIndicatorEvent,
    QualityQueryCommand,
    QualityRejectedEvent,
    ReceivedBroadcastEvent,
    ReceivedUnicastEvent,
    RemoteVoltageQueryAckEvent,
    RemoteVoltageQueryCommand,
    RemoteVoltageResponseEvent,
    RoundtripResponseEvent,
    SetAddressCommand,
    StatusQueryCommand,
    StatusResponseEvent,
    TestBroadcastReceivedEvent,
    TestRequestAckEvent,
    TestRequestCommand,
    UnicastCommand,
    UnicastCommandAckEvent,
    UnicastWithAckCommand,
    UnicastWithAckCommandAckEvent,
)

MOCK_BYTES_CORRECTED = 3
MOCK_STATUS_VOLTAGE_RAW = 48123

logger = logging.getLogger(__name__)


class InMemoryBus:
    """Shared in-process bus for InMemoryTransport instances."""

    def __init__(self, sound_speed: float = SOUND_SPEED_WATER_M_S) -> None:
        self._transports: dict[str, InMemoryTransport] = {}
        self._sound_speed = validate_sound_speed(sound_speed)
        self._heard_data_packet: dict[str, bool] = {}

    def register(self, transport: InMemoryTransport) -> None:
        self._transports[transport.node_id] = transport

    def unregister(self, node_id: str) -> None:
        self._transports.pop(node_id, None)

    def get_transport(self, node_id: str) -> InMemoryTransport | None:
        return self._transports.get(node_id)

    def get_all_except(self, node_id: str) -> list[InMemoryTransport]:
        return [transport for nid, transport in self._transports.items() if nid != node_id]

    def dispatch(self, sender_id: str, command: ModemCommand) -> None:
        match command:
            case BroadcastCommand(data=data):
                self._handle_broadcast(sender_id, data)
            case UnicastCommand(target_id=target_id, data=data):
                self._handle_unicast(sender_id, target_id, data)
            case UnicastWithAckCommand(target_id=target_id, data=data):
                self._handle_unicast_with_ack(sender_id, target_id, data)
            case PingCommand(target_id=target_id):
                self._handle_ping(sender_id, target_id)
            case StatusQueryCommand():
                self._handle_status_query(sender_id)
            case QualityQueryCommand():
                self._handle_quality_query(sender_id)
            case TestRequestCommand(target_id=target_id):
                self._handle_test_request(sender_id, target_id)
            case SetAddressCommand(address=address):
                self._handle_set_address(sender_id, address)
            case RemoteVoltageQueryCommand(target_id=target_id):
                self._handle_remote_voltage_query(sender_id, target_id)
            case EchoCommand(target_id=target_id, data=data):
                self._handle_echo(sender_id, target_id, data)
            case _:
                logger.warning(
                    "InMemoryBus does not simulate %s from node %s",
                    type(command).__name__,
                    sender_id,
                )

    def _handle_broadcast(self, sender_id: str, data: bytes) -> None:
        sender = self.get_transport(sender_id)
        if sender is not None:
            sender.deliver(BroadcastCommandAckEvent(byte_count=len(data)))

        event = ReceivedBroadcastEvent(sender_id=sender_id, data=data)
        for listener in self.get_all_except(sender_id):
            listener.deliver(event)
            self._heard_data_packet[listener.node_id] = True

    def _deliver_unicast_to_target(self, target_id: str, data: bytes) -> bool:
        target = self.get_transport(target_id)
        if target is None:
            return False
        target.deliver(ReceivedUnicastEvent(data=data))
        self._heard_data_packet[target_id] = True
        return True

    def _handle_unicast(self, sender_id: str, target_id: str, data: bytes) -> None:
        if not self._deliver_unicast_to_target(target_id, data):
            return

        sender = self.get_transport(sender_id)
        if sender is not None:
            sender.deliver(
                UnicastCommandAckEvent(target_id=target_id, byte_count=len(data)),
            )

    def _handle_unicast_with_ack(self, sender_id: str, target_id: str, data: bytes) -> None:
        if not self._deliver_unicast_to_target(target_id, data):
            return

        sender = self.get_transport(sender_id)
        if sender is None:
            return
        sender.deliver(
            UnicastWithAckCommandAckEvent(target_id=target_id, byte_count=len(data)),
        )

    def _handle_set_address(self, node_id: str, address: str) -> None:
        transport = self.get_transport(node_id)
        if transport is None:
            return

        if address != node_id:
            if address in self._transports and self._transports[address] is not transport:
                return

            self._transports.pop(node_id, None)
            transport.node_id = address
            self._transports[address] = transport

            if node_id in self._heard_data_packet:
                self._heard_data_packet[address] = self._heard_data_packet.pop(node_id)

        transport.deliver(AddressSetEvent(address=address))

    def _handle_remote_voltage_query(self, sender_id: str, target_id: str) -> None:
        sender = self.get_transport(sender_id)
        if sender is None:
            return

        sender.deliver(RemoteVoltageQueryAckEvent(target_id=target_id))

        target = self.get_transport(target_id)
        if target is None:
            return

        sender.deliver(
            RemoteVoltageResponseEvent(
                responder_id=target_id,
                voltage_raw=MOCK_STATUS_VOLTAGE_RAW,
            ),
        )

    def _handle_echo(self, sender_id: str, target_id: str, data: bytes) -> None:
        sender = self.get_transport(sender_id)
        if sender is None:
            return
        if self.get_transport(target_id) is None:
            return
        sender.deliver(EchoCommandAckEvent(target_id=target_id, byte_count=len(data)))

    def _handle_ping(self, sender_id: str, target_id: str) -> None:
        sender = self.get_transport(sender_id)
        if sender is None:
            return

        sender.deliver(PingCommandAckEvent(target_id=target_id))

        target = self.get_transport(target_id)
        if target is None or sender.position is None or target.position is None:
            sender.deliver(PingTimeoutEvent())
            return

        distance = calculate_distance_3d(
            sender.position,
            sender.depth,
            target.position,
            target.depth,
        )
        timestamp = distance_to_timestamp(distance, self._sound_speed)
        sender.deliver(
            RoundtripResponseEvent(
                responder_id=target_id,
                timestamp_counts=timestamp,
            ),
        )

    def _handle_status_query(self, node_id: str) -> None:
        transport = self.get_transport(node_id)
        if transport is None:
            return
        transport.deliver(
            StatusResponseEvent(
                address=node_id,
                voltage_raw=MOCK_STATUS_VOLTAGE_RAW,
            ),
        )

    def _handle_quality_query(self, node_id: str) -> None:
        transport = self.get_transport(node_id)
        if transport is None:
            return

        if self._heard_data_packet.pop(node_id, False):
            transport.deliver(QualityIndicatorEvent(bytes_corrected=MOCK_BYTES_CORRECTED))
            return

        transport.deliver(QualityRejectedEvent())

    def _handle_test_request(self, sender_id: str, target_id: str) -> None:
        sender = self.get_transport(sender_id)
        if sender is None:
            return

        if self.get_transport(target_id) is None:
            return

        sender.deliver(TestRequestAckEvent(target_id=target_id))

        event = TestBroadcastReceivedEvent(sender_id=target_id)
        for listener in self.get_all_except(target_id):
            listener.deliver(event)
            self._heard_data_packet[listener.node_id] = True


class InMemoryTransport:
    """In-memory WireTransport — simulates modem events without serial encoding."""

    def __init__(self, node_id: str, bus: InMemoryBus) -> None:
        self.node_id = node_id
        self.position: Optional[Coord] = None
        self.get_depth_callback: Optional[Callable[[], float]] = None
        self._bus = bus
        self._callback: OnModemEventCallback | None = None
        bus.register(self)

    @property
    def depth(self) -> float:
        if self.get_depth_callback is not None:
            return self.get_depth_callback()
        return 0.0

    def send_command(self, command: ModemCommand) -> None:
        self._bus.dispatch(self.node_id, command)

    def on_event(self, callback: OnModemEventCallback) -> None:
        self._callback = callback

    def start(self) -> None:
        return

    def stop(self) -> None:
        self._bus.unregister(self.node_id)

    def deliver(self, event: ModemEvent) -> None:
        if self._callback is not None:
            self._callback(event)
