# Nanomodem Library

Python library for underwater localization using acoustic modems (Nanomodem v3).

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
│       │   └── serial.py       # SerialTransport (real hardware)
│       ├── drivers/
│       │   └── v3.py           # NanomodemV3Driver (modem command protocol)
│       ├── codecs/
│       │   └── v3.py           # Codec (message body encoding)
│       ├── __main__.py         # CLI entry point (mock demo)
│       └── tests/              # Unit + integration tests
├── apps/
│   └── gui_controller/         # Tkinter GUI application
│       ├── controller.py       # Per-node ControllerWindow
│       ├── scenarios/          # Launch configurations
│       │   ├── mock_4_nodes.py # 4-node simulation
│       │   └── single_node.py  # Single node UI
│       └── __main__.py         # Help/Scenario directory
├── pyproject.toml
└── README.md
```

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

**TransportProtocol** defines `broadcast_position(coord, depth)`, `request_range(target_id)`, and `on_message(callback)`. Two implementations:

- **MockTransport** routes typed `Message` objects through a shared **MockEther** bus. No codec or driver needed.
- **SerialTransport** wraps a serial port. Delegates command formatting and response parsing to a **DriverProtocol** implementation.

**NanomodemV3Driver** handles the nanomodem v3 modem protocol: formats `$P`, `$B` commands and parses `#R`, `#B`, `#U` responses. Uses a **Codec** for message body encoding/decoding.

**Calculation** is stateless and pure. Trilateration (scipy least_squares), 3D-to-2D projection, timestamp-to-distance conversion.

## Installation

From the repository root:

```bash
make install
```

This creates `.venv/` and installs dependencies. To activate:

```bash
source .venv/bin/activate
```

## Usage

### Mock Demo (No hardware needed)

**GUI with 4 mock nodes (1 host + 3 beacons):**

```bash
nanomodem-demo
```

**Single node GUI (requires node ID):**

```bash
nanomodem-node 001
```

**CLI demo:**

```bash
python3 -m nanomodem
```

### Real Hardware (Single Modem on Serial)

Connect a nanomodem v3 to your serial port and run:

```python
from nanomodem import AcousticNode, SerialTransport, NanomodemV3Driver, Codec, Coord

# Wire up: codec -> driver -> transport -> node
driver = NanomodemV3Driver(codec=Codec())
transport = SerialTransport(node_id="001", port="/dev/ttyUSB0", driver=driver)
node = AcousticNode(node_id="001", transport=transport)

transport.start()

node.set_position(Coord(lat=63.0, lon=10.0))
node.broadcast_position()    # Announce to other nodes
node.request_range("002")    # Ping another node
# ... incoming messages are delivered via on_message callback ...

transport.stop()
```

### Two Mock Nodes (No Hardware)

Simulate two nodes communicating through an in-memory bus:

```python
from nanomodem import AcousticNode, MockEther, MockTransport, Coord

ether = MockEther()

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

For complete scenarios with GUI, trilateration, and multi-node setups, see `apps/gui_controller/scenarios/`.

### CLI

```bash
python3 -m nanomodem                  # Mock demo (no hardware)
python3 -m nanomodem --port /dev/ttyUSB0 --node-id 001  # Real hardware
```

## Development

### Setup

```bash
make install
```

### Quality Control

A `Makefile` is provided to simplify common development tasks. Run `make help` to see all available commands:

```bash
make test      # Run all tests
make lint      # Check for style and logical errors (Ruff)
make format    # Automatically format code (Ruff)
make typecheck # Run strict type checking (Mypy)
```

### IDE Integration

To ensure your IDE matches the project's quality standards:
1. **Ruff Extension**: Install the [Ruff extension](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff) for Cursor/VS Code.
2. **Format on Save**: Enable "Format on Save" in your editor settings and set Ruff as the default formatter. This will ensure your code is always formatted according to the project's rules (Black-compatible).
3. **Mypy**: The `pyproject.toml` is configured for strict type checking. Most IDEs will pick this up automatically if you have a Python type-checking extension installed.

---

## API Reference

### Node Capabilities

Nodes have two boolean capabilities that gate automatic behavior:

- `is_broadcasting_own_position` -- auto-broadcast when `set_position()` is called
- `is_inferring_own_position` -- auto-trilaterate when a new range response arrives and 3+ beacon positions/ranges are available

A "beacon" node sets `is_broadcasting_own_position = True`. A "submerged host" sets `is_inferring_own_position = True`. Both can be toggled independently on any node.

### Callbacks

AcousticNode accepts two optional callbacks:

- `on_state_changed: Callable[[], None]` -- called whenever node state changes (position set, depth changed, message received)
- `on_message_received: Callable[[Message], None]` -- called with each incoming message for logging/display

GUI controllers use these with `root.after(0, ...)` for thread-safe reactive UI updates.
