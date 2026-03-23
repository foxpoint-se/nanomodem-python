# AcousticNode API Interface Design

This document defines the clean, library-grade API for the `AcousticNode` class. It follows a unidirectional data flow: **Methods** are inputs from the consumer (sensors/UI), and **Callbacks** are outputs from the node (learned facts/calculations).

## 1. Helper Types

To avoid positional parameter "hell" and allow for React-style property updates, we use a `NodeUpdate` dataclass.

```python
@dataclass(frozen=True, kw_only=True)
class NodeUpdate:
    """Props for updating a known node in the registry. 
    Only provided fields will be modified.
    """
    position: Optional[Coord] = None
    depth: Optional[float] = None
    range: Optional[float] = None
```

## 2. AcousticNode Class

### Parameters (Constructor)
*   **`node_id: str`**: Unique 3-digit ID ("001"-"255"). Identity of this unit.
*   **`transport: TransportInterface`**: Injected communication layer. Decouples logic from Serial/Mock/ROS.
*   **`calculation: CalculationInterface`**: Injected math engine for trilateration.
*   **`sound_speed: float`**: Environment constant (m/s) used to convert time-of-flight to distance.

### Callbacks (Events Learned from the World)
*   **`on_range_measured(node_id: str, range_m: float)`**: 
    *   Fired when a physical acoustic response is received and converted to meters.
*   **`on_node_updated(node: KnownNode)`**: 
    *   Fired when a peer is discovered or changed (via modem broadcast or manual set). Allows incremental UI/Map updates.
*   **`on_node_deleted(node_id: str)`**: 
    *   Fired when a peer is removed from the registry (manual or timeout).
*   **`on_position_inferred(coord: Coord)`**: 
    *   Fired when the node successfully calculates its own location from peer data (distinct from a manual GPS update).
*   **`on_message_received(msg: Message)`**: 
    *   Low-level escape hatch for debugging or handling raw protocol strings.

### Methods (Actions Triggered by Consumer)
*   **`set_position(pos: Coord)`**: Input from a local GPS sensor.
*   **`set_depth(depth: float)`**: Input from a local pressure sensor.
*   **`request_range(node_id: str)`**: Triggers a physical acoustic event to measure distance.
*   **`broadcast_position()`**: Shares local sensor data (pos/depth) with the network.
*   **`calculate_position()`**: Manually triggers trilateration from current registry data.
*   **`update_known_node(node_id: str, props: NodeUpdate)`**: Manual override for registry (e.g., setting a fixed beacon position).
*   **`delete_known_node(node_id: str)`**: Explicitly removes a node from the registry.

---

## Design Principles
1.  **Separation of Concerns**: The Node manages localization logic; the Transport manages bits; the Consumer manages the runtime (GUI/ROS).
2.  **No Leaky Abstractions**: The API uses domain terms (Coord, Range) and never mentions hardware details like Serial Ports or Tkinter.
3.  **Typed & Explicit**: Uses `kw_only` dataclasses to ensure updates are readable and type-safe.
