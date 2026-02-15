"""Per-node controller window with integrated map visualization.

Each ControllerWindow manages a single AcousticNode and shows
that node's worldview: own position, known nodes, range circles,
and a console for events.
"""

from __future__ import annotations

import math
import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Optional

from tkintermapview import TkinterMapView

from nanomodem.node import AcousticNode
from nanomodem.transport import TransportInterface
from nanomodem.types import (
    Coord,
    Message,
    PositionMessage,
    RangeResponseMessage,
    UnknownMessage,
)

NODE_COLORS = ["#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#e67e22", "#1abc9c"]
OWN_COLOR = "#e74c3c"


def _circle_coords(
    lat: float, lon: float, radius_m: float, n: int = 48
) -> list[tuple[float, float]]:
    """Generate lat/lon points forming a circle of given radius."""
    meters_per_deg = 111320.0
    cos_lat = math.cos(math.radians(lat))
    points: list[tuple[float, float]] = []
    for i in range(n + 1):
        angle = 2 * math.pi * i / n
        dlat = radius_m * math.cos(angle) / meters_per_deg
        dlon = radius_m * math.sin(angle) / (meters_per_deg * cos_lat)
        points.append((lat + dlat, lon + dlon))
    return points


class ControllerWindow:
    """Tkinter window controlling a single AcousticNode.

    Shows the node's worldview on an integrated map, with controls
    for position setting, ranging, broadcasting, and trilateration.
    """

    def __init__(
        self,
        root: tk.Tk,
        node_id: str,
        pretty_name: str,
        transport: TransportInterface,
        peer_ids: list[str],
        map_center: tuple[float, float] = (59.310153, 17.975189),
        map_zoom: int = 17,
        position: Optional[Coord] = None,
        window_geometry: Optional[str] = None,
    ) -> None:
        self._root = root
        self._peer_ids = peer_ids
        self._pending_click: Optional[tuple[float, float]] = None
        self._map_markers: list[object] = []
        self._map_paths: list[object] = []

        # --- Create the window ---
        self._window = tk.Toplevel(root)
        self._window.title(f"Controller — Node {node_id} ({pretty_name})")
        self._window.protocol("WM_DELETE_WINDOW", self._on_close)
        if window_geometry:
            self._window.geometry(window_geometry)

        # --- Build all UI panels ---
        self._build_map(map_center, map_zoom)
        self._build_position_panel()
        self._build_known_nodes_panel()
        self._build_actions_panel()
        self._build_console()

        # --- Create AcousticNode (after UI so callbacks can schedule updates) ---
        self._node = AcousticNode(
            node_id=node_id,
            transport=transport,
            position=position,
            on_state_changed=lambda: root.after(0, self._refresh_ui),
            on_message_received=lambda msg: root.after(0, self._log_message, msg),
        )

        # Sync MockTransport position (duck-typed: only MockTransport has .position)
        if position is not None and hasattr(transport, "position"):
            transport.position = position

        self._refresh_ui()

    @property
    def node(self) -> AcousticNode:
        return self._node

    # ------------------------------------------------------------------ #
    #  UI construction                                                     #
    # ------------------------------------------------------------------ #

    def _build_map(self, center: tuple[float, float], zoom: int) -> None:
        frame = ttk.LabelFrame(self._window, text="Map — what this node knows")
        frame.pack(fill=tk.X, padx=6, pady=(6, 3))

        self._map = TkinterMapView(frame, width=420, height=250, corner_radius=0)
        self._map.pack(fill=tk.X, padx=2, pady=2)
        self._map.set_position(center[0], center[1])
        self._map.set_zoom(zoom)
        self._map.add_left_click_map_command(self._on_map_click)

    def _build_position_panel(self) -> None:
        frame = ttk.LabelFrame(self._window, text="Own Position")
        frame.pack(fill=tk.X, padx=6, pady=3)

        # Readout row
        readout = ttk.Frame(frame)
        readout.pack(fill=tk.X, padx=4, pady=(4, 2))

        self._lat_var = tk.StringVar(value="—")
        self._lon_var = tk.StringVar(value="—")
        self._depth_display_var = tk.StringVar(value="—")

        for label, var in [
            ("Lat:", self._lat_var),
            ("Lon:", self._lon_var),
            ("Depth:", self._depth_display_var),
        ]:
            ttk.Label(readout, text=label, foreground="gray").pack(side=tk.LEFT, padx=(0, 2))
            ttk.Label(readout, textvariable=var).pack(side=tk.LEFT, padx=(0, 12))

        # Controls row
        controls = ttk.Frame(frame)
        controls.pack(fill=tk.X, padx=4, pady=(2, 4))

        ttk.Label(controls, text="Depth:").pack(side=tk.LEFT)
        self._depth_entry = ttk.Entry(controls, width=6)
        self._depth_entry.insert(0, "0.0")
        self._depth_entry.pack(side=tk.LEFT, padx=(4, 2))
        ttk.Label(controls, text="m").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(controls, text="Set depth", command=self._on_set_depth).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(
            controls, text="Set position from map", command=self._on_set_position_from_map
        ).pack(side=tk.RIGHT)

    def _build_known_nodes_panel(self) -> None:
        outer = ttk.LabelFrame(self._window, text="Known Nodes")
        outer.pack(fill=tk.X, padx=6, pady=3)

        self._known_nodes_frame = ttk.Frame(outer)
        self._known_nodes_frame.pack(fill=tk.X, padx=4, pady=4)

    def _build_actions_panel(self) -> None:
        frame = ttk.LabelFrame(self._window, text="Actions")
        frame.pack(fill=tk.X, padx=6, pady=3)

        # Range row
        range_row = ttk.Frame(frame)
        range_row.pack(fill=tk.X, padx=4, pady=(4, 2))

        ttk.Label(range_row, text="Range to:").pack(side=tk.LEFT)
        self._range_target = ttk.Combobox(
            range_row, values=self._peer_ids, width=6, state="readonly"
        )
        if self._peer_ids:
            self._range_target.current(0)
        self._range_target.pack(side=tk.LEFT, padx=4)
        ttk.Button(range_row, text="Request range", command=self._on_request_range).pack(
            side=tk.LEFT
        )

        # Button row
        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=tk.X, padx=4, pady=(2, 4))

        ttk.Button(btn_row, text="Broadcast position", command=self._on_broadcast).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(btn_row, text="Calculate position", command=self._on_calculate).pack(
            side=tk.LEFT
        )

    def _build_console(self) -> None:
        frame = ttk.LabelFrame(self._window, text="Console")
        frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(3, 6))

        self._console = tk.Text(
            frame,
            height=7,
            state=tk.DISABLED,
            wrap=tk.WORD,
            font=("monospace", 9),
            bg="#1e1e1e",
            fg="#cccccc",
            insertbackground="#cccccc",
            selectbackground="#3a5a8c",
        )
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self._console.yview)
        self._console.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._console.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

    # ------------------------------------------------------------------ #
    #  Event handlers                                                      #
    # ------------------------------------------------------------------ #

    def _on_map_click(self, coords: tuple[float, float]) -> None:
        self._pending_click = coords
        self._log(f"Map clicked: ({coords[0]:.6f}, {coords[1]:.6f})")
        self._refresh_map()

    def _on_set_position_from_map(self) -> None:
        if self._pending_click is None:
            self._log("No map position selected — click the map first.")
            return

        lat, lon = self._pending_click
        depth = self._parse_depth()
        coord = Coord(lat=lat, lon=lon, depth=depth)

        self._node.set_position(coord)
        self._sync_transport_position(coord)
        self._pending_click = None
        self._log(f"Position set: ({coord.lat:.6f}, {coord.lon:.6f}, {coord.depth:.1f})")

    def _on_set_depth(self) -> None:
        try:
            depth = float(self._depth_entry.get())
        except ValueError:
            self._log("Invalid depth value.")
            return

        self._node.set_depth(depth)
        pos = self._node.get_position()
        if pos is not None:
            self._sync_transport_position(pos)
        self._log(f"Depth set to {depth:.1f}m")

    def _on_request_range(self) -> None:
        target = self._range_target.get()
        if not target:
            self._log("No target selected.")
            return
        self._log(f"Ranging to {target}...")
        self._node.request_range(target)

    def _on_broadcast(self) -> None:
        if self._node.get_position() is None:
            self._log("Cannot broadcast: no position set.")
            return
        self._node.broadcast_position()
        self._log("Position broadcast sent.")

    def _on_calculate(self) -> None:
        result = self._node.calculate_position()
        if result is not None:
            self._sync_transport_position(result)
            self._log(f"Calculated position: ({result.lat:.6f}, {result.lon:.6f})")
        else:
            self._log("Cannot calculate: need 3+ nodes with position and range.")

    def _on_close(self) -> None:
        self._window.destroy()
        remaining = [
            w
            for w in self._root.winfo_children()
            if isinstance(w, tk.Toplevel) and w.winfo_exists()
        ]
        if not remaining:
            self._root.quit()

    # ------------------------------------------------------------------ #
    #  UI refresh (called via on_state_changed callback)                   #
    # ------------------------------------------------------------------ #

    def _refresh_ui(self) -> None:
        self._refresh_position_display()
        self._refresh_known_nodes()
        self._refresh_map()

    def _refresh_position_display(self) -> None:
        pos = self._node.get_position()
        if pos is not None:
            self._lat_var.set(f"{pos.lat:.6f}")
            self._lon_var.set(f"{pos.lon:.6f}")
            self._depth_display_var.set(f"{pos.depth:.1f}m")
        else:
            self._lat_var.set("—")
            self._lon_var.set("—")
            self._depth_display_var.set("—")

    def _refresh_known_nodes(self) -> None:
        for widget in self._known_nodes_frame.winfo_children():
            widget.destroy()

        known = self._node.get_known_nodes()
        if not known:
            ttk.Label(
                self._known_nodes_frame, text="No known nodes", foreground="gray"
            ).pack(anchor=tk.W)
            return

        for i, (nid, kn) in enumerate(sorted(known.items())):
            color = NODE_COLORS[i % len(NODE_COLORS)]
            row = ttk.Frame(self._known_nodes_frame)
            row.pack(fill=tk.X, pady=1)

            dot = tk.Canvas(row, width=10, height=10, highlightthickness=0)
            dot.create_oval(1, 1, 9, 9, fill=color, outline="")
            dot.pack(side=tk.LEFT, padx=(0, 4))

            ttk.Label(row, text=nid, font=("monospace", 10, "bold")).pack(
                side=tk.LEFT, padx=(0, 8)
            )

            if kn.position is not None:
                ttk.Label(
                    row,
                    text=f"({kn.position.lat:.4f}, {kn.position.lon:.4f})",
                    foreground="gray",
                ).pack(side=tk.LEFT, padx=(0, 8))
            else:
                ttk.Label(row, text="pos unknown", foreground="gray").pack(
                    side=tk.LEFT, padx=(0, 8)
                )

            if kn.last_range is not None:
                ttk.Label(row, text=f"{kn.last_range:.1f}m", foreground="green").pack(
                    side=tk.LEFT
                )
            else:
                ttk.Label(row, text="no range", foreground="gray").pack(side=tk.LEFT)

    def _refresh_map(self) -> None:
        # Remove old markers and paths
        for m in self._map_markers:
            try:
                m.delete()  # type: ignore[union-attr]
            except Exception:
                pass
        for p in self._map_paths:
            try:
                p.delete()  # type: ignore[union-attr]
            except Exception:
                pass
        self._map_markers.clear()
        self._map_paths.clear()

        # Own position (red)
        pos = self._node.get_position()
        if pos is not None:
            m = self._map.set_marker(
                pos.lat,
                pos.lon,
                text=f"{self._node.node_id} (me)",
                marker_color_circle=OWN_COLOR,
                marker_color_outside=OWN_COLOR,
            )
            self._map_markers.append(m)

        # Pending click (yellow)
        if self._pending_click is not None:
            m = self._map.set_marker(
                self._pending_click[0],
                self._pending_click[1],
                text="click",
                marker_color_circle="#f1c40f",
                marker_color_outside="#f1c40f",
            )
            self._map_markers.append(m)

        # Known nodes + range circles
        known = self._node.get_known_nodes()
        for i, (nid, kn) in enumerate(sorted(known.items())):
            color = NODE_COLORS[i % len(NODE_COLORS)]

            if kn.position is not None:
                m = self._map.set_marker(
                    kn.position.lat,
                    kn.position.lon,
                    text=nid,
                    marker_color_circle=color,
                    marker_color_outside=color,
                )
                self._map_markers.append(m)

                # Range circle
                if kn.last_range is not None and kn.last_range > 0:
                    pts = _circle_coords(
                        kn.position.lat, kn.position.lon, kn.last_range
                    )
                    p = self._map.set_path(pts, color=color, width=2)
                    self._map_paths.append(p)

    # ------------------------------------------------------------------ #
    #  Console                                                             #
    # ------------------------------------------------------------------ #

    def _log(self, text: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._console.configure(state=tk.NORMAL)
        self._console.insert(tk.END, f"[{timestamp}] {text}\n")
        self._console.see(tk.END)
        self._console.configure(state=tk.DISABLED)

    def _log_message(self, msg: Message) -> None:
        match msg:
            case PositionMessage(node_id=nid, coord=c):
                self._log(
                    f"Received position from {nid}: ({c.lat:.4f}, {c.lon:.4f}, {c.depth:.1f})"
                )
            case RangeResponseMessage(node_id=nid, timestamp=ts):
                kn = self._node.get_known_nodes().get(nid)
                if kn and kn.last_range is not None:
                    self._log(f"Range to {nid}: {kn.last_range:.2f}m (ts={ts})")
                else:
                    self._log(f"Range response from {nid}: ts={ts}")
            case UnknownMessage(raw=raw):
                self._log(f"Unknown: {raw}")

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _sync_transport_position(self, coord: Coord) -> None:
        """Keep MockTransport.position in sync (duck-typed, no-op for real serial)."""
        if hasattr(self._node.transport, "position"):
            self._node.transport.position = coord  # type: ignore[union-attr]

    def _parse_depth(self) -> float:
        try:
            return float(self._depth_entry.get())
        except ValueError:
            return 0.0
