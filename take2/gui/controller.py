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
from typing import Callable, Optional

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
SIM_COLOR = "#f1c40f"


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
        get_sim_pos_callback: Optional[Callable[[], Optional[Coord]]] = None,
        set_sim_pos_callback: Optional[Callable[[Coord], None]] = None,
    ) -> None:
        self._root = root
        self._peer_ids = peer_ids
        self._map_markers: list[object] = []
        self._map_paths: list[object] = []

        # Edit state
        self._editing_target: Optional[str] = None  # "me_pos", "me_depth", "sim_pos", or node_id
        self._editing_type: Optional[str] = None    # "pos" or "depth"
        self._edit_lat_var = tk.StringVar()
        self._edit_lon_var = tk.StringVar()
        self._edit_depth_var = tk.StringVar()

        # Simulated position callbacks
        self._get_sim_pos = get_sim_pos_callback
        self._set_sim_pos = set_sim_pos_callback
        self._show_sim_pos_var = tk.BooleanVar(value=True)

        # --- Create the window ---
        self._window = tk.Toplevel(root)
        self._window.title(f"Controller — Node {node_id} ({pretty_name})")
        self._window.protocol("WM_DELETE_WINDOW", self._on_close)
        if window_geometry:
            self._window.geometry(window_geometry)

        # --- Build all UI panels ---
        self._build_map(map_center, map_zoom)
        self._build_my_node_panel()
        self._build_simulated_pos_panel()
        self._build_registry_panel()
        self._build_actions_panel()
        self._build_console()

        # --- Create AcousticNode ---
        self._node = AcousticNode(
            node_id=node_id,
            transport=transport,
            position=position,
            on_state_changed=lambda: root.after(0, self._refresh_ui),
            on_message_received=lambda msg: root.after(0, self._log_message, msg),
        )

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

        self._map = TkinterMapView(frame, width=420, height=240, corner_radius=0)
        self._map.pack(fill=tk.X, padx=2, pady=2)
        self._map.set_position(center[0], center[1])
        self._map.set_zoom(zoom)
        self._map.add_left_click_map_command(self._on_map_click)

        self._map_hint_label = ttk.Label(
            frame, text="Editing position → click map to fill input", foreground="orange"
        )
        # Hidden by default, shown during position edit

    def _build_my_node_panel(self) -> None:
        frame = ttk.LabelFrame(self._window, text="My node")
        frame.pack(fill=tk.X, padx=6, pady=3)
        self._my_node_frame = ttk.Frame(frame)
        self._my_node_frame.pack(fill=tk.X, padx=4, pady=4)

    def _build_simulated_pos_panel(self) -> None:
        self._sim_pos_panel = ttk.LabelFrame(self._window, text="Simulated position (for ranging)")
        self._sim_pos_panel.pack(fill=tk.X, padx=6, pady=3)
        self._sim_pos_frame = ttk.Frame(self._sim_pos_panel)
        self._sim_pos_frame.pack(fill=tk.X, padx=4, pady=4)

    def _build_registry_panel(self) -> None:
        frame = ttk.LabelFrame(self._window, text="Registry (known nodes)")
        frame.pack(fill=tk.X, padx=6, pady=3)
        self._registry_frame = ttk.Frame(frame)
        self._registry_frame.pack(fill=tk.X, padx=4, pady=4)

    def _build_actions_panel(self) -> None:
        frame = ttk.LabelFrame(self._window, text="Actions")
        frame.pack(fill=tk.X, padx=6, pady=3)

        # Range row
        range_row = ttk.Frame(frame)
        range_row.pack(fill=tk.X, padx=4, pady=(4, 2))

        ttk.Label(range_row, text="Range to:").pack(side=tk.LEFT)
        self._range_target = ttk.Combobox(range_row, width=6)
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

    def _on_map_click(self, coords: tuple[float, float]) -> None:
        if self._editing_target and self._editing_type == "pos":
            self._edit_lat_var.set(f"{coords[0]:.6f}")
            self._edit_lon_var.set(f"{coords[1]:.6f}")

    def _start_edit(self, target: str, edit_type: str) -> None:
        self._editing_target = target
        self._editing_type = edit_type
        
        # Initialize vars
        if target == "me_pos":
            pos = self._node.get_position()
            self._edit_lat_var.set(f"{pos.lat:.6f}" if pos else "")
            self._edit_lon_var.set(f"{pos.lon:.6f}" if pos else "")
            self._edit_depth_var.set(f"{pos.depth:.1f}" if pos else "0.0")
        elif target == "me_depth":
            pos = self._node.get_position()
            self._edit_depth_var.set(f"{pos.depth:.1f}" if pos else "0.0")
        elif target == "sim_pos":
            pos = self._get_sim_pos() if self._get_sim_pos else None
            self._edit_lat_var.set(f"{pos.lat:.6f}" if pos else "")
            self._edit_lon_var.set(f"{pos.lon:.6f}" if pos else "")
            self._edit_depth_var.set(f"{pos.depth:.1f}" if pos else "0.0")
        else:
            # Registry node
            kn = self._node.get_known_nodes().get(target)
            if edit_type == "pos":
                self._edit_lat_var.set(f"{kn.position.lat:.6f}" if kn and kn.position else "")
                self._edit_lon_var.set(f"{kn.position.lon:.6f}" if kn and kn.position else "")
                self._edit_depth_var.set(f"{kn.position.depth:.1f}" if kn and kn.position else "0.0")
            else:
                self._edit_depth_var.set(f"{kn.position.depth:.1f}" if kn and kn.position else "0.0")

        if edit_type == "pos":
            self._map_hint_label.pack(pady=2)
        
        self._refresh_ui()

    def _cancel_edit(self) -> None:
        self._editing_target = None
        self._editing_type = None
        self._map_hint_label.pack_forget()
        self._refresh_ui()

    def _save_edit(self) -> None:
        target = self._editing_target
        etype = self._editing_type
        
        try:
            if etype == "pos":
                lat = float(self._edit_lat_var.get())
                lon = float(self._edit_lon_var.get())
                depth = float(self._edit_depth_var.get())
                coord = Coord(lat=lat, lon=lon, depth=depth)
                
                if target == "me_pos":
                    self._node.set_position(coord)
                elif target == "sim_pos":
                    if self._set_sim_pos:
                        self._set_sim_pos(coord)
                else:
                    self._node.set_known_node_position(target, coord)
            else:
                depth = float(self._edit_depth_var.get())
                if target == "me_depth":
                    self._node.set_depth(depth)
                else:
                    self._node.set_known_node_depth(target, depth)
        except ValueError:
            self._log("Invalid input values.")

        self._cancel_edit()

    def _on_add_node(self) -> None:
        # Simple dialog for ID
        dialog = tk.Toplevel(self._window)
        dialog.title("Add Node")
        dialog.geometry("200x100")
        ttk.Label(dialog, text="Node ID (3 digits):").pack(pady=5)
        entry = ttk.Entry(dialog)
        entry.pack(pady=5)
        def confirm():
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

    def _on_request_range(self) -> None:
        target = self._range_target.get()
        if not target:
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
    #  UI refresh                                                          #
    # ------------------------------------------------------------------ #

    def _refresh_ui(self) -> None:
        self._refresh_my_node_panel()
        self._refresh_sim_pos_panel()
        self._refresh_registry_panel()
        self._refresh_actions_dropdown()
        self._refresh_map()

    def _refresh_my_node_panel(self) -> None:
        for w in self._my_node_frame.winfo_children(): w.destroy()
        pos = self._node.get_position()
        
        # Position row
        row = ttk.Frame(self._my_node_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Position:", foreground="gray", width=10).pack(side=tk.LEFT)
        
        if self._editing_target == "me_pos":
            ttk.Entry(row, textvariable=self._edit_lat_var, width=10).pack(side=tk.LEFT, padx=2)
            ttk.Entry(row, textvariable=self._edit_lon_var, width=10).pack(side=tk.LEFT, padx=2)
            ttk.Entry(row, textvariable=self._edit_depth_var, width=5).pack(side=tk.LEFT, padx=2)
            ttk.Button(row, text="Save", command=self._save_edit).pack(side=tk.LEFT, padx=2)
            ttk.Button(row, text="X", command=self._cancel_edit).pack(side=tk.LEFT)
        else:
            val = f"{pos.lat:.6f}, {pos.lon:.6f}" if pos else "—"
            ttk.Label(row, text=val, font="monospace").pack(side=tk.LEFT)
            ttk.Button(row, text="Edit", command=lambda: self._start_edit("me_pos", "pos")).pack(side=tk.RIGHT)

        # Depth row
        row = ttk.Frame(self._my_node_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Depth:", foreground="gray", width=10).pack(side=tk.LEFT)
        
        if self._editing_target == "me_depth":
            ttk.Entry(row, textvariable=self._edit_depth_var, width=10).pack(side=tk.LEFT, padx=2)
            ttk.Button(row, text="Save", command=self._save_edit).pack(side=tk.LEFT, padx=2)
            ttk.Button(row, text="X", command=self._cancel_edit).pack(side=tk.LEFT)
        else:
            val = f"{pos.depth:.1f} m" if pos else "—"
            ttk.Label(row, text=val, font="monospace").pack(side=tk.LEFT)
            ttk.Button(row, text="Edit", command=lambda: self._start_edit("me_depth", "depth")).pack(side=tk.RIGHT)

    def _refresh_sim_pos_panel(self) -> None:
        for w in self._sim_pos_frame.winfo_children(): w.destroy()
        
        if self._get_sim_pos is None:
            # Real mode - disabled look
            ttk.Label(self._sim_pos_frame, text="N/A (real mode)", foreground="gray").pack()
            return

        pos = self._get_sim_pos()
        row = ttk.Frame(self._sim_pos_frame)
        row.pack(fill=tk.X)
        ttk.Label(row, text="Position:", foreground="gray", width=10).pack(side=tk.LEFT)
        
        if self._editing_target == "sim_pos":
            ttk.Entry(row, textvariable=self._edit_lat_var, width=10).pack(side=tk.LEFT, padx=2)
            ttk.Entry(row, textvariable=self._edit_lon_var, width=10).pack(side=tk.LEFT, padx=2)
            ttk.Entry(row, textvariable=self._edit_depth_var, width=5).pack(side=tk.LEFT, padx=2)
            ttk.Button(row, text="Save", command=self._save_edit).pack(side=tk.LEFT, padx=2)
            ttk.Button(row, text="X", command=self._cancel_edit).pack(side=tk.LEFT)
        else:
            val = f"{pos.lat:.6f}, {pos.lon:.6f}, {pos.depth:.1f}" if pos else "—"
            ttk.Label(row, text=val, font="monospace").pack(side=tk.LEFT)
            ttk.Button(row, text="Edit", command=lambda: self._start_edit("sim_pos", "pos")).pack(side=tk.RIGHT)
        
        ttk.Checkbutton(
            self._sim_pos_frame, text="Show simulated position on map", 
            variable=self._show_sim_pos_var, command=self._refresh_map
        ).pack(anchor=tk.W, pady=(4, 0))

    def _refresh_registry_panel(self) -> None:
        for w in self._registry_frame.winfo_children(): w.destroy()
        
        known = self._node.get_known_nodes()
        
        # Table headers
        header = ttk.Frame(self._registry_frame)
        header.pack(fill=tk.X)
        ttk.Label(header, text="ID", width=5, font="TkDefaultFont 9 bold").pack(side=tk.LEFT)
        ttk.Label(header, text="Position", width=20, font="TkDefaultFont 9 bold").pack(side=tk.LEFT)
        ttk.Label(header, text="Depth", width=8, font="TkDefaultFont 9 bold").pack(side=tk.LEFT)
        ttk.Label(header, text="Range", width=8, font="TkDefaultFont 9 bold").pack(side=tk.LEFT)

        for nid, kn in sorted(known.items()):
            row = ttk.Frame(self._registry_frame)
            row.pack(fill=tk.X, pady=1)
            
            if self._editing_target == nid:
                # Editing row
                ttk.Label(row, text=nid, width=5, font="monospace").pack(side=tk.LEFT)
                edit_f = ttk.Frame(row)
                edit_f.pack(side=tk.LEFT, fill=tk.X, expand=True)
                
                if self._editing_type == "pos":
                    ttk.Entry(edit_f, textvariable=self._edit_lat_var, width=10).pack(side=tk.LEFT, padx=1)
                    ttk.Entry(edit_f, textvariable=self._edit_lon_var, width=10).pack(side=tk.LEFT, padx=1)
                    ttk.Entry(edit_f, textvariable=self._edit_depth_var, width=4).pack(side=tk.LEFT, padx=1)
                else:
                    ttk.Entry(edit_f, textvariable=self._edit_depth_var, width=10).pack(side=tk.LEFT, padx=1)
                
                ttk.Button(edit_f, text="Save", command=self._save_edit).pack(side=tk.LEFT, padx=1)
                ttk.Button(edit_f, text="X", command=self._cancel_edit).pack(side=tk.LEFT)
            else:
                # Display row
                ttk.Label(row, text=nid, width=5, font="monospace").pack(side=tk.LEFT)
                pos_val = f"{kn.position.lat:.4f}, {kn.position.lon:.4f}" if kn.position else "—"
                ttk.Label(row, text=pos_val, width=20, font="monospace", foreground="gray").pack(side=tk.LEFT)
                depth_val = f"{kn.position.depth:.1f}m" if kn.position else "—"
                ttk.Label(row, text=depth_val, width=8, font="monospace", foreground="gray").pack(side=tk.LEFT)
                range_val = f"{kn.last_range:.1f}m" if kn.last_range is not None else "—"
                ttk.Label(row, text=range_val, width=8, font="monospace", foreground="green").pack(side=tk.LEFT)
                
                ttk.Button(row, text="Del", width=4, command=lambda n=nid: self._on_delete_node(n)).pack(side=tk.RIGHT)
                ttk.Button(row, text="D", width=3, command=lambda n=nid: self._start_edit(n, "depth")).pack(side=tk.RIGHT, padx=1)
                ttk.Button(row, text="P", width=3, command=lambda n=nid: self._start_edit(n, "pos")).pack(side=tk.RIGHT)

        ttk.Button(self._registry_frame, text="+ Add node", command=self._on_add_node).pack(anchor=tk.W, pady=4)

    def _refresh_actions_dropdown(self) -> None:
        ids = sorted(self._node.get_known_nodes().keys())
        self._range_target["values"] = ids

    def _refresh_map(self) -> None:
        for m in self._map_markers:
            try: m.delete()
            except: pass
        for p in self._map_paths:
            try: p.delete()
            except: pass
        self._map_markers.clear()
        self._map_paths.clear()

        # Own position (red)
        pos = self._node.get_position()
        if pos:
            m = self._map.set_marker(pos.lat, pos.lon, text=f"{self._node.node_id} (me)",
                                   marker_color_circle=OWN_COLOR, marker_color_outside=OWN_COLOR)
            self._map_markers.append(m)

        # Simulated position (dashed yellow)
        if self._show_sim_pos_var.get() and self._get_sim_pos:
            sim_pos = self._get_sim_pos()
            if sim_pos:
                m = self._map.set_marker(sim_pos.lat, sim_pos.lon, text="simulated",
                                       marker_color_circle=SIM_COLOR, marker_color_outside=SIM_COLOR)
                self._map_markers.append(m)

        # Known nodes
        known = self._node.get_known_nodes()
        for i, (nid, kn) in enumerate(sorted(known.items())):
            color = NODE_COLORS[i % len(NODE_COLORS)]
            if kn.position:
                m = self._map.set_marker(kn.position.lat, kn.position.lon, text=nid,
                                       marker_color_circle=color, marker_color_outside=color)
                self._map_markers.append(m)
                if kn.last_range is not None and kn.last_range > 0:
                    pts = _circle_coords(kn.position.lat, kn.position.lon, kn.last_range)
                    p = self._map.set_path(pts, color=color, width=2)
                    self._map_paths.append(p)

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
            case PositionMessage(node_id=nid, coord=c):
                self._log(f"Recv POS from {nid}: ({c.lat:.4f}, {c.lon:.4f}, {c.depth:.1f})")
            case RangeResponseMessage(node_id=nid, timestamp=ts):
                kn = self._node.get_known_nodes().get(nid)
                dist = f"{kn.last_range:.2f}m" if kn and kn.last_range is not None else "??m"
                self._log(f"Recv RANGE from {nid}: {dist} (ts={ts})")
            case UnknownMessage(raw=raw):
                self._log(f"Recv UNKNOWN: {raw}")
