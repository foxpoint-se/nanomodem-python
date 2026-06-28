"""Protocol interfaces for the core modem layer."""

from __future__ import annotations

from typing import Callable, Protocol, TypeVar

from .wire_types import ModemCommand, ModemEvent

T = TypeVar("T")

OnModemEventCallback = Callable[[ModemEvent], None]


class PayloadCodec(Protocol[T]):
    """Encode and decode application payloads carried in broadcast/unicast data."""

    def encode(self, payload: T) -> bytes: ...

    def decode(self, data: bytes) -> T: ...


class WireTransport(Protocol):
    """Low-level transport for ModemCommand / ModemEvent I/O."""

    def send_command(self, cmd: ModemCommand) -> None: ...

    def on_event(self, callback: OnModemEventCallback) -> None: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...
