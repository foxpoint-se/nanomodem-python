# CLI open decisions

**Execution order:** [master-plan.md](./master-plan.md) step 10 — **blocked on step 9b** (demo transport rename; [open-decisions.md](./open-decisions.md) #7). Discuss one by one; say **next** to advance. When all are locked, update [cli-use-cases.md](./cli-use-cases.md).

**Draft UX:** [cli-use-cases.md](./cli-use-cases.md) · **Examples (older):** [cli-examples.md](./cli-examples.md)

---

## Package & binary

| # | Topic | Options | Decision |
|---|-------|---------|----------|
| 1 | Package name | `nanomodem-cli` · `nanomodem_cli` | **`nanomodem-cli`** |
| 2 | Binary name on `$PATH` | `nanomodem` · `nm` · other | **`nanomodem`** — field install via `pipx install …` → `nanomodem` on PATH; repo dev via `make install` + `uv run nanomodem` |
| 3 | Depends on | `nanomodem` only · `nanomodem` + `nanomodem-demo` (network backend) | **`nanomodem` only** — serial + in-memory; no demo package (#33) |

---

## Connection flags (one-shot & repl bootstrap)

| # | Topic | Options | Decision |
|---|-------|---------|----------|
| 4 | Node id flag | `--node-id` + `-n` · `--node` + `-n` · positional (reject?) | **`--node-id` + `-n`** — one vocabulary with REPL `node add` / library `node_id`; “modem” in user-facing errors only |
| 5 | Transport selection | Mutually exclusive flags: `--serial PATH` / `-s`, `--in-memory`, `--network HOST:PORT` · single `--transport KIND:VALUE` | **Three mutually exclusive flags** — map 1:1 to library transport types |
| 6 | Transport shorthands | `-s` serial · `-m` in-memory · short flag for network/tcp | **`-s PATH`**, **`-m`**, **`--network HOST:PORT` long-only** (no short flag — `-n` is node id) |
| 7 | Default transport in `repl` with no flags | Error (must pick) · default `--in-memory` | **Default `--in-memory`** |
| 8 | Baud / sound-speed flags | `--baud` (serial) · `--sound-speed` (ping/range) — global or per `node add`? | **Optional on one-shot + `node add` / repl bootstrap** — default **9600** baud, **1500** m/s (`SOUND_SPEED_WATER_M_S`); omit = library defaults |

---

## Entry shape: one-shot vs REPL

| # | Topic | Options | Decision |
|---|-------|---------|----------|
| 9 | REPL entry | `nanomodem repl …` only · bare `nanomodem` = repl (like `redis-cli`) | **Bare `nanomodem` = REPL** — no `repl` subcommand |
| 10 | One-shot entry | Subcommand required: `nanomodem … ping 002` · no implicit one-shot | **Verb present → one-shot** (`status`, `ping`, `listen`, `cmd`); run and exit |
| 11 | `repl` bootstrap | Optional `-n` + transport flags create first node → land on `001>` · no flags → empty `nanomodem>` | **Both** — flags bootstrap first node → `001>`; bare entry → `nanomodem>` + `node add` |

---

## REPL session model

| # | Topic | Options | Decision |
|---|-------|---------|----------|
| 12 | Prompts | `nanomodem>` (session) + `001>` (active node) | **`nanomodem>`** + **`001>`**; session also accepts **`001 ping 002`** (node prefix, no `use` required) |
| 13 | Switch node | `use 001` · `switch 001` | **`use 001`** — works from `nanomodem>` and `001>` |
| 14 | Leave active node | `back` · `exit` · `.` · `use` with no arg | **`exit`** — pop one level (`001>` → `nanomodem>` → leave CLI); **`quit`** alias optional; **Ctrl-D** same as `exit` at each level |
| 15 | Add node | `node add …` · guided wizard · inner shell | **`node`** — wizard prompts when flags missing; **`node -n 001 -s …`** skips wizard; Ctrl-C cancels |
| 16 | In-memory bus lifetime | One `InMemoryBus` per REPL session · new bus per `node add` (reject?) | **One bus per session** |
| 17 | Serial nodes in REPL | One serial node per session · multiple if multiple `-s` paths | **Multiple allowed** — duplicate path → error |

---

## Commands

| # | Topic | Options | Decision |
|---|-------|---------|----------|
| 18 | Structured commands (v1) | `status`, `ping`, `listen`, `cmd` · add `quality`, `test`, … | **`status`, `ping`, `listen`, `cmd`** |
| 19 | Escape hatch name | `wire` · `send` · `cmd` · `raw` | **`cmd`** — literal user-guide wire string, e.g. `cmd '$P002'` |
| 20 | `listen` duration syntax | Positional `listen 60s` · optional `--duration 60s` alias | **`listen 60s`** only (REPL and one-shot) |
| 21 | CLI stack | `PositioningNode` · `ModemNode` + codec | **`ModemNode` + `RawPayloadCodec`** — wire/modem CLI; `ping` converts `#R` → meters in CLI code |
| 22 | `cmd` on network backend | Allowed (if simulator accepts) · serial/in-memory only | **Allowed on all transports** |
| 23 | Startup id check | Always on serial · all transports · never | **All transports** — same `$?` check after node create; serial catches mismatch, sim always passes |

---

## Output & async RX

| # | Topic | Options | Decision |
|---|-------|---------|----------|
| 24 | Log output | Print `→`/`←` on serial only · always · never | **`--log-events`**, **`--log-wire`** (independent; wire serial/network only); default quiet; set in **`node` wizard** + one-shot flags + REPL `log events/wire on/off`; `[wire]`/`[evt]` prefixes; **colors when TTY**, plain when piped/`NO_COLOR`; reuse `format_serial_log` style for wire |
| 25 | Unsolicited RX (REPL) | Prefix all nodes `[id] …` · active node only | **All nodes** when `--log-events` on — prefixed `[EVT id]` |
| 26 | `listen` scope | Active node only · all nodes in session | **Active node only** |
| 27 | Exit codes | `ping` timeout → 1 · `status` mismatch → 1 · default 0 | **One-shot only** — 0 ok, 1 on failure (timeout, id mismatch, bad args) |
| 28 | stdout vs stderr | Data/events stdout, errors stderr · all stdout | **stdout** = results + logs; **stderr** = errors |

---

## REPL implementation

| # | Topic | Options | Decision |
|---|-------|---------|----------|
| 29 | REPL library | `prompt_toolkit` · stdlib `cmd` · hand-rolled readline | **`prompt_toolkit`** — history, dynamic prompt, Ctrl-C/D, completion |
| 30 | Tab completion (v1 scope) | Ship in v1 · follow-up | **Ship in v1** + `help` / `help CMD` at both prompt levels |
| 31 | Completion targets | Commands · node ids · target ids for `ping` | **All three** — context-aware per prompt (`nanomodem>` vs `001>`) |

---

## In-memory & network constraints

| # | Topic | Options | Decision |
|---|-------|---------|----------|
| 32 | In-memory one-shot | Allow `status` only · disallow all one-shots · allow if peer auto-spawned | **All one-shots, all transports** — same semantics; missing peer = timeout |
| 33 | Network backend | v1 · defer · demo-only extra binary | **Out of scope** — God View / TCP simulator stays in `nanomodem-demo` (`nanomodem-controller`), not this CLI |
| 34 | Share `verify_modem_id_at_startup` | Copy into CLI · shared module in `nanomodem-demo` · small `nanomodem_cli/startup.py` | **Copy to `nanomodem_cli/startup.py`** — adapted for `ModemNode` |
| 35 | LBL / positioning scope | Same CLI · subcommands · separate CLI later | **Separate CLI later** (not v1 `nanomodem`) — LBL = `PositioningNode`, own package/binary TBD |

---

