"""Modem protocol relay helpers.

Pure functions that simulate what nanomodem v3 hardware does when routing
messages between nodes. Used by virtual serial bridge scenarios.

All formats are per the nanomodem v3 user guide (section 5.2):

  Broadcast:
    Sender sends:   $Bnn{body}
    Sender gets:    $Bnn\\r\\n          (immediate ack)
    Others get:     #B{xxx}nn{body}\\r\\n  (where xxx is sender address)

  Ping:
    Sender sends:   $Pxxx
    Sender gets:    $Pxxx\\r\\n         (immediate ack)
    Sender gets:    #RxxxTyyyyy\\r\\n   (range response, after acoustic round-trip)

  Status:
    Sender sends:   $?
    Sender gets:    #AxxxVyyyyy\\r\\n   (node address and supply voltage raw)
"""

from __future__ import annotations

import math
import re

_BROADCAST_CMD_RE = re.compile(rb"^\$B(\d{2})(.+)$")
_PING_CMD_RE = re.compile(rb"^\$P(\d{3})$")

SOUND_SPEED_DEFAULT = 1500.0  # m/s


# ------------------------------------------------------------------ #
#  Broadcast                                                           #
# ------------------------------------------------------------------ #


def split_modem_command(buffer: bytes) -> tuple[bytes, bytes] | None:
    """Extract one complete outbound command from a serial buffer.

    Modem commands have no line terminator. Returns (command, remainder) or None
    if the buffer does not yet contain a full command.
    """
    buf = buffer.lstrip()
    if buf.startswith(b"$B"):
        if len(buf) < 4:
            return None
        body_len = int(buf[2:4])
        total = 4 + body_len
        if len(buf) < total:
            return None
        return buf[:total], buf[total:]
    if buf.startswith(b"$?"):
        if len(buf) < 2:
            return None
        return buf[:2], buf[2:]
    if buf.startswith(b"$P"):
        if len(buf) < 5:
            return None
        return buf[:5], buf[5:]
    return None


def parse_broadcast(raw: bytes) -> tuple[str, bytes] | None:
    """Parse a broadcast command. Returns (nn, body) or None."""
    m = _BROADCAST_CMD_RE.match(raw.strip())
    if not m:
        return None
    return m.group(1).decode("ascii"), m.group(2)


def broadcast_ack(nn: str) -> bytes:
    """Immediate ack to sender: $Bnn\\r\\n."""
    return f"$B{nn}\r\n".encode("ascii")


def broadcast_relay(sender_id: str, nn: str, body: bytes) -> bytes:
    """Message delivered to all other nodes: #B{sender_id}{nn}{body}\\r\\n."""
    return f"#B{sender_id}{nn}".encode("ascii") + body + b"\r\n"


# ------------------------------------------------------------------ #
#  Ping                                                                #
# ------------------------------------------------------------------ #


def parse_ping(raw: bytes) -> str | None:
    """Parse a ping command. Returns target_id or None."""
    m = _PING_CMD_RE.match(raw.strip())
    if not m:
        return None
    return m.group(1).decode("ascii")


def ping_ack(target_id: str) -> bytes:
    """Immediate ack to sender: $P{target_id}\\r\\n."""
    return f"$P{target_id}\r\n".encode("ascii")


def range_response(target_id: str, distance: float, sound_speed: float = SOUND_SPEED_DEFAULT) -> bytes:
    """Range response to sender: #R{target_id}T{timestamp:05d}\\r\\n.

    Timestamp formula per user guide: R = yyyyy * c * 3.125e-5
    """
    timestamp = round((distance / sound_speed) / 3.125e-5)
    return f"#R{target_id}T{timestamp:05d}\r\n".encode("ascii")


# ------------------------------------------------------------------ #
#  Status query ($?)                                                   #
# ------------------------------------------------------------------ #


def parse_status_query(raw: bytes) -> bool:
    """True if raw is a modem status query ($?)."""
    return raw.strip() == b"$?"


def status_response(node_id: str, voltage_raw: int) -> bytes:
    """Status response to sender: #A{node_id}V{voltage_raw:05d}\\r\\n."""
    return f"#A{node_id}V{voltage_raw:05d}\r\n".encode("ascii")


# ------------------------------------------------------------------ #
#  Distance                                                            #
# ------------------------------------------------------------------ #


def distance_metres(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> float:
    """Euclidean distance in metres using flat-earth approximation.

    - 1 degree lat  ~ 111320 m
    - 1 degree lon  ~ 111320 * cos(lat) m
    """
    lat_a, lon_a, depth_a = a
    lat_b, lon_b, depth_b = b
    lat_m = (lat_b - lat_a) * 111320.0
    avg_lat = math.radians((lat_a + lat_b) / 2.0)
    lon_m = (lon_b - lon_a) * 111320.0 * math.cos(avg_lat)
    depth_m = depth_b - depth_a
    return math.sqrt(lat_m**2 + lon_m**2 + depth_m**2)
