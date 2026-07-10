# nanomodem-cli — usage examples

**Execution order:** [master-plan.md](./master-plan.md) step 10 only — defer until refactor is done.

Illustrative only (not implemented). `$` = your shell prompt. `→` / `←` = TX/RX on serial wire.

---

## One-liner (script)

**Check modem id and voltage before a field run.**

```bash
$ nanomodem --node-id 001 --port /dev/ttyUSB0 status
```

```
→ $?
← #A001V48123
id=001  voltage=11.01V
```

**Ping another unit; exit code 1 on timeout.**

```bash
$ nanomodem --node-id 001 --port /dev/ttyUSB0 ping 042
```

```
→ $P042
← $P042
← #R042T039520
range 042: 1234 m
```

```bash
$ nanomodem --node-id 001 --port /dev/ttyUSB0 ping 099
```

```
→ $P099
← $P099
← #TO
timeout
$ echo $?
1
```

---

## One-liner `listen` (script / pipe)

**Stream raw RX for 60s into a log file.**

```bash
$ nanomodem --node-id 001 --port /dev/ttyUSB0 listen 60s > rx.log
```

```
← #B00308…
← #R042T039520
← #U08…
```

**Capture traffic while sending from another terminal.**

```bash
# terminal 1
$ nanomodem --node-id 001 --port /dev/ttyUSB0 listen 30s &

# terminal 2
$ nanomodem --node-id 001 --port /dev/ttyUSB0 ping 042
```

---

## REPL (interactive poke)

**Persistent session with always-on RX — GUI controller without the map.**

```bash
$ nanomodem --node-id 001 --port /dev/ttyUSB0
```

```
connected 001 on /dev/ttyUSB0
001> status
→ $?
← #A001V48123
id=001  voltage=11.01V
001> ping 042
→ $P042
← $P042
← #R042T039520
range 042: 1234 m
001> 
← #B00308…          ← unsolicited; prints between prompts
001> quit
```

---

## Raw escape hatch (serial only)

**Send a wire command the structured subcommands don't wrap yet.**

```bash
$ nanomodem --node-id 001 --port /dev/ttyUSB0 raw '$V042'
```

```
→ $V042
← $V042
← #B04206V47800
```

---

## Mock backend (single process, no hardware)

**Same subcommands; no serial lines — typed messages inside one Python process.**

```bash
$ nanomodem --mock --node-id 001 status
```

```
id=001  voltage=11.01V
```

```bash
$ nanomodem --mock --node-id 001 --lat 63.0 --lon 10.0 ping 002
```

```
timeout
```

*(No peer 002 registered on the shared in-memory bus — same as pinging a missing node.)*

**Two mock nodes talking requires one process** (not two CLI terminals):

```
# internal: MockEther + node 001 + node 002 with positions set
001> ping 002
range 002: 847 m
```

---

## Network backend (two terminals)

**Multi-process testing via the God View simulator — not mock.**

```bash
# terminal 1
$ nanomodem-simulator

# terminal 2
$ nanomodem --network 127.0.0.1:5555 --node-id 001 listen

# terminal 3
$ nanomodem --network 127.0.0.1:5555 --node-id 002 ping 001
```

```
← range 001: 312 m        ← appears in terminal 2's listen stream
range 001: 312 m            ← summary in terminal 3
```

*(Network mode delivers typed messages over TCP/JSON — no `$P` / `#R` wire lines.)*

---

## Transport comparison

| Backend  | Wire output (`→`/`←`) | Two terminals? |
|----------|----------------------|----------------|
| `--port` | yes                  | yes            |
| `--mock` | no                   | no (one process) |
| `--network` | no                | yes (simulator) |
