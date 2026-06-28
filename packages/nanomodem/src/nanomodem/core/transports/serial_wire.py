"""Serial wire transport for real nanomodem hardware."""

from __future__ import annotations

import logging
import threading
from typing import Optional

import serial

from nanomodem.serial_logger import format_serial_log

from ..driver import NanomodemV3Driver
from ..protocols import OnModemEventCallback
from ..wire_types import ModemCommand

logger = logging.getLogger(__name__)


class SerialWireTransport:
    """WireTransport over a serial port using NanomodemV3Driver."""

    def __init__(
        self,
        port: str,
        driver: NanomodemV3Driver,
        baud: int = 9600,
        timeout: float = 0.1,
    ) -> None:
        self._port = port
        self._driver = driver
        self._callback: Optional[OnModemEventCallback] = None
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
            name=f"serial-wire-{port}-reader",
        )
        self._reader_started = False
        self._stopped = False

    @property
    def port(self) -> str:
        return self._port

    def send_command(self, command: ModemCommand) -> None:
        data = self._driver.format_command(command)
        self._write(data)

    def on_event(self, callback: OnModemEventCallback) -> None:
        self._callback = callback

    def start(self) -> None:
        if self._reader_started:
            return
        self._running = True
        self._reader_thread.start()
        self._reader_started = True

    def stop(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        self._running = False
        if self._reader_started:
            self._reader_thread.join(timeout=2.0)
        if self._serial.is_open:
            self._serial.close()

    def _write(self, data: bytes) -> None:
        with self._lock:
            self._serial.write(data)
            logger.info(format_serial_log("TX", self._port, data))

    def _read_loop(self) -> None:
        while self._running:
            try:
                raw = self._serial.readline()
                if not raw:
                    continue
                logger.info(format_serial_log("RX", self._port, raw))
                line = raw.decode("ascii", errors="replace").strip()
                if not line:
                    continue
                self._dispatch(line)
            except serial.SerialException:
                logger.exception("Serial error on %s", self._port)
                break
            except Exception:
                logger.exception("Unexpected error in reader thread for %s", self._port)

    def _dispatch(self, line: str) -> None:
        event = self._driver.parse_line(line)
        if self._callback is not None:
            self._callback(event)
