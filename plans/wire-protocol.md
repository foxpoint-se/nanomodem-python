# Wire protocol types (nanomodem v3)

**Execution order:** [master-plan.md](./master-plan.md) steps 2–3. Reference for driver-layer types in `nanomodem.core`. Maps [user guide](../docs/nanomodem_v3_user_guide.md) commands and responses.

**Rules**

- Event/command fields = parsed line fields only. No inferred metadata.
- Driver produces `ModemEvent`; driver consumes `ModemCommand`. No codec at this layer.
- `#RxxxTyyyyy` is one event type — same line for ping (`$P`) and delivery ack (`$M`).
- `#U` has no sender id on the wire; `#B` includes sender id (`xxx`).

Decisions: [open-decisions.md](./open-decisions.md) #24–26.

---

## `ModemCommand` (host → modem)

```python
ModemCommand = (
    SetAddressCommand              # $Axxx
    | StatusQueryCommand           # $?
    | PingCommand                  # $Pxxx
    | RemoteVoltageQueryCommand    # $Vxxx
    | BroadcastCommand             # $Bnnddd…
    | UnicastCommand               # $Uxxxnnddd…
    | UnicastWithAckCommand        # $Mxxxnnddd…
    | TestRequestCommand           # $Txxx
    | EchoCommand                  # $Exxxnnddd…
    | QualityQueryCommand          # $Q
)
```

| Type | Fields |
|------|--------|
| `SetAddressCommand` | `address: str` (3-digit) |
| `StatusQueryCommand` | — |
| `PingCommand` | `target_id: str` |
| `RemoteVoltageQueryCommand` | `target_id: str` |
| `BroadcastCommand` | `data: bytes` |
| `UnicastCommand` | `target_id: str`, `data: bytes` |
| `UnicastWithAckCommand` | `target_id: str`, `data: bytes` |
| `TestRequestCommand` | `target_id: str` |
| `EchoCommand` | `target_id: str`, `data: bytes` |
| `QualityQueryCommand` | — |

---

## `ModemEvent` (modem → host)

Top level follows line prefix (`$` / `#` / error):

```python
ModemEvent = LocalAckEvent | ReceivedEvent | ErrorEvent
```

### `LocalAckEvent` — `$…` (immediate local acknowledgement)

```python
LocalAckEvent = (
    PingCommandAckEvent            # $Pxxx
    | TestRequestAckEvent          # $Txxx
    | BroadcastCommandAckEvent     # $Bnn
    | UnicastCommandAckEvent       # $Uxxxnn
    | UnicastWithAckCommandAckEvent  # $Mxxxnn
    | RemoteVoltageQueryAckEvent   # $Vxxx
    | EchoCommandAckEvent          # $Exxxnn
    | QualityIndicatorEvent        # $Cx
    | QualityRejectedEvent         # $C-
)
```

| Type | Fields |
|------|--------|
| `PingCommandAckEvent` | `target_id: str` |
| `TestRequestAckEvent` | `target_id: str` |
| `BroadcastCommandAckEvent` | `byte_count: int` |
| `UnicastCommandAckEvent` | `target_id: str`, `byte_count: int` |
| `UnicastWithAckCommandAckEvent` | `target_id: str`, `byte_count: int` |
| `RemoteVoltageQueryAckEvent` | `target_id: str` |
| `EchoCommandAckEvent` | `target_id: str`, `byte_count: int` |
| `QualityIndicatorEvent` | `bytes_corrected: int` |
| `QualityRejectedEvent` | — |

### `ReceivedEvent` — `#…` (acoustic / delayed result)

```python
ReceivedEvent = (
    AddressSetEvent                # #Axxx
    | StatusResponseEvent          # #AxxxVyyyyy
    | RoundtripResponseEvent       # #RxxxTyyyyy
    | PingTimeoutEvent             # #TO
    | RemoteVoltageResponseEvent   # #Bxxx06Vyyyyy
    | ReceivedBroadcastEvent       # #Bxxxnnddd…
    | TestBroadcastReceivedEvent   # #Bxxx64{fixed payload}
    | ReceivedUnicastEvent         # #Unnddd…
)
```

| Type | Fields |
|------|--------|
| `AddressSetEvent` | `address: str` |
| `StatusResponseEvent` | `address: str`, `voltage_raw: int` |
| `RoundtripResponseEvent` | `responder_id: str`, `timestamp_counts: int` |
| `PingTimeoutEvent` | — |
| `RemoteVoltageResponseEvent` | `responder_id: str`, `voltage_raw: int` |
| `ReceivedBroadcastEvent` | `sender_id: str`, `data: bytes` |
| `TestBroadcastReceivedEvent` | `sender_id: str` |
| `ReceivedUnicastEvent` | `data: bytes` |

### `ErrorEvent`

```python
ErrorEvent = (
    CommandErrorEvent              # E
    | UnknownLineEvent             # unparsed line
)
```

| Type | Fields |
|------|--------|
| `CommandErrorEvent` | — |
| `UnknownLineEvent` | `raw: str` |

---

## Replaces (today)

| Today | Wire type |
|-------|-----------|
| `Message` union | `ModemEvent` |
| `LocalAckMessage` | variants under `LocalAckEvent` |
| `RangeResponseMessage` | `RoundtripResponseEvent` |
| `ModemStatusMessage` | `StatusResponseEvent` |
| `QualityIndicatorMessage` | `QualityIndicatorEvent` / `QualityRejectedEvent` |
| `V3TestBroadcastMessage` | `TestBroadcastReceivedEvent` |
| `UnknownMessage` | `UnknownLineEvent` |
| `PositionMessage` (from driver decode) | `ReceivedBroadcastEvent` / `ReceivedUnicastEvent` — decode in `ModemNode` |
