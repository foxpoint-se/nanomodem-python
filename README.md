# Nanomodem Library

Python library for underwater localization using acoustic modems (Nanomodem v3).

## Project Structure

```text
.
├── src/
│   └── nanomodem/              # Core library (nanomodem)
│       ├── node.py             # AcousticNode — the only stateful class
│       ├── transport.py        # TransportInterface, MockTransport, MockEther
│       ├── nanomodem_transport.py  # Real serial transport
│       ├── codec.py            # Encode/decode message bodies
│       ├── calculation.py       # Trilateration, projection, timestamp conversion
│       ├── types.py            # Coord, KnownNode, Message union, etc.
│       ├── __main__.py         # CLI entry point (mock demo)
│       └── tests/              # 71 unit + integration tests
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
    Caps["NodeCapabilities"]
    Registry["KnownNodes registry"]
    Transport["TransportInterface"]
    Calc["Calculation"]
    NanoTransport["NanomodemTransport"]
    Codec["Codec (encode/decode bodies)"]
    MockTransport["MockTransport"]
    MockEther["MockEther (shared bus)"]
    Serial["Serial Port"]

    Client --> Node
    Node --> Caps
    Node --> Registry
    Node --> Transport
    Node --> Calc
    Transport -.-> NanoTransport
    Transport -.-> MockTransport
    NanoTransport --> Codec
    NanoTransport --> Serial
    MockTransport --> MockEther
```

**AcousticNode** is the only stateful class. It holds its own position, depth, known nodes, and distances. Orchestrates communication and calculation via injected dependencies.

**Calculation** is stateless and pure. Trilateration (scipy least_squares), 3D-to-2D projection, timestamp-to-distance conversion.

**TransportInterface** defines two operations: `broadcast_position(coord)` and `request_range(target_id)`, plus `on_message(callback)` for receiving. Two implementations:

- **MockTransport** routes typed `Message` objects through a shared **MockEther** bus. No codec needed.
- **NanomodemTransport** wraps a serial port. Uses **Codec** internally to encode/decode message bodies. Formats `$P`, `$B`, `$M` commands. Parses `#` responses. Nothing received on serial is ever silently dropped -- everything becomes a typed `Message` (or `UnknownMessage` as catch-all).

**Codec** encodes/decodes message bodies (position data). Stateless, pure, injected into NanomodemTransport. The node never knows it exists.

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
python3 -m apps.gui_controller.scenarios.mock_4_nodes
```

**Single node GUI (requires node ID):**

```bash
python3 -m apps.gui_controller.scenarios.single_node 001
```

**CLI demo:**

```bash
python3 -m nanomodem
```

### Real Hardware

```bash
python3 -m nanomodem --port /dev/ttyUSB0 --baud 9600 --node-id 001
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
