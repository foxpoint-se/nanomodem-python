"""Per-node controller window with integrated map visualization.

Each ControllerWindow manages a single AcousticNode and shows
that node's worldview: own position, known nodes, range circles,
and a console for events.
"""

from __future__ import annotations

import math
import re
import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Callable, Optional

from nanomodem.constants import SOUND_SPEED_WATER_M_S
from nanomodem.drivers.v3_spec import TEST_MESSAGE_PAYLOAD, supply_voltage_volts
from nanomodem.node import AcousticNode
from nanomodem.positioning.types import KnownNode
from nanomodem.protocols import TransportProtocol
from nanomodem.transports.mock import MockTransport
from nanomodem.types import (
    Coord,
    LocalAckMessage,
    Message,
    ModemStatusMessage,
    PositionMessage,
    QualityIndicatorMessage,
    RangeResponseMessage,
    UnknownMessage,
    V3TestBroadcastMessage,
)
from PIL import Image, ImageDraw, ImageTk
from tkintermapview import TkinterMapView
from tkintermapview.canvas_position_marker import CanvasPositionMarker
from tkintermapview.map_widget import CanvasPath

NODE_COLORS = [
    "#3498db",  # Blue
    "#2ecc71",  # Green
    "#e67e22",  # Orange
    "#9b59b6",  # Purple
    "#1abc9c",  # Turquoise
    "#f39c12",  # Yellow
    "#d35400",  # Pumpkin
    "#c0392b",  # Pomegranate
    "#8e44ad",  # Wisteria
    "#273c75",  # Mazarine Blue
]
OWN_COLOR_OUTSIDE = "black"
OWN_COLOR_CIRCLE = "white"
KNOWN_COLOR_CIRCLE = "white"
MAP_SELECTION_COLOR_OUTSIDE = "grey"
MAP_SELECTION_COLOR_CIRCLE = "white"


def _circle_coords(lat: float, lon: float, radius_m: float, n: int = 48) -> list[tuple[float, float]]:
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
        transport: TransportProtocol,
        peer_ids: list[str],
        map_center: tuple[float, float] = (59.310153, 17.975189),
        map_zoom: int = 16,
        position: Optional[Coord] = None,
        window_geometry: Optional[str] = None,
        sound_speed: float = SOUND_SPEED_WATER_M_S,
    ) -> None:
        self._root = root
        self._peer_ids = peer_ids
        self._markers: dict[str, CanvasPositionMarker] = {}  # node_id -> marker
        self._paths: dict[str, CanvasPath] = {}  # node_id -> path (range circle)
        self._registry_rows: dict[str, dict[str, ttk.Frame | ttk.Label]] = {}
        self._icon_cache: dict[str, ImageTk.PhotoImage] = {}

        # Edit state
        self._editing_target: Optional[str] = None  # "me_pos", "me_depth", or node_id
        self._editing_type: Optional[str] = None  # "pos" or "depth"
        self._selection_marker_pos: Optional[tuple[float, float]] = None
        self._edit_var = tk.StringVar()
        self._edit_var.trace_add("write", self._on_edit_var_changed)
        self._debounce_timer: Optional[str] = None
        self._shutdown_callbacks: list[Callable[[], None]] = []
        self._shutdown_done = False

        # --- Create the window ---
        self._window = tk.Toplevel(root)
        self._window.title(f"Controller — Node {node_id} ({pretty_name})")
        self._window.protocol("WM_DELETE_WINDOW", self._on_close)
        if window_geometry:
            self._window.geometry(window_geometry)

        # --- Build all UI panels ---
        self._build_map(map_center, map_zoom)
        self._build_my_node_panel()
        self._build_registry_panel()
        self._build_actions_panel()
        self._build_console()

        # --- Create AcousticNode ---
        def _on_depth_changed(_depth: float) -> None:
            root.after(0, self._refresh_ui)

        def _on_known_nodes_changed(_known: dict[str, KnownNode]) -> None:
            root.after(0, self._refresh_ui)

        def _on_message_received(msg: Message) -> None:
            root.after(0, self._log_message, msg)

        self._node = AcousticNode(
            node_id=node_id,
            transport=transport,
            position=position,
            sound_speed=sound_speed,
            on_position_changed=self._handle_position_changed,
            on_depth_changed=_on_depth_changed,
            on_known_nodes_changed=_on_known_nodes_changed,
            on_message_received=_on_message_received,
        )

        self._refresh_ui()

    @property
    def node(self) -> AcousticNode:
        return self._node

    def register_shutdown_callback(self, callback: Callable[[], None]) -> None:
        """Run callback once when this window closes (e.g. stop metadata client)."""
        self._shutdown_callbacks.append(callback)

    def _shutdown(self) -> None:
        if self._shutdown_done:
            return
        self._shutdown_done = True
        for callback in self._shutdown_callbacks:
            callback()
        stop = getattr(self._node.transport, "stop", None)
        if callable(stop):
            stop()

    # ------------------------------------------------------------------ #
    #  UI construction                                                     #
    # ------------------------------------------------------------------ #

    def _build_map(self, center: tuple[float, float], zoom: int) -> None:
        frame = ttk.LabelFrame(self._window, text="Map — what this node knows")
        frame.pack(fill=tk.X, padx=6, pady=(6, 3))

        self._map = TkinterMapView(frame, width=420, height=240, corner_radius=0)
        self._map.pack(fill=tk.X, padx=2, pady=2)
        self._map.set_position(center[0], center[1])
        self._map.set_zoom(zoom)
        self._map.add_left_click_map_command(self._on_map_click)

        self._map_hint_label = ttk.Label(frame, text="Editing position → click map to fill input", foreground="orange")
        # Hidden by default, shown during position edit

    def _on_map_click(self, coords: tuple[float, float]) -> None:
        if self._editing_target and self._editing_type == "pos":
            self._selection_marker_pos = coords
            self._edit_var.set(f"{coords[0]:.6f}, {coords[1]:.6f}")
            self._refresh_map()

    def _build_my_node_panel(self) -> None:
        frame = ttk.LabelFrame(self._window, text="My node")
        frame.pack(fill=tk.X, padx=6, pady=3)
        self._my_node_frame = ttk.Frame(frame)
        self._my_node_frame.pack(fill=tk.X, padx=4, pady=4)

        # --- Position Row ---
        self._me_pos_row = ttk.Frame(self._my_node_frame)
        self._me_pos_row.pack(fill=tk.X, pady=2)
        ttk.Label(self._me_pos_row, text="Position:", foreground="gray", width=10).pack(side=tk.LEFT)

        # Display sub-frame
        self._me_pos_display_f = ttk.Frame(self._me_pos_row)
        self._me_pos_val_label = ttk.Label(self._me_pos_display_f, text="—", font="monospace")
        self._me_pos_val_label.pack(side=tk.LEFT)
        ttk.Button(self._me_pos_display_f, text="Edit pos", command=lambda: self._start_edit("me_pos", "pos")).pack(
            side=tk.RIGHT
        )

        # Edit sub-frame
        self._me_pos_edit_f = ttk.Frame(self._me_pos_row)
        ttk.Entry(self._me_pos_edit_f, textvariable=self._edit_var, width=25).pack(side=tk.LEFT, padx=2)
        ttk.Button(self._me_pos_edit_f, text="Save", command=self._save_edit).pack(side=tk.LEFT, padx=2)
        ttk.Button(self._me_pos_edit_f, text="X", command=self._cancel_edit).pack(side=tk.LEFT)

        # --- Depth Row ---
        self._me_depth_row = ttk.Frame(self._my_node_frame)
        self._me_depth_row.pack(fill=tk.X, pady=2)
        ttk.Label(self._me_depth_row, text="Depth:", foreground="gray", width=10).pack(side=tk.LEFT)

        # Display sub-frame
        self._me_depth_display_f = ttk.Frame(self._me_depth_row)
        self._me_depth_val_label = ttk.Label(self._me_depth_display_f, text="—", font="monospace")
        self._me_depth_val_label.pack(side=tk.LEFT)
        ttk.Button(
            self._me_depth_display_f, text="Edit depth", command=lambda: self._start_edit("me_depth", "depth")
        ).pack(side=tk.RIGHT)

        # Edit sub-frame
        self._me_depth_edit_f = ttk.Frame(self._me_depth_row)
        ttk.Entry(self._me_depth_edit_f, textvariable=self._edit_var, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(self._me_depth_edit_f, text="Save", command=self._save_edit).pack(side=tk.LEFT, padx=2)
        ttk.Button(self._me_depth_edit_f, text="X", command=self._cancel_edit).pack(side=tk.LEFT)

    def _build_registry_panel(self) -> None:
        frame = ttk.LabelFrame(self._window, text="Registry (known nodes)")
        frame.pack(fill=tk.X, padx=6, pady=3)
        self._registry_frame = ttk.Frame(frame)
        self._registry_frame.pack(fill=tk.X, padx=4, pady=4)

        # Table headers
        self._registry_header = ttk.Frame(self._registry_frame)
        self._registry_header.pack(fill=tk.X)
        ttk.Label(self._registry_header, text="ID", width=5, font="TkDefaultFont 9 bold").pack(side=tk.LEFT)
        ttk.Label(self._registry_header, text="Position", width=20, font="TkDefaultFont 9 bold").pack(side=tk.LEFT)
        ttk.Label(self._registry_header, text="Depth", width=8, font="TkDefaultFont 9 bold").pack(side=tk.LEFT)
        ttk.Label(self._registry_header, text="Range", width=8, font="TkDefaultFont 9 bold").pack(side=tk.LEFT)

        self._registry_rows_container = ttk.Frame(self._registry_frame)
        self._registry_rows_container.pack(fill=tk.X)

        ttk.Button(self._registry_frame, text="+ Add node", command=self._on_add_node).pack(anchor=tk.W, pady=4)

    def _build_actions_panel(self) -> None:
        frame = ttk.LabelFrame(self._window, text="Actions")
        frame.pack(fill=tk.X, padx=6, pady=3)

        # Range row
        range_row = ttk.Frame(frame)
        range_row.pack(fill=tk.X, padx=4, pady=(4, 2))

        ttk.Label(range_row, text="Target:").pack(side=tk.LEFT)
        self._range_target = ttk.Combobox(range_row, width=6)
        self._range_target.pack(side=tk.LEFT, padx=4)
        ttk.Button(range_row, text="Request range", command=self._on_request_range).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(range_row, text="Request test", command=self._on_request_test).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(range_row, text="Query quality", command=self._on_query_quality).pack(side=tk.LEFT)

        # Button row
        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=tk.X, padx=4, pady=(2, 4))

        ttk.Button(btn_row, text="Broadcast position", command=self._on_broadcast).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_row, text="Calculate position", command=self._on_calculate).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_row, text="Get info from device", command=self._on_get_modem_info).pack(side=tk.LEFT)

    def _build_console(self) -> None:
        frame = ttk.LabelFrame(self._window, text="Console")
        frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(3, 6))

        self._console = tk.Text(
            frame,
            height=6,
            state=tk.DISABLED,
            wrap=tk.WORD,
            font=("monospace", 9),
            bg="#1e1e1e",
            fg="#cccccc",
        )
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self._console.yview)
        self._console.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._console.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

    # ------------------------------------------------------------------ #
    #  Event handlers                                                      #
    # ------------------------------------------------------------------ #

    def _on_edit_var_changed(self, *args: object) -> None:
        """Handle changes to the single edit input field."""
        if not self._editing_target or self._editing_type != "pos":
            return

        # If the field is empty, clear the selection marker immediately
        if not self._edit_var.get().strip():
            self._selection_marker_pos = None
            self._refresh_map()
            if self._debounce_timer:
                self._root.after_cancel(self._debounce_timer)
                self._debounce_timer = None
            return

        # Debounce the map update
        if self._debounce_timer:
            self._root.after_cancel(self._debounce_timer)

        self._debounce_timer = self._root.after(500, self._sync_selection_from_input)

    def _sync_selection_from_input(self) -> None:
        """Parse input and update selection marker if valid."""
        self._debounce_timer = None
        val = self._edit_var.get()

        # Strict pattern: Number.X, Number.Y
        # Allows optional spaces, requires at least one decimal digit for both
        match = re.match(r"^\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\s*$", val)
        if match:
            try:
                lat = float(match.group(1))
                lon = float(match.group(2))
                self._selection_marker_pos = (lat, lon)
                self._refresh_map()
            except ValueError:
                pass

    def _start_edit(self, target: str, edit_type: str) -> None:
        self._editing_target = target
        self._editing_type = edit_type
        self._selection_marker_pos = None

        # Always start with an empty field as requested
        self._edit_var.set("")

        if edit_type == "pos":
            self._map_hint_label.pack(pady=2)

        self._refresh_ui()

    def _cancel_edit(self) -> None:
        self._editing_target = None
        self._editing_type = None
        self._selection_marker_pos = None
        self._map_hint_label.pack_forget()
        self._refresh_ui()

    def _save_edit(self) -> None:
        target = self._editing_target
        etype = self._editing_type
        val = self._edit_var.get()

        try:
            if etype == "pos":
                # Use the same strict parsing as the debounced sync
                match = re.match(r"^\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\s*$", val)
                if not match:
                    self._log("Invalid format. Use 'lat.x, lon.y'")
                    return

                lat = float(match.group(1))
                lon = float(match.group(2))
                coord = Coord(lat=lat, lon=lon)

                if target == "me_pos":
                    self._node.set_position(coord)
                elif target is not None:
                    self._node.set_known_node_position(target, coord)
            else:
                depth = float(val)
                if target == "me_depth":
                    self._node.set_depth(depth)
                elif target is not None:
                    self._node.set_known_node_depth(target, depth)
        except ValueError:
            self._log("Invalid numeric values.")

        self._cancel_edit()

    def _on_add_node(self) -> None:
        # Simple dialog for ID
        dialog = tk.Toplevel(self._window)
        dialog.title("Add Node")
        dialog.geometry("200x100")
        ttk.Label(dialog, text="Node ID (3 digits):").pack(pady=5)
        entry = ttk.Entry(dialog)
        entry.pack(pady=5)

        def confirm() -> None:
            nid = entry.get()
            if len(nid) == 3 and nid.isdigit():
                self._node.set_known_node_position(nid, None)
                dialog.destroy()
                self._start_edit(nid, "pos")
            else:
                self._log("Invalid ID.")

        ttk.Button(dialog, text="Add", command=confirm).pack()

    def _on_delete_node(self, node_id: str) -> None:
        self._node.delete_known_node(node_id)
        self._refresh_ui()

    def _on_request_range(self) -> None:
        target = self._range_target.get().strip()
        if not target:
            return
        self._log(f"Ranging to {target}...")
        self._node.request_range(target)

    def _on_request_test(self) -> None:
        target = self._range_target.get().strip()
        if not target:
            return
        self._log(f"Requesting test from {target} ($T)...")
        self._node.request_test(target)

    def _on_query_quality(self) -> None:
        self._log("Querying link quality ($Q)...")
        self._node.query_quality()

    def _on_broadcast(self) -> None:
        if self._node.get_position() is None:
            self._log("Cannot broadcast: no position set.")
            return
        self._node.broadcast_position()
        self._log("Position broadcast sent.")

    def _on_calculate(self) -> None:
        result = self._node.calculate_position()
        if result is not None:
            self._log(f"Calculated position: ({result.lat:.6f}, {result.lon:.6f})")
        else:
            self._log("Cannot calculate: need 3+ nodes with position and range.")

    def _on_get_modem_info(self) -> None:
        self._log("Querying modem status ($?)...")
        self._node.query_modem_status()

    def _handle_position_changed(self, pos: Optional[Coord]) -> None:
        """Refresh UI when node position changes."""
        transport = self._node.transport
        if isinstance(transport, MockTransport):
            transport.position = pos
        self._root.after(0, self._refresh_ui)

    def _on_close(self) -> None:
        self._shutdown()
        self._window.destroy()
        remaining = [w for w in self._root.winfo_children() if isinstance(w, tk.Toplevel) and w.winfo_exists()]
        if not remaining:
            self._root.quit()

    # ------------------------------------------------------------------ #
    #  UI refresh                                                          #
    # ------------------------------------------------------------------ #

    def _refresh_ui(self) -> None:
        self._refresh_my_node_panel()
        self._refresh_registry_panel()
        self._refresh_actions_dropdown()
        self._refresh_map()

    def _refresh_my_node_panel(self) -> None:
        pos = self._node.get_position()

        # Update Position Row
        if self._editing_target == "me_pos":
            self._me_pos_display_f.pack_forget()
            self._me_pos_edit_f.pack(side=tk.LEFT, fill=tk.X, expand=True)
        else:
            self._me_pos_edit_f.pack_forget()
            self._me_pos_display_f.pack(side=tk.LEFT, fill=tk.X, expand=True)
            val = f"{pos.lat:.6f}, {pos.lon:.6f}" if pos else "—"
            self._me_pos_val_label.configure(text=val)

        # Update Depth Row
        if self._editing_target == "me_depth":
            self._me_depth_display_f.pack_forget()
            self._me_depth_edit_f.pack(side=tk.LEFT, fill=tk.X, expand=True)
        else:
            self._me_depth_edit_f.pack_forget()
            self._me_depth_display_f.pack(side=tk.LEFT, fill=tk.X, expand=True)
            depth = self._node._depth
            val = f"{depth:.1f} m"
            self._me_depth_val_label.configure(text=val)

    def _refresh_registry_panel(self) -> None:
        known = self._node.get_known_nodes()

        # Remove widgets for nodes that are no longer in the registry
        current_ids = set(known.keys())
        stored_ids = set(self._registry_rows.keys())
        for nid in stored_ids - current_ids:
            self._registry_rows[nid]["row_frame"].destroy()
            del self._registry_rows[nid]

        # Add or update widgets for each node
        for nid, kn in sorted(known.items()):
            if nid not in self._registry_rows:
                # Create row frame
                row_frame = ttk.Frame(self._registry_rows_container)
                row_frame.pack(fill=tk.X, pady=1)

                # ID label
                ttk.Label(row_frame, text=nid, width=5, font="monospace").pack(side=tk.LEFT)

                # Display sub-frame
                display_f = ttk.Frame(row_frame)
                pos_label = ttk.Label(display_f, text="—", width=20, font="monospace", foreground="gray")
                pos_label.pack(side=tk.LEFT)
                depth_label = ttk.Label(display_f, text="—", width=8, font="monospace", foreground="gray")
                depth_label.pack(side=tk.LEFT)
                range_label = ttk.Label(display_f, text="—", width=8, font="monospace")
                range_label.pack(side=tk.LEFT)

                def _make_delete(n: str) -> Callable[[], None]:
                    return lambda: self._on_delete_node(n)

                def _make_edit(n: str, t: str) -> Callable[[], None]:
                    return lambda: self._start_edit(n, t)

                ttk.Button(display_f, text="🗑", width=3, command=_make_delete(nid)).pack(side=tk.RIGHT)
                ttk.Button(display_f, text="Edit depth", width=9, command=_make_edit(nid, "depth")).pack(
                    side=tk.RIGHT, padx=1
                )
                ttk.Button(display_f, text="Edit pos", width=8, command=_make_edit(nid, "pos")).pack(side=tk.RIGHT)

                # Edit sub-frame
                edit_f = ttk.Frame(row_frame)

                self._registry_rows[nid] = {
                    "row_frame": row_frame,
                    "display_f": display_f,
                    "pos_label": pos_label,
                    "depth_label": depth_label,
                    "range_label": range_label,
                    "edit_f": edit_f,
                }

            row_info = self._registry_rows[nid]

            # Deterministic color based on ID
            color_idx: int
            try:
                color_idx = int(nid) % len(NODE_COLORS)
            except ValueError:
                color_idx = hash(nid) % len(NODE_COLORS)
            color = NODE_COLORS[color_idx]

            if self._editing_target == nid:
                row_info["display_f"].pack_forget()
                row_info["edit_f"].pack(side=tk.LEFT, fill=tk.X, expand=True)

                # Re-create edit widgets to ensure correct type (pos vs depth)
                for w in row_info["edit_f"].winfo_children():
                    w.destroy()

                if self._editing_type == "pos":
                    ttk.Entry(row_info["edit_f"], textvariable=self._edit_var, width=22).pack(side=tk.LEFT, padx=1)
                else:
                    ttk.Entry(row_info["edit_f"], textvariable=self._edit_var, width=10).pack(side=tk.LEFT, padx=1)

                ttk.Button(row_info["edit_f"], text="Save", command=self._save_edit).pack(side=tk.LEFT, padx=1)
                ttk.Button(row_info["edit_f"], text="X", command=self._cancel_edit).pack(side=tk.LEFT)
            else:
                row_info["edit_f"].pack_forget()
                row_info["display_f"].pack(side=tk.LEFT, fill=tk.X, expand=True)

                pos_val = f"{kn.position.lat:.4f}, {kn.position.lon:.4f}" if kn.position else "—"
                row_info["pos_label"].configure({"text": pos_val})
                depth_val = f"{kn.depth:.1f}m"
                row_info["depth_label"].configure({"text": depth_val})
                range_val = f"{kn.last_range:.1f}m" if kn.last_range is not None else "—"
                row_info["range_label"].configure({"text": range_val, "foreground": color})

    def _refresh_actions_dropdown(self) -> None:
        ids = sorted(self._node.get_known_nodes().keys())
        self._range_target["values"] = ids

    def _refresh_map(self) -> None:
        known = self._node.get_known_nodes()
        current_ids = set(known.keys()) | {"me", "selection"}
        stored_ids = set(self._markers.keys())

        # Remove markers for nodes no longer present
        for nid in stored_ids - current_ids:
            self._delete_marker(nid)
            self._delete_path(nid)

        # 1. Own position (Circle, transparent center)
        pos = self._node.get_position()
        if pos:
            icon = self._get_circle_icon("black", transparent=True)
            self._update_or_create_marker(
                "me",
                pos.lat,
                pos.lon,
                text=f"{self._node.node_id} (me)",
                icon=icon,
            )
        else:
            self._delete_marker("me")

        # 2. Known nodes (Colored ring, transparent center)
        for nid, kn in sorted(known.items()):
            # Deterministic color based on ID
            try:
                color_idx = int(nid) % len(NODE_COLORS)
            except ValueError:
                color_idx = hash(nid) % len(NODE_COLORS)
            color = NODE_COLORS[color_idx]

            if kn.position:
                icon = self._get_circle_icon(color, transparent=True)
                self._update_or_create_marker(nid, kn.position.lat, kn.position.lon, text=nid, icon=icon)

                # Range circle
                if kn.last_range is not None and kn.last_range > 0:
                    pts = _circle_coords(kn.position.lat, kn.position.lon, kn.last_range)
                    self._update_or_create_path(nid, pts, color=color)
                else:
                    self._delete_path(nid)
            else:
                self._delete_marker(nid)
                self._delete_path(nid)

        # Map Selection (Grey ring, transparent center)
        if self._selection_marker_pos:
            icon = self._get_circle_icon("grey", transparent=True)
            self._update_or_create_marker(
                "selection", self._selection_marker_pos[0], self._selection_marker_pos[1], text="Selection", icon=icon
            )
        else:
            self._delete_marker("selection")

    def _get_circle_icon(
        self, color: str, size: int = 16, thickness: int = 2, transparent: bool = True
    ) -> ImageTk.PhotoImage:
        """Create or retrieve a circular icon from cache."""
        cache_key = f"{color}_{size}_{thickness}_{transparent}"
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]

        # Create RGBA image with transparent background
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        if transparent:
            # Draw only the outline
            draw.ellipse((0, 0, size - 1, size - 1), outline=color, width=thickness)
        else:
            # Draw solid circle
            draw.ellipse((0, 0, size - 1, size - 1), fill=color)

        icon = ImageTk.PhotoImage(img)
        self._icon_cache[cache_key] = icon
        return icon

    def _update_or_create_marker(
        self,
        key: str,
        lat: float,
        lon: float,
        text: str,
        icon: Optional[ImageTk.PhotoImage] = None,
        color_circle: Optional[str] = None,
        color_outside: Optional[str] = None,
    ) -> None:
        if key in self._markers:
            marker = self._markers[key]
            try:
                marker.set_position(lat, lon)
                marker.set_text(text)
                return
            except tk.TclError:
                # Stale widget (e.g. map redraw) — drop and recreate below.
                self._delete_marker(key)

        if icon:
            m = self._map.set_marker(lat, lon, text=text, icon=icon, icon_anchor="center", text_color="black")
        else:
            m = self._map.set_marker(
                lat,
                lon,
                text=text,
                marker_color_circle=color_circle,
                marker_color_outside=color_outside,
                text_color="black",
            )
        self._markers[key] = m

    def _update_or_create_path(self, key: str, position_list: list[tuple[float, float]], color: str) -> None:
        # tkintermapview paths don't support set_position_list easily without flickering
        # so we delete and recreate, but only for paths (less frequent than markers)
        self._delete_path(key)
        p = self._map.set_path(position_list, color=color, width=2)
        self._paths[key] = p

    def _delete_marker(self, key: str) -> None:
        if key in self._markers:
            marker = self._markers.pop(key)
            try:
                marker.delete()
            except tk.TclError:
                pass

    def _delete_path(self, key: str) -> None:
        if key in self._paths:
            path_obj = self._paths.pop(key)
            try:
                path_obj.delete()
            except tk.TclError:
                pass

    # ------------------------------------------------------------------ #
    #  Console                                                             #
    # ------------------------------------------------------------------ #

    def _log(self, text: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self._console.configure(state=tk.NORMAL)
        self._console.insert(tk.END, f"[{ts}] {text}\n")
        self._console.see(tk.END)
        self._console.configure(state=tk.DISABLED)

    def _log_message(self, msg: Message) -> None:
        match msg:
            case PositionMessage(node_id=nid, coord=c, depth=d):
                self._log(f"Recv POS from {nid}: ({c.lat:.4f}, {c.lon:.4f}, {d:.1f}m)")
            case RangeResponseMessage(node_id=nid, timestamp=ts):
                kn = self._node.get_known_nodes().get(nid)
                dist = f"{kn.last_range:.2f}m" if kn and kn.last_range is not None else "??m"
                self._log(f"Recv RANGE from {nid}: {dist} (ts={ts})")
            case LocalAckMessage(command=cmd, target_id=tid):
                self._log(f"Local ack {cmd} target={tid}")
            case QualityIndicatorMessage(bytes_corrected=bytes_corrected):
                if bytes_corrected is None:
                    self._log("Quality: rejected")
                else:
                    self._log(f"Quality: {bytes_corrected} bytes corrected")
            case ModemStatusMessage(node_id=nid, voltage_raw=raw):
                volts = supply_voltage_volts(raw)
                self._log(f"Modem status: id={nid}, {volts:.2f} V (raw {raw})")
            case V3TestBroadcastMessage(node_id=nid):
                self._log(f"Recv TEST broadcast from {nid}: {TEST_MESSAGE_PAYLOAD}")
            case UnknownMessage(raw=raw):
                self._log(f"Recv UNKNOWN: {raw}")
