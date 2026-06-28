"""Built-in payload codecs for ModemNode."""

from __future__ import annotations


class RawPayloadCodec:
    """Default codec that passes bytes through unchanged."""

    def encode(self, payload: bytes) -> bytes:
        return payload

    def decode(self, data: bytes) -> bytes:
        return data
