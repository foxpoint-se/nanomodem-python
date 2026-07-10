# Master plan
Outcome: a thin core you can drive from a CLI — serial I/O and wire types separated from LBL and demo glue.
Rule: do not commit anything under `plans/` during steps 1–10 (keep plan docs local until refactor is done).
- [x] **1.** Package skeleton — `nanomodem.core` + `nanomodem.positioning` ([open-decisions.md](./open-decisions.md))
- [x] **2.** Wire types — `ModemCommand` / `ModemEvent` ([wire-protocol.md](./wire-protocol.md))
- [x] **3.** Driver — parse/format only, no codec ([wire-protocol.md](./wire-protocol.md))
- [x] **4.** `ModemNode` + `PayloadCodec[T]` in core ([layering.md](./layering.md))
- [x] **5.** Transports — `InMemoryTransport`, serial via driver ([inventory.md](./inventory.md))
- [x] **6.** Positioning — `PositioningNode`, move LBL types ([inventory.md](./inventory.md))
- [x] **7.** Demo — move simulator glue out of core ([inventory.md](./inventory.md))
- [x] **8.** Cleanup — drop compat aliases, id check in apps, major bump ([open-decisions.md](./open-decisions.md))
- [x] **9.** Bump evaluating-nanomodem — adopt new API; smoke-test that it still works (v3.0.0, `419f503` on main)
- [x] **9b.** Finish demo transport rename — [open-decisions.md](./open-decisions.md) #7: `NetworkMockTransport` → `SimulatorJsonTransport` in `transports/simulator_json.py`
- [ ] **10.** CLI ([cli-use-cases.md](./cli-use-cases.md), [cli-open-decisions.md](./cli-open-decisions.md))
  - [x] **10a.** Package skeleton — `nanomodem-cli`, argparse, serial one-shots (`status`, `ping`)
  - [ ] **10b.** REPL — session model, `node`, `use`, in-memory bus
  - [ ] **10c.** Rest — `listen`, `cmd`, logging, completion/help
