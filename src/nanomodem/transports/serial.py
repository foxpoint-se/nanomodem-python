"""SerialTransport -- real serial transport for acoustic modem hardware.

Wraps a serial port. Uses a DriverProtocol for command formatting
and response parsing. Handles the serial I/O and background reader thread.

Serial format: 9600,8,n,1, no flow control.
All modem responses are terminated with CR+LF.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

import serial

from ..protocols import DriverProtocol, OnMessageCallback
from ..serial_logger import format_serial_log
from ..types import Coord

logger = logging.getLogger(__name__)


class SerialTransport:
    """Transport implementation for real serial hardware.

    Reads lines from serial in a background thread and delivers
    typed Message objects to the registered callback via the driver.
    """

    def __init__(
        self,
        node_id: str,
        port: str,
        driver: DriverProtocol,
        baud: int = 9600,
        timeout: float = 0.1,
    ) -> None:
        self.node_id = node_id
        self._driver = driver
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
            name=f"serial-{node_id}-reader",
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

    def broadcast_position(self, coord: Coord, depth: float) -> None:
        cmd = self._driver.format_broadcast(self.node_id, coord, depth)
        self._write(cmd)

    def request_range(self, target_id: str) -> None:
        cmd = self._driver.format_ping(target_id)
        self._write(cmd)

    def request_test(self, target_id: str) -> None:
        cmd = self._driver.format_test_request(target_id)
        self._write(cmd)

    def query_quality(self) -> None:
        cmd = self._driver.format_quality_query()
        self._write(cmd)

    def query_modem_status(self) -> None:
        cmd = self._driver.format_status_query()
        self._write(cmd)

    def on_message(self, callback: OnMessageCallback) -> None:
        self._callback = callback

    def _write(self, data: bytes) -> None:
        with self._lock:
            self._serial.write(data)
            logger.info(format_serial_log("TX", self.node_id, data))

    def _read_loop(self) -> None:
        """Background thread: read lines from serial and dispatch."""
        while self._running:
            try:
                raw = self._serial.readline()
                if not raw:
                    continue
                logger.info(format_serial_log("RX", self.node_id, raw))
                line = raw.decode("ascii", errors="replace").strip()
                if not line:
                    continue
                self._dispatch(line)
            except serial.SerialException:
                logger.exception("Serial error")
                break
            except Exception:
                logger.exception("Unexpected error in reader thread")

    def _dispatch(self, line: str) -> None:
        """Parse a serial line via the driver and deliver to the callback."""
        msg = self._driver.parse_line(line)
        if self._callback is not None:
            self._callback(msg)
