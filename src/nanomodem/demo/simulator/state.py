"""State management for the God View Simulator.

Maintains the "Physical Truth" of the simulation, including:
- Physical positions of all nodes
- Belief positions (what each node thinks its position is)
- Virtual GPS state for side-channel updates
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from nanomodem.types import Coord


@dataclass
class NodePhysicalState:
    """Physical state of a node in the simulation (God View truth)."""

    node_id: str
    position: Optional[Coord] = None
    depth: float = 0.0


@dataclass
class NodeBeliefState:
    """What the node believes about its own state (from controller)."""

    node_id: str
    position: Optional[Coord] = None
    depth: float = 0.0
    known_nodes: dict[str, Coord] = field(default_factory=dict)


@dataclass
class SimulatorState:
    """Complete state of the God View Simulator.

    Maintains both physical truth and belief states for all nodes.
    """

    # Physical truth (managed by simulator UI)
    physical: dict[str, NodePhysicalState] = field(default_factory=dict)

    # Belief (reported by controllers)
    belief: dict[str, NodeBeliefState] = field(default_factory=dict)

    # Acoustic propagation parameters
    sound_speed: float = 1500.0  # m/s in water

    def register_node(self, node_id: str) -> None:
        """Register a new node in the simulation."""
        if node_id not in self.physical:
            self.physical[node_id] = NodePhysicalState(node_id=node_id)
        if node_id not in self.belief:
            self.belief[node_id] = NodeBeliefState(node_id=node_id)

    def set_physical_position(self, node_id: str, position: Coord, depth: float = 0.0) -> None:
        """Set the physical (truth) position of a node."""
        if node_id not in self.physical:
            self.register_node(node_id)
        self.physical[node_id].position = position
        self.physical[node_id].depth = depth

    def get_physical_position(self, node_id: str) -> Optional[tuple[Coord, float]]:
        """Get the physical (truth) position of a node."""
        if node_id not in self.physical:
            return None
        state = self.physical[node_id]
        if state.position is None:
            return None
        return (state.position, state.depth)

    def set_belief_position(self, node_id: str, position: Coord, depth: float = 0.0) -> None:
        """Set what the node believes its position is."""
        if node_id not in self.belief:
            self.register_node(node_id)
        self.belief[node_id].position = position
        self.belief[node_id].depth = depth

    def get_belief_position(self, node_id: str) -> Optional[tuple[Coord, float]]:
        """Get what the node believes its position is."""
        if node_id not in self.belief:
            return None
        state = self.belief[node_id]
        if state.position is None:
            return None
        return (state.position, state.depth)

    def get_all_node_ids(self) -> list[str]:
        """Get all registered node IDs."""
        return sorted(set(self.physical.keys()) | set(self.belief.keys()))
