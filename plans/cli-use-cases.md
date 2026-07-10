# nanomodem-cli — use cases

Consumer-facing UX for **`nanomodem-cli`** (binary: **`nanomodem`**). Snippets are the target behavior — not all implemented yet.

**Decisions:** [cli-open-decisions.md](./cli-open-decisions.md) · **Status:** blocked on step 9b (demo transport rename), then step 10.

---

## Install

Field / boat laptop — one binary on `$PATH`:

```bash
pipx install "git+https://github.com/foxpoint-se/nanomodem-python.git#subdirectory=packages/nanomodem-cli"
nanomodem --help
```

Repo development:

```bash
make install
uv run nanomodem --help
```

**Dependency:** `nanomodem` only (serial + in-memory). No GUI, no demo package.

**Out of scope for this CLI:** God View / TCP simulator (use **`nanomodem-demo`**: `nanomodem-simulator` + `nanomodem-controller`), LBL/positioning (separate CLI later).

---

## Mental model

| You type | What happens |
|---|---|
| `nanomodem` | Interactive REPL |
| `nanomodem -n 001 -s …` | REPL with first node bootstrapped |
| `nanomodem status …` | One-shot: run command, print result, exit |

No `repl` subcommand — bare **`nanomodem`** *is* the REPL (like `redis-cli`).

Verbs `status`, `ping`, `listen`, `cmd` → one-shot. Anything else at the top level → REPL.

**Stack:** `ModemNode` + `RawPayloadCodec` — wire/modem tool. `ping` parses `#R…` and prints range in meters (uses `--sound-speed`, default 1500 m/s).

**Connection:** always via flags — never positional transport args.

| Flag | Meaning |
|---|---|
| `-n` / `--node-id ID` | Modem node id (e.g. `001`) |
| `-s PATH` / `--serial PATH` | Real hardware on serial port |
| `-m` / `--in-memory` | Simulated acoustic bus (in-process) |
| `--baud N` | Serial baud (default 9600) |
| `--sound-speed M` | Speed of sound for range (default 1500) |
| `--log-events` | Print parsed modem events |
| `--log-wire` | Print raw wire bytes (serial only) |

Pick **exactly one** transport: `-s` or `-m`.

REPL with **no transport flags** → defaults to **in-memory** (`-m`).

---

## One-shot (serial)

Run a single command against one modem, then exit.

**Exit code** (for scripts: `echo $?` after the command):

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Failure — ping timeout, modem id mismatch on `status`, bad args |

The REPL does not set exit codes per command; only one-shots exit with `0`/`1`.

**Ping a peer and exit:**

```bash
nanomodem -n 001 -s /dev/ttyUSB0 ping 002
# stdout: range line, e.g. "range 002: 1234 m"
# exit 1 if no reply within timeout
```

**Check modem id and voltage:**

```bash
nanomodem -n 001 -s /dev/ttyUSB0 status
```

**Listen on the active modem for 60s, print events, then exit:**

```bash
nanomodem -n 001 -s /dev/ttyUSB0 listen 60s
```

**Listen with event logging, then exit:**

```bash
nanomodem -n 001 -s /dev/ttyUSB0 --log-events listen 60s
```

**Send a literal wire string (escape hatch):**

```bash
nanomodem -n 001 -s /dev/ttyUSB0 cmd '$P002'
```

**With wire logging (TTY = colored `[wire]` lines):**

```bash
nanomodem -n 001 -s /dev/ttyUSB0 --log-wire ping 002
```

On startup, all transports run the same id check (`$?` query). Serial catches wrong `--node-id`; in-memory always passes.

---

## One-shot (in-memory)

Same verbs, same semantics. **No peer means timeout**, not a special error.

```bash
nanomodem -n 001 -m status
nanomodem -n 001 -m ping 002          # times out if 002 not on the bus
```

Multi-node in-memory ping needs both nodes on the same bus — use the **REPL** (one `InMemoryBus` per session).

---

## REPL — getting in

**Empty session** (add nodes interactively):

```bash
nanomodem
```

```
nanomodem> help
nanomodem>
```

Same with explicit in-memory:

```bash
nanomodem -m
```

**Bootstrap first node from flags** — land directly on node prompt:

```bash
nanomodem -n 001 -s /dev/ttyUSB0
```

```
001> status
001> ping 002
```

---

## REPL — session model

**Two prompt levels:**

- `nanomodem>` — session (multiple nodes)
- `001>` — active node

**Switch node:** `use 001` (works from either level)

**Leave a level:** `exit` (or Ctrl-D) — `001>` → `nanomodem>` → leave CLI. Optional `quit` alias.

**Run on a node without switching:** from `nanomodem>`:

```
nanomodem> 001 ping 002
```

**Add a node** — guided wizard when flags are missing:

```
nanomodem> node
node id: 002
transport [in-memory]: 
log events [off]: on
log wire [off]: 
002> 
```

Serial wizard (abbreviated):

```
nanomodem> node
node id: 001
transport [in-memory]: serial
serial path: /dev/ttyUSB0
baud [9600]: 
log events [off]: 
log wire [off]: on
001>
```

Or skip the wizard:

```
nanomodem> node -n 002 -s /dev/ttyUSB1
```

Ctrl-C cancels the wizard. Duplicate serial path → error. Multiple serial nodes allowed (different paths).

In-memory: **one shared bus per REPL session** — all `-m` nodes hear each other.

---

## REPL — commands (v1)

At `001>` (or via `001 …` from session level):

| Command | Purpose |
|---|---|
| `status` | Query modem id / voltage |
| `ping TARGET` | Range to target id |
| `listen DURATION` | Tail events for active node (e.g. `listen 60s`) |
| `cmd 'WIRE'` | Send literal wire string, e.g. `cmd '$Q'` |
| `log events on\|off` | Toggle `[evt]` output |
| `log wire on\|off` | Toggle `[wire]` output (serial) |
| `help` / `help ping` | Built-in help |
| `use ID` / `exit` | Navigation |

Tab completion in v1: commands, node ids, ping targets (context-aware per prompt).

REPL UX (history, completion, prompts) uses **`prompt_toolkit`** internally — not something you configure.

**Example `help` output:**

```
001> help
Commands at node prompt:
  status              Query modem id and voltage
  ping TARGET         Range to target node id
  listen DURATION     Tail events (e.g. listen 60s)
  cmd 'WIRE'          Send literal wire string
  log events on|off   Toggle parsed event log
  log wire on|off     Toggle raw wire log (serial)
  use ID              Switch active node
  exit                Pop one prompt level (Ctrl-D)
  help [CMD]          This help

001> help ping
ping TARGET
  Send $P to TARGET and print range in meters.
  Uses --sound-speed from session (default 1500 m/s).
```

---

## Logging & async RX

**Default:** quiet — only command output on stdout.

**Configure at REPL startup** (same flags as one-shot):

```bash
nanomodem -m --log-events
nanomodem -n 001 -s /dev/ttyUSB0 --log-wire
nanomodem -m --log-events --log-wire    # both independent
```

**Configure inside the REPL** (toggle without restarting):

```
nanomodem> log events on
nanomodem> log wire on
001> log events off
001> log wire off
```

The `node` wizard may also offer log toggles when adding a node.

**What they do:**

- `--log-events` / `log events on` → unsolicited parsed events from **all nodes** in the session, prefixed `[EVT 002] …`
- `--log-wire` / `log wire on` → raw TX/RX on serial, `[wire]` prefix, `format_serial_log` style; colors when stdout is a TTY, plain when piped or when `NO_COLOR` is set

**`listen`:** scopes to **active node only** (still respects `--log-events` formatting).

**Streams:** stdout = results + logs; stderr = errors.

---

## Example session (in-memory, two nodes)

```bash
nanomodem -m
```

```
nanomodem> node -n 002
nanomodem> node -n 001
nanomodem> use 001
001> ping 002
range 002: 847 m
001> exit
nanomodem> exit
```

With event logging:

```bash
nanomodem -m --log-events
```

```
nanomodem> node -n 001
nanomodem> node -n 002
nanomodem> use 001
001> ping 002
[EVT 001] … parsed event …
[EVT 002] … parsed event …
range 002: 847 m
001>
```

---

## Example session (serial, one modem)

```bash
nanomodem -n 001 -s /dev/ttyUSB0 --baud 9600
```

```
001> status
001> ping 002
001> listen 30s
001> cmd '$V042'
001> exit
```

---

## Multi-terminal / God View

Not this CLI. Use **`nanomodem-demo`**:

```bash
# terminal 1
nanomodem-simulator

# terminal 2
nanomodem-controller 001 --network 127.0.0.1:5555
```

TCP simulator transport lives in demo (`SimulatorJsonTransport`) — a consumer `WireTransport` impl, not part of `nanomodem-cli`.

---

## Quick reference

```bash
# REPL
nanomodem
nanomodem -m
nanomodem -n 001 -s /dev/ttyUSB0

# One-shots
nanomodem -n 001 -s /dev/ttyUSB0 status
nanomodem -n 001 -s /dev/ttyUSB0 ping 002
nanomodem -n 001 -s /dev/ttyUSB0 listen 60s
nanomodem -n 001 -s /dev/ttyUSB0 cmd '$P002'
nanomodem -n 001 -m status
```
