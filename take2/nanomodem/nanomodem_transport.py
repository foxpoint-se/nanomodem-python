"""NanomodemTransport — real serial transport for nanomodem hardware.

Wraps a serial port. Uses Codec to decode message bodies.
Handles $ (local ack) and # (result) prefixes.
Nothing received on serial is ever silently dropped — everything
becomes a typed Message object delivered to the node.

Serial format: 9600,8,n,1, no flow control.
All modem responses are terminated with CR+LF.

Protocol reference: nanomodem_v3_user_guide.md
"""

from __future__ import annotations

import logging
import re
import threading
from typing import Optional

import serial

from .codec import CodecInterface
from .transport import OnMessageCallback
from .types import (
    Coord,
    Message,
    RangeResponseMessage,
    UnknownMessage,
)

logger = logging.getLogger(__name__)

# Response patterns from the modem
# #RxxxTyyyyy — range response (from ping or unicast-with-ack)
RANGE_RESPONSE_RE = re.compile(r"^#R(\d{3})T(\d{5})$")
# #Bxxxnnddd... — incoming broadcast data
BROADCAST_DATA_RE = re.compile(r"^#B(\d{3})(\d{2})(.+)$")
# #Unnddd... — incoming unicast data (no sender ID from modem!)
UNICAST_DATA_RE = re.compile(r"^#U(\d{2})(.+)$")


class NanomodemTransport:
    """Transport implementation for real nanomodem serial hardware.

    Reads lines from serial in a background thread and delivers
    typed Message objects to the registered callback.
    """

    def __init__(
        self,
        node_id: str,
        port: str,
        codec: CodecInterface,
        baud: int = 9600,
        timeout: float = 0.1,
    ) -> None:
        self.node_id = node_id
        self._codec = codec
        self._callback: Optional[OnMessageCallback] = None
        self._running = False
        self._lock = threading.Lock()

        self._serial = serial.Serial(
            port=port,
            baudrate=baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
        )

        self._reader_thread = threading.Thread(
            target=self._read_loop,
            daemon=True,
            name=f"nanomodem-{node_id}-reader",
        )

    def start(self) -> None:
        """Start the background serial reader thread."""
        self._running = True
        self._reader_thread.start()

    def stop(self) -> None:
        """Stop the background reader and close the serial port."""
        self._running = False
        self._reader_thread.join(timeout=2.0)
        self._serial.close()

    # --- TransportInterface methods ---

    def broadcast_position(self, coord: Coord, depth: float) -> None:
        """Broadcast position using $Bnnddd... command."""
        payload = self._codec.encode_position(self.node_id, coord, depth)
        nn = f"{len(payload):02d}"
        cmd = f"$B{nn}".encode("ascii") + payload
        self._write(cmd)

    def request_range(self, target_id: str) -> None:
        """Send ping using $Pxxx command."""
        cmd = f"$P{target_id}".encode("ascii")
        self._write(cmd)

    def on_message(self, callback: OnMessageCallback) -> None:
        self._callback = callback

    # --- Internal ---

    def _write(self, data: bytes) -> None:
        """Write bytes to serial port."""
        with self._lock:
            self._serial.write(data)
            logger.debug("TX: %s", data)

    def _read_loop(self) -> None:
        """Background thread: read lines from serial and dispatch."""
        while self._running:
            try:
                raw = self._serial.readline()
                if not raw:
                    continue
                line = raw.decode("ascii", errors="replace").strip()
                if not line:
                    continue
                logger.debug("RX: %s", line)
                self._dispatch(line)
            except serial.SerialException:
                logger.exception("Serial error")
                break
            except Exception:
                logger.exception("Unexpected error in reader thread")

    def _dispatch(self, line: str) -> None:
        """Parse a serial line and deliver a typed Message to the callback.

        Nothing is silently dropped. Everything becomes a Message.
        """
        msg = self._parse_line(line)
        if self._callback is not None:
            self._callback(msg)

    def _parse_line(self, line: str) -> Message:
        """Parse a single line from the modem into a typed Message.

        Known patterns:
          - #RxxxTyyyyy  → RangeResponseMessage
          - #Bxxxnnddd... → decode broadcast body via codec
          - #Unnddd...  → decode unicast body via codec
          - Everything else → UnknownMessage (nothing lost)
        """
        # Range response
        m = RANGE_RESPONSE_RE.match(line)
        if m:
            node_id = m.group(1)
            timestamp = int(m.group(2))
            return RangeResponseMessage(node_id=node_id, timestamp=timestamp)

        # Broadcast data — decode body via codec
        m = BROADCAST_DATA_RE.match(line)
        if m:
            sender_id = m.group(1)
            _nn = m.group(2)
            body = m.group(3)
            return self._codec.decode(body.encode("ascii"))

        # Unicast data — decode body via codec (sender ID is in payload)
        m = UNICAST_DATA_RE.match(line)
        if m:
            _nn = m.group(1)
            body = m.group(2)
            return self._codec.decode(body.encode("ascii"))

        # Everything else: local acks ($...), errors (E), timeouts (#TO), etc.
        return UnknownMessage(raw=line)
