 ### I say

Hmmmm.. It is alright, but not perfect.
I would hope that the driver would be very generic. The one we'll have now is the V3 driver. This complies with the specs of the hardware, as described in the @docs/nanomodem_v3_user_guide.md 

I was hoping that this could be "provided" in this lib. For 99% of use cases, u just import that one. Because it has the correct protocol as stated in the user guide. Maybe one day there will be an updated nanomodem... v4 perhaps. In theory, u would just have to use another driver.

The codec feels like it is working like this. That u just encode whatever u want in the body. Write your own codec if u want. Or please do that. Ours is probably shit, or it doesn't solve your use case. But the ping, broadcast, unicast "methods" of the userguide (this is what the hardware provides) should be the same for everyone. So it is a shame if our driver has hardcoded that a range request always means a ping.

What is your take? If u think it this would be better, then how would that work? And are there any drawbacks?

### Agent says

You're right, and the spec confirms it. Look at $M:

$Mxxxnnddd… -- Unicast data and acknowledge. [...] If message has been delivered the sending unit will receive #RxxxTyyyyy where yyyyy is the range count as in the ping command.

So $M gives you both data delivery AND range measurement in one round-trip. Hardcoding "range request = ping" means you can't use that. The hardware provides distinct primitives, and the driver should expose them faithfully.

How it would work:

The driver mirrors the hardware command set directly:

```python
class DriverProtocol(Protocol):
    # Formatting (outgoing)
    def format_ping(self, target_id: str) -> bytes: ...
    def format_broadcast(self, payload: bytes) -> bytes: ...
    def format_unicast(self, target_id: str, payload: bytes) -> bytes: ...
    def format_unicast_with_ack(self, target_id: str, payload: bytes) -> bytes: ...
    # Parsing (incoming)
    def parse_line(self, line: str) -> DriverResponse: ...

# The transport exposes the same primitives (not domain operations):
class TransportProtocol(Protocol):
    def ping(self, target_id: str) -> None: ...
    def broadcast(self, payload: bytes) -> None: ...
    def unicast(self, target_id: str, payload: bytes) -> None: ...
    def unicast_with_ack(self, target_id: str, payload: bytes) -> None: ...
    def on_response(self, callback: Callable[[DriverResponse], None]) -> None: ...

# The response types also mirror the hardware (not domain concepts):
DriverResponse = PingResponse | BroadcastReceived | UnicastReceived | Timeout | UnknownResponse

# Then the Node owns the domain mapping and the codec:
class AcousticNode:
    def __init__(self, transport: TransportProtocol, codec: CodecProtocol, ...):
        ...

    def broadcast_position(self) -> None:
        payload = self._codec.encode_position(self._node_id, self._position, self._depth)
        self._transport.broadcast(payload)

    def request_range(self, target_id: str) -> None:
        self._transport.ping(target_id)  # user could change this

    def _handle_response(self, resp: DriverResponse) -> None:
        match resp:
            case PingResponse(node_id=nid, timestamp=ts):
                distance = self._calc.timestamp_to_distance(ts, ...)
                ...
            case BroadcastReceived(body=body):
                msg = self._codec.decode(body)
                # could be PositionMessage, or whatever the codec produces
                ...
```

Drawbacks:

Node gets a codec dependency. Currently the Node doesn't know about encoding -- it just calls transport.broadcast_position(coord, depth) and the transport handles it. With this change, the Node imports and uses the codec. More DI, but arguably correct since the Node is the domain layer.

Mock scenarios need a codec. Currently MockTransport works at the message level (it delivers PositionMessage directly). With hardware-primitive transport, MockTransport.broadcast(payload) delivers raw bytes, and the receiving node's codec decodes them. One extra line in test setup, but also more realistic.

Two type layers. You'd have hardware-level responses (PingResponse, BroadcastReceived) and domain-level messages (PositionMessage, etc. from the codec). The current single Message type splits into two concerns. Slightly more to think about, but each type is simpler.

Agent's take: the drawbacks are mild and the gain is real. The driver becomes a genuine, reusable hardware API that anyone can import. The user decides what's a "range request." And when nanomodem v4 comes out, you write a new driver and everything else stays the same.


===

My take:
We should probably change from a ping to something else. And this breaks things.
Although, we don't want codecs spilling into the mocks. So then you could of course create a new transport, that does it differently.
But the "generic transport" could be the raw functions. And you could use that for whatever u wanna do, so you would pass in the transport into your "functionality thing", whatever that is? We have to come up with a name for that. But if u are designing an application, then you'd have buttons or other triggers. These triggers are triggering things u have decided, so in this "thing" u define "now use the ping message for this". But that is kinda how it works today? So I dunno.
Something for another day.