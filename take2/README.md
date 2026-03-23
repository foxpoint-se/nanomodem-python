# Acoustic Modem Localization System

Layered system for underwater localization using acoustic modems (Nanomodem v3).

## Project structure

```
take2/
├── nanomodem/          # Core library (pure logic, no GUI)
│   ├── node.py         # AcousticNode — the only stateful class
│   ├── transport.py    # TransportInterface, MockTransport, MockEther
│   ├── nanomodem_transport.py  # Real serial transport
│   ├── codec.py        # Encode/decode message bodies
│   ├── calculation.py  # Trilateration, projection, timestamp conversion
│   ├── types.py        # Coord, KnownNode, Message union, etc.
│   ├── __main__.py     # CLI entry point (mock demo)
│   └── tests/          # 71 unit + integration tests
├── gui/                # Tkinter GUI application
│   ├── controller.py   # Per-node ControllerWindow
│   ├── launcher.py     # Boots nodes + windows
│   └── __main__.py     # python -m gui
├── pyproject.toml
├── TODO.md
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

## Install

```bash
cd take2
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

### Mock demo (no hardware needed)

From the **parent** of `take2` (repo root):

```bash
python -m nanomodem
```

From **inside** the `take2` folder:

```bash
PYTHONPATH=. python -m nanomodem
```

### GUI (mock mode)

```bash
cd take2
PYTHONPATH=. python -m gui
```

### Real hardware

```bash
python -m nanomodem --port /dev/ttyUSB0 --baud 9600 --node-id 001
```

(NanomodemTransport is implemented but not yet wired into the entry point's main loop.)

## Tests

```bash
PYTHONPATH= python -m pytest nanomodem/tests/ -v
```

71 tests covering all layers: node, codec, transport, calculation, and integration.

If you have ROS sourced, pytest may load ROS pytest plugins. The `PYTHONPATH=` prefix clears this so only the venv is used.

## Node capabilities

Nodes have two boolean capabilities that gate automatic behavior:

- `is_broadcasting_own_position` -- auto-broadcast when `set_position()` is called
- `is_inferring_own_position` -- auto-trilaterate when a new range response arrives and 3+ beacon positions/ranges are available

A "beacon" node sets `is_broadcasting_own_position = True`. A "submerged host" sets `is_inferring_own_position = True`. Both can be toggled independently on any node.

## Callbacks

AcousticNode accepts two optional callbacks:

- `on_state_changed: Callable[[], None]` -- called whenever node state changes (position set, depth changed, message received)
- `on_message_received: Callable[[Message], None]` -- called with each incoming message for logging/display

GUI controllers use these with `root.after(0, ...)` for thread-safe reactive UI updates.
