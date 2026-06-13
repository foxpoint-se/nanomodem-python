# Nanomodem Library

Python library for underwater acoustic positioning — trilaterate a submerged node's position using a network of surface beacons and acoustic range measurements.

## Installation

### For Users (Library)

Install the core library (includes `scipy` and `pyserial`):

```bash
pip install git+https://github.com/foxpoint-se/nanomodem-python.git
```

To include the demo scenarios and their dependencies:

```bash
pip install "nanomodem[demo] @ git+https://github.com/foxpoint-se/nanomodem-python.git"
```

### For Developers (Local)

Clone and set up the full environment (requires `uv`):

```bash
git clone https://github.com/foxpoint-se/nanomodem-python.git
cd nanomodem-python
make install
```

Run `make help` to see all available commands:

```bash
make test           # Run all tests
make lint           # Check for style and logical errors (Ruff)
make format         # Automatically format code (Ruff)
make typecheck      # Run strict type checking (Mypy)
make verify-dist    # Verify the core library is installable in a clean environment
make verify-dist-demo  # Verify the demo extra is installable in a clean environment
```

## Usage

### Demo Scenarios (requires `[demo]` extra)

**4-node mock simulation (1 host + 3 beacons):**

```bash
uv run nanomodem-demo

# OR
source .venv/bin/activate
nanomodem-demo
```

**Single node UI (mock or serial):**

```bash
# Mock mode (no hardware)
uv run nanomodem-controller 001

# Real hardware
uv run nanomodem-controller 001 --port /dev/ttyUSB0
```

On startup the controller sends `$?` and **exits** if the modem's stored id does not match the id you passed.

**Speed of sound (ranging):** Defaults to **1500 m/s** (water). For air bench tests with ping/range, use **340 m/s**:

```bash
# Air bench (USB modems, map range circles)
uv run nanomodem-controller 001 --port /dev/ttyUSB0 --sound-speed 340
```

With the God View simulator, use the **same** `--sound-speed` on the simulator and every controller so simulated `#R` timestamps match decode.

**God View Simulator (multi-process testing):**

The simulator provides a "God View" of physical truth separate from controller belief, enabling realistic multi-terminal testing without hardware.

**Network mode (fast, multi-terminal logic testing):**

```bash
# Start simulator in one terminal
uv run nanomodem-simulator

# Connect controllers in other terminals
uv run nanomodem-controller 001 --network 127.0.0.1:5555
uv run nanomodem-controller 002 --network 127.0.0.1:5555

# Air bench (matching c on simulator + controllers)
uv run nanomodem-simulator --sound-speed 340
uv run nanomodem-controller 001 --network 127.0.0.1:5555 --sound-speed 340
```

**Serial mode (hardware-accurate stack testing with PTYs):**

```bash
# Start simulator in one terminal
uv run nanomodem-simulator

# Create PTY pair for Node 001 in another terminal
socat -d -d pty,raw,echo=0 pty,raw,echo=0
# Note the PTY paths (e.g., /dev/pts/4 and /dev/pts/5)

# Connect controller 001 in a third terminal
uv run nanomodem-controller 001 --port /dev/pts/4 --world 127.0.0.1:5555 --world-port /dev/pts/5

# Repeat for additional nodes
```

Serial mode tests the full `SerialTransport`, `Driver`, and `Codec` stack — the same code that runs on the boat. Acoustic data flows through the PTY, while metadata (registration, GPS updates) flows through a TCP connection to the simulator.

**All-in-one serial test** (socat + simulator + two controllers in one process):

```bash
uv run python -m nanomodem.demo.scenarios.serial_bridge_with_god_view
```

### Real Hardware (Single Modem on Serial)

```python
from nanomodem import AcousticNode, SerialTransport, NanomodemV3Driver, Codec, Coord

# Wire up: codec -> driver -> transport -> node
driver = NanomodemV3Driver(codec=Codec())
transport = SerialTransport(node_id="001", port="/dev/ttyUSB0", driver=driver)
node = AcousticNode(node_id="001", transport=transport)  # sound_speed defaults to 1500 m/s (water)

transport.start()

node.set_position(Coord(lat=63.0, lon=10.0))
node.broadcast_position()    # Announce to other nodes
node.request_range("002")    # Ping another node
node.request_test("002")     # Request test transmission from unit 002
node.query_quality()         # Bytes corrected on last received data packet
node.query_modem_status()    # Modem NVM address and supply voltage ($?)
# ... incoming messages are delivered via on_message callback ...

transport.stop()
```

### Two Mock Nodes (No Hardware)

```python
from nanomodem import AcousticNode, MockEther, MockTransport, Coord, SOUND_SPEED_WATER_M_S

ether = MockEther(sound_speed=SOUND_SPEED_WATER_M_S)

node_a = AcousticNode(
    node_id="001",
    transport=MockTransport("001", ether),
    position=Coord(lat=63.0, lon=10.0),
)
node_b = AcousticNode(
    node_id="002",
    transport=MockTransport("002", ether),
)

# Node A broadcasts its position, Node B receives it
node_a.broadcast_position()
print(node_b.get_known_nodes())  # Node B now knows about Node A
```

### CLI

```bash
python3 -m nanomodem                                    # Mock demo (no hardware)
python3 -m nanomodem --port /dev/ttyUSB0 --node-id 001  # Real hardware
```

For complete scenarios with GUI, trilateration, and multi-node setups, see `src/nanomodem/demo/scenarios/`.

## Architecture

```mermaid
graph TD
    Client["Client (ROS, CLI, GUI, test)"]
    Node["AcousticNode"]
    TP["TransportProtocol"]
    Calc["Calculation"]
    MockT["MockTransport"]
    MockE["MockEther"]
    SerialT["SerialTransport"]
    Driver["NanomodemV3Driver"]
    CodecV3["Codec"]
    Serial["serial.Serial"]

    Client --> Node
    Node --> TP
    Node --> Calc
    TP -.->|"impl"| MockT
    TP -.->|"impl"| SerialT
    MockT --> MockE
    SerialT --> Driver
    SerialT --> Serial
    Driver --> CodecV3
```

**Pluggable design**: all core interfaces live in `protocols.py`. Swap implementations without changing core logic.

**AcousticNode** is the only stateful class. It holds its own position, depth, known nodes, and distances. Orchestrates communication and calculation via injected dependencies (transport, calculation).

**TransportProtocol** defines `broadcast_position(coord, depth)`, `request_range(target_id)`, `request_test(target_id)`, `query_quality()`, `query_modem_status()`, and `on_message(callback)`. Two implementations:

- **MockTransport** routes typed `Message` objects through a shared **MockEther** bus (including mock `$T` / `$Q` behavior). No codec or driver needed.
- **SerialTransport** wraps a serial port. Delegates command formatting and response parsing to a **DriverProtocol** implementation.

**NanomodemV3Driver** handles the nanomodem v3 modem protocol: formats `$P`, `$B`, `$T`, `$Q`, `$?` and parses `#R`, `#B`, `#U`, `#A…V…` (modem status), `$C` / `$C-`, and local acks. Uses a **Codec** for position body encoding/decoding. Fixed test payloads are recognized with `is_test_broadcast_line()` on received `#B` lines. Supply voltage from `$?` uses `supply_voltage_volts(voltage_raw)`.

**Calculation** is stateless and pure. Trilateration (scipy least_squares), 3D-to-2D projection, timestamp-to-distance conversion.

## Project Structure

```text
.
├── src/
│   └── nanomodem/              # Core library
│       ├── node.py             # AcousticNode — the only stateful class
│       ├── protocols.py        # TransportProtocol, DriverProtocol, etc.
│       ├── types.py            # Coord, KnownNode, Message union, etc.
│       ├── calculation.py      # Trilateration, projection, timestamp conversion
│       ├── transports/
│       │   ├── mock.py         # MockTransport + MockEther (in-memory)
│       │   ├── serial.py       # SerialTransport (real hardware)
│       │   └── network.py      # NetworkMockTransport (simulator TCP)
│       ├── drivers/
│       │   └── v3.py           # NanomodemV3Driver (modem command protocol)
│       ├── codecs/
│       │   └── v3.py           # Codec (message body encoding)
│       ├── demo/               # Demo tools (installed with [demo] extra)
│       │   ├── controller.py   # Per-node ControllerWindow
│       │   ├── simulator/      # God View simulator (`nanomodem-simulator`)
│       │   └── scenarios/      # mock_4_nodes, single_node, serial_bridge_with_god_view, …
│       ├── __main__.py         # CLI entry point (mock demo)
│       └── tests/              # Unit + integration tests
├── plans/TODO.md               # Forward-looking backlog
├── pyproject.toml
└── README.md
```

## API Reference

### Node Capabilities

Nodes have two boolean capabilities that gate automatic behavior:

- `is_broadcasting_own_position` -- auto-broadcast when `set_position()` is called
- `is_inferring_own_position` -- auto-trilaterate when a new range response arrives and 3+ beacon positions/ranges are available

A "beacon" node sets `is_broadcasting_own_position = True`. A "submerged host" sets `is_inferring_own_position = True`. Both can be toggled independently on any node.

### Callbacks

AcousticNode accepts optional typed callbacks:

- `on_position_changed: Callable[[Optional[Coord]], None]` -- called when own position is set or cleared
- `on_depth_changed: Callable[[float], None]` -- called when own depth changes
- `on_known_nodes_changed: Callable[[dict[str, KnownNode]], None]` -- called when the peer registry changes (new node seen, range updated, etc.)
- `on_message_received: Callable[[Message], None]` -- called with each incoming message for logging/display

GUI controllers use these with `root.after(0, ...)` for thread-safe reactive UI updates.

## IDE Integration

1. **Ruff Extension**: Install the [Ruff extension](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff) for Cursor/VS Code.
2. **Format on Save**: Enable "Format on Save" in your editor settings and set Ruff as the default formatter.
3. **Mypy**: The `pyproject.toml` is configured for strict type checking. Most IDEs will pick this up automatically if you have a Python type-checking extension installed.
