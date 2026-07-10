# Open decisions — move & maybe

**Execution order:** [master-plan.md](./master-plan.md). This file records *what* we decided; master plan records *when* to do it.

Subset of [inventory.md](./inventory.md). Discuss these one by one. Say **next** to advance.

**Policy:** No backwards-compat aliases. Breaking renames/moves ship as a major version bump.

**Package layout (decided):** `nanomodem.core.*` (wire, driver, transports, `ModemNode`) · `nanomodem.positioning.*` (LBL abstractions — `PositioningNode`, `Calculation`, etc.)

---

## move

### Positioning layer (out of core)

| # | Name | Today | Target | Decision |
|---|------|-------|--------|----------|
| 1 | `AcousticNode` | `node.py` | `PositioningNode` (app layer) | **Yes** — `nanomodem.positioning`; breaking rename |
| 2 | `Calculation` | `calculation.py` | positioning layer | **Yes** — `nanomodem.positioning` |
| 3 | `calculate_distance_3d` | `calculation.py` | positioning layer or demo | **Yes** — `nanomodem.core` (generic geo, no LBL assumption) |
| 4 | `CalculationProtocol` | `protocols.py` | positioning layer | **Yes** — `nanomodem.positioning`; keep protocol for now |
| 5 | `KnownNode` | `types.py` | positioning layer | **Yes** — `nanomodem.positioning` |
| 6 | `NodeCapabilities` | `types.py` | positioning layer | **Yes** — `nanomodem.positioning` |

### Core → demo (God View / simulator glue)

| # | Name | Today | Decision |
|---|------|-------|----------|
| 7 | `NetworkMockTransport` | `transports/network.py` | **Partial** — moved to `nanomodem_demo`; rename to `SimulatorJsonTransport` (`transports/simulator_json.py`) **still TODO** (step 9b, before CLI) |
| 8 | `SimulatorMetadataClient` | `simulator_protocol.py` | **Move** → `nanomodem-demo` (God View side channel only) |
| 9 | `SimulatorInboundHandlers` | `simulator_protocol.py` | **Move** → `nanomodem-demo` |
| 10 | `JsonLineBuffer` | `simulator_protocol.py` | **Move** → `nanomodem-demo` |
| 11 | `build_registration`, `build_transmit`, `send_json_line` | `simulator_protocol.py` | **Move** → `nanomodem-demo` |
| 12 | `dispatch_simulator_*` | `simulator_protocol.py` | **Move** → `nanomodem-demo` |
| 13 | `AcousticTransportConfig` | `sim_types.py` | **Move** → `nanomodem-demo` |
| 14 | `NodeRegistration` | `sim_types.py` | **Move** → `nanomodem-demo` |
| 15 | `TransmitMessage` | `sim_types.py` | **Move** → `nanomodem-demo` |
| 16 | `AcousticMessageEvent` | `sim_types.py` | **Move** → `nanomodem-demo` |
| 17 | `GPSUpdateMessage` | `sim_types.py` | **Move** → `nanomodem-demo` |
| 18 | `tests/test_simulator_protocol.py` | move with #8–12 | **Move** → `nanomodem-demo/tests/` |

---

## maybe

### Renames

| # | Name | Today | Candidate | Decision |
|---|------|-------|-----------|----------|
| 19 | `Codec` | `codecs/v3.py` | `BasicPositionCodec` | **Yes** — `nanomodem.positioning`; implements `PayloadCodec[PositionMessage]` |
| 20 | `CodecProtocol` | `protocols.py` | `PayloadCodec[T]` | **Yes** — `nanomodem.core`; `encode(T)->bytes`, `decode(bytes)->T`. Default impl: `RawPayloadCodec` (`PayloadCodec[bytes]`) |
| 21 | `MockTransport` | `transports/mock.py` | `InMemoryTransport` | **Yes** — `nanomodem.core.transports.in_memory` |
| 22 | `MockEther` | `transports/mock.py` | `InMemoryBus` | **Yes** — private impl detail of in-memory transport (not public API) |
| 23 | `transports/mock.py` | module path | `transports/in_memory.py` | **Yes** |

### Splits / new types

| # | Item | Notes | Decision |
|---|------|-------|----------|
| 24 | `Message` union | Split wire types vs app types? | **Yes** — `ModemEvent` = `LocalAckEvent \| ReceivedEvent \| ErrorEvent` in `nanomodem.core`; app decode → **Body** types in `nanomodem.positioning`. See [wire-protocol.md](./wire-protocol.md) |
| 25 | Wire protocol types | Full user-guide coverage | **Yes** — `ModemCommand` + nested `ModemEvent` variants; wire fields only; no `PayloadBytes`. See [wire-protocol.md](./wire-protocol.md) |
| 26 | Driver vs codec | Driver returns wire events; codec in `ModemNode`? | **Yes** — driver: `ModemCommand` ↔ bytes, line → `ModemEvent` only; `ModemNode` decodes `ReceivedBroadcastEvent` / `ReceivedUnicastEvent` via `PayloadCodec[T]` |

### Shared helpers

| # | Name | Today | Notes | Decision |
|---|------|-------|-------|----------|
| 27 | `verify_modem_id_at_startup` | `nanomodem_demo/startup.py` | Share via core or future CLI? | **Yes** — not in core; drop `ensure_modem_id_matches` from `ModemNode`; core only exposes `$?` → `StatusResponseEvent`; demo/eval/CLI compare ids and exit on mismatch |

### Planned (not in repo)

| # | Name | Notes | Decision |
|---|------|-------|----------|
| 28 | `ModemNode` | New thin core entry — where does RX decode live? | **Yes** — `nanomodem.core`; generic `ModemNode[T]`; default `RawPayloadCodec` (not nullable); `PositioningNode` wraps with `PayloadCodec[PositionMessage]` |
| 29 | `nanomodem-cli` | New package — depends on layering choices above | **Defer** — new package after core/positioning/demo moves land; no CLI work until refactor is done |
