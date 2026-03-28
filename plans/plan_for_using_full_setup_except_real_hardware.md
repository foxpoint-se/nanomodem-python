# Plan: Full Integration Test Without Real Hardware

**Goal:** Verify the full stack (real `SerialTransport`, real codec, real driver) works end-to-end using virtual serial ports — so that when we put it in water, we're confident.

---

### Phase 1: Serial Broker (the "fake water")
*Goal: A running broker that links two virtual serial port pairs and prints every raw byte it sees.*

- [x] Create `scripts/serial_broker.py` — a standalone script
- [x] Use `socat` to create two virtual serial pairs (documented in the script's usage comment)
- [x] Broker reads from both ports, relays bytes in both directions
- [x] Broker logs every raw line to stdout with direction and timestamp (e.g. `[A→B] $B32P001...`)
- [x] When broker sees `$Pxxx`, synthesize a `#RxxxTyyyyy` response back to sender using hardcoded positions
- [x] Hardcoded node positions are defined at top of script (easy to change)
- [x] Figure out if we should add any of this to the "convenient scripts" defined in toml or Makefile or similar
- [x] Find out if there are unit tests that should be added at this point

**Outcome:** Run `python scripts/serial_broker.py` and see a live bus monitor in the terminal.

---

### Phase 2: New Launch Scenario
*Goal: Two nodes running with `SerialTransport`, pointed at the virtual ports, using the real driver and codec.*

- [ ] Create `src/nanomodem/gui/scenarios/serial_bridge_2_nodes.py`
- [ ] Wire up two `ControllerWindow`s, each using `SerialTransport` on their respective virtual TTY
- [ ] Pass `get_sim_pos_callback` / `set_sim_pos_callback` that read/write into the broker's position table
- [ ] Node A gets the sim pos panel (movable); Node B is static (no sim callbacks)
- [ ] Add a `make run-bridge` Makefile target to launch this scenario
- [ ] Find out if there are unit tests that should be added at this point

**Outcome:** Two GUI windows open. Broker is running. Everything wired.

---

### Phase 3: Verify End-to-End Behaviour
*Goal: Manually walk through the real scenario and confirm everything behaves as expected.*

- [ ] Node A broadcasts position → broker relays raw bytes → Node B receives and updates registry
- [ ] Node A requests range to Node B → broker synthesizes `#R` response → Node A computes distance
- [ ] Move Node A's sim pos in GUI → broker uses new position → range value changes accordingly
- [ ] Inspect broker terminal to confirm codec output looks correct (32-byte position body, etc.)
- [ ] Find out if there are unit tests that should be added at this point

**Outcome:** Everything behaves exactly as it will in water, verified visually.

---

### Phase 4: Complementary things
- [ ] Maybe (probably?) move the serial broker from scripts to gui so it is available when installing with [gui] option
- [ ] Maybe rename the [gui] profile to something more descriptive? Dev? Demo?
- [ ] Consolidate the broker. Should be one thing, used across all scripts or launch files that need it.
- [ ] Go through everything and see if anything smells.