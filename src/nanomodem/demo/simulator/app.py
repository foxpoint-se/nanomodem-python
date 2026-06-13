"""God View Simulator GUI application.

Provides a God View UI for managing the physical world state
and acoustic propagation in multi-process simulations.
"""

from __future__ import annotations

import logging
import queue
import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Callable, Optional

from PIL import Image, ImageDraw, ImageTk
from tkintermapview import TkinterMapView
from tkintermapview.canvas_position_marker import CanvasPositionMarker

from nanomodem.constants import SOUND_SPEED_WATER_M_S, validate_sound_speed
from nanomodem.demo.simulator.backends import HybridBackend
from nanomodem.demo.simulator.state import SimulatorState
from nanomodem.types import Coord

logger = logging.getLogger(__name__)

# Node colors (matching controller)
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

PHYSICAL_MARKER_STYLE = "circle"  # Filled circle for physical truth
BELIEF_MARKER_STYLE = "circle_outline"  # Hollow circle for belief
_REFRESH_UI = object()


def _circle_icon(color: str, transparent: bool = False) -> ImageTk.PhotoImage:
    """Generate a circle icon for markers."""
    size = 24
    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    if transparent:
        # Hollow circle
        draw.ellipse([2, 2, size - 2, size - 2], outline=color, width=3)
    else:
        # Filled circle
        draw.ellipse([2, 2, size - 2, size - 2], fill=color, outline="black", width=2)

    return ImageTk.PhotoImage(img)


class SimulatorWindow:
    """God View Simulator GUI."""

    def __init__(
        self,
        root: tk.Tk,
        state: SimulatorState,
        backend: HybridBackend,
        map_center: tuple[float, float] = (59.310153, 17.975189),
        map_zoom: int = 16,
    ) -> None:
        self._root = root
        self.state = state
        self.backend = backend

        self._markers: dict[str, CanvasPositionMarker] = {}
        self._icon_cache: dict[str, ImageTk.PhotoImage] = {}
        self._registry_rows: dict[str, dict[str, ttk.Frame | ttk.Label]] = {}

        # Edit state (matching Controller pattern)
        self._editing_target: Optional[str] = None  # node_id being edited
        self._selection_marker_pos: Optional[tuple[float, float]] = None
        self._edit_var = tk.StringVar()
        self._ui_queue: queue.Queue[object] = queue.Queue()

        # Window
        self._window = tk.Toplevel(root)
        self._window.title("God View Simulator")
        self._window.geometry("800x900")
        self._window.protocol("WM_DELETE_WINDOW", self._on_close)

        # Build UI
        self._build_map(map_center, map_zoom)
        self._build_node_registry()
        self._build_console()

        # Wire backend callbacks
        self.backend.on_message = self._handle_message
        self.backend.on_register = self._handle_registration
        self.backend.on_raw_traffic = lambda node_id, data: self._log_console(
            f"[RAW] {node_id}: {data.decode('ascii', errors='replace').strip()}"
        )
        self.backend.on_interpreted = self._log_console

        # Start backend
        self.backend.start()

        self._root.after(50, self._process_ui_queue)

        # Initial refresh
        self._refresh_ui()

    @property
    def window(self) -> tk.Toplevel:
        return self._window

    def _build_map(self, center: tuple[float, float], zoom: int) -> None:
        map_frame = ttk.Frame(self._window)
        map_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self._map = TkinterMapView(map_frame, corner_radius=0)
        self._map.set_position(center[0], center[1])
        self._map.set_zoom(zoom)
        self._map.pack(fill=tk.BOTH, expand=True)

        self._map.add_left_click_map_command(self._on_map_click)

        self._map_hint_label = ttk.Label(
            map_frame, text="Editing position → click map to fill input", foreground="orange"
        )

    def _build_node_registry(self) -> None:
        registry_frame = ttk.LabelFrame(self._window, text="Node Registry")
        registry_frame.pack(fill=tk.X, padx=6, pady=3)

        # Header
        header = ttk.Frame(registry_frame)
        header.pack(fill=tk.X, padx=4, pady=(4, 2))

        ttk.Label(header, text="ID", width=8).pack(side=tk.LEFT, padx=2)
        ttk.Label(header, text="Transport", width=15).pack(side=tk.LEFT, padx=2)
        ttk.Label(header, text="Physical Position", width=35).pack(side=tk.LEFT, padx=2)

        self._registry_container = ttk.Frame(registry_frame)
        self._registry_container.pack(fill=tk.X, padx=4, pady=4)

    def _build_console(self) -> None:
        console_frame = ttk.LabelFrame(self._window, text="Console (Message Events)")
        console_frame.pack(fill=tk.BOTH, expand=False, padx=6, pady=3)

        self._console = tk.Text(console_frame, height=10, state=tk.DISABLED, font="monospace", wrap=tk.WORD)
        self._console.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        scrollbar = ttk.Scrollbar(console_frame, command=self._console.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._console.configure(yscrollcommand=scrollbar.set)

    def _on_close(self) -> None:
        self.backend.stop()
        self._window.destroy()

    def _log_console(self, text: str) -> None:
        """Queue console output for the Tk main thread (backend callbacks run elsewhere)."""
        self._ui_queue.put(text)

    def _process_ui_queue(self) -> None:
        refresh = False
        while True:
            try:
                item = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            if item is _REFRESH_UI:
                refresh = True
            elif isinstance(item, str):
                self._write_console(item)
        if refresh:
            self._refresh_ui()
        self._root.after(50, self._process_ui_queue)

    def _write_console(self, text: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self._console.configure(state=tk.NORMAL)
        self._console.insert(tk.END, f"[{ts}] {text}\n")
        self._console.see(tk.END)
        self._console.configure(state=tk.DISABLED)

    def _handle_message(self, node_id: str, data: bytes) -> None:
        """Callback when backend receives a message from a node.

        Note: Raw traffic is now logged via on_raw_traffic callback.
        This method is kept for backward compatibility but may be deprecated.
        """
        pass

    def _handle_registration(self, node_id: str) -> None:
        """Callback when a new node registers."""
        self._log_console(f"Node {node_id} connected")
        self._ui_queue.put(_REFRESH_UI)

    def _on_map_click(self, coords: tuple[float, float]) -> None:
        """Handle map click when editing position."""
        if self._editing_target:
            self._selection_marker_pos = coords
            self._edit_var.set(f"{coords[0]:.6f}, {coords[1]:.6f}")
            self._refresh_map()

    def _start_edit(self, node_id: str) -> None:
        """Start editing a node's physical position."""
        self._editing_target = node_id
        self._selection_marker_pos = None

        pos = self.state.get_physical_position(node_id)
        if pos:
            coord, depth = pos
            self._edit_var.set(f"{coord.lat:.6f}, {coord.lon:.6f}, {depth:.1f}")
        else:
            self._edit_var.set("")

        self._map_hint_label.pack(pady=2)
        self._refresh_ui()

    def _cancel_edit(self) -> None:
        """Cancel editing."""
        self._editing_target = None
        self._selection_marker_pos = None
        self._map_hint_label.pack_forget()
        self._refresh_ui()

    def _save_edit(self) -> None:
        """Save the edited physical position."""
        if not self._editing_target:
            return

        try:
            parts = self._edit_var.get().split(",")
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            depth = float(parts[2].strip()) if len(parts) > 2 else 0.0

            coord = Coord(lat=lat, lon=lon)
            self.state.set_physical_position(self._editing_target, coord, depth)

            self._log_console(f"Updated physical position for {self._editing_target}")
            self._cancel_edit()

        except (ValueError, IndexError) as e:
            self._log_console(f"Invalid position format: {e}")

    def _push_gps(self, node_id: str) -> None:
        """Push GPS update to a node."""
        pos = self.state.get_physical_position(node_id)
        if pos:
            coord, _ = pos
            self.backend.send_gps_update(node_id, coord)
            self._log_console(f"Pushed GPS to {node_id}: ({coord.lat:.4f}, {coord.lon:.4f})")
        else:
            self._log_console(f"Cannot push GPS to {node_id}: no physical position set")

    def _old_handle_map_right_click(self, coords: tuple[float, float]) -> None:
        """Handle right-click on map to set physical position."""
        lat, lon = coords

        # Ask which node to position
        dialog = tk.Toplevel(self._window)
        dialog.title("Set Physical Position")
        dialog.geometry("300x150")

        ttk.Label(dialog, text=f"Position: {lat:.6f}, {lon:.6f}").pack(pady=10)
        ttk.Label(dialog, text="Select node:").pack()

        node_var = tk.StringVar()
        node_ids = self.state.get_all_node_ids()

        if not node_ids:
            ttk.Label(dialog, text="No nodes registered yet.").pack()
            ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
            return

        combo = ttk.Combobox(dialog, textvariable=node_var, values=node_ids, state="readonly")
        combo.pack(pady=10)
        combo.current(0)

        def set_pos() -> None:
            node_id = node_var.get()
            if node_id:
                coord = Coord(lat=lat, lon=lon)
                self.state.set_physical_position(node_id, coord, depth=0.0)

                self._log_console(f"Set physical position for {node_id}: {lat:.6f}, {lon:.6f}")
                self._refresh_ui()
            dialog.destroy()

        ttk.Button(dialog, text="Set Position", command=set_pos).pack(pady=5)

    def _refresh_ui(self) -> None:
        self._refresh_registry()
        self._refresh_map()

    def _refresh_registry(self) -> None:
        """Refresh the node registry panel."""
        node_ids = self.state.get_all_node_ids()

        # Remove rows for nodes no longer present
        for nid in list(self._registry_rows.keys()):
            if nid not in node_ids:
                self._registry_rows[nid]["frame"].destroy()
                del self._registry_rows[nid]

        # Add or update rows
        for nid in node_ids:
            if nid not in self._registry_rows:
                self._create_registry_row(nid)
            self._update_registry_row(nid)

    def _create_registry_row(self, node_id: str) -> None:
        """Create a new registry row for a node."""
        row = ttk.Frame(self._registry_container)
        row.pack(fill=tk.X, pady=2)

        color = NODE_COLORS[int(node_id) % len(NODE_COLORS)]

        id_label = ttk.Label(row, text=node_id, width=8, foreground=color)
        id_label.pack(side=tk.LEFT, padx=2)

        transport_label = ttk.Label(row, text="—", width=15)
        transport_label.pack(side=tk.LEFT, padx=2)

        # Display sub-frame
        display_f = ttk.Frame(row)
        pos_label = ttk.Label(display_f, text="—", width=25)
        pos_label.pack(side=tk.LEFT, padx=2)

        def make_edit_callback(nid: str) -> Callable[[], None]:
            return lambda: self._start_edit(nid)

        def make_push_gps_callback(nid: str) -> Callable[[], None]:
            return lambda: self._push_gps(nid)

        ttk.Button(display_f, text="Edit", command=make_edit_callback(node_id)).pack(side=tk.LEFT, padx=2)
        ttk.Button(display_f, text="Push GPS", command=make_push_gps_callback(node_id)).pack(side=tk.LEFT, padx=2)

        # Edit sub-frame
        edit_f = ttk.Frame(row)
        ttk.Entry(edit_f, textvariable=self._edit_var, width=30).pack(side=tk.LEFT, padx=2)
        ttk.Button(edit_f, text="Save", command=self._save_edit).pack(side=tk.LEFT, padx=2)
        ttk.Button(edit_f, text="X", command=self._cancel_edit).pack(side=tk.LEFT)

        self._registry_rows[node_id] = {
            "frame": row,
            "id_label": id_label,
            "transport_label": transport_label,
            "display_f": display_f,
            "pos_label": pos_label,
            "edit_f": edit_f,
        }

    def _update_registry_row(self, node_id: str) -> None:
        """Update the display of a registry row."""
        if node_id not in self._registry_rows:
            return

        row = self._registry_rows[node_id]

        # Update transport info
        reader = self.backend.serial_readers.get(node_id)
        if reader is not None:
            transport_text = f"Serial: {reader.pty_path}"
        elif node_id in self.backend.network_acoustic_clients:
            transport_text = "Network: TCP"
        else:
            transport_text = "—"

        transport_label = row["transport_label"]
        if isinstance(transport_label, ttk.Label):
            transport_label.config(text=transport_text)

        # Toggle between display and edit frames
        if self._editing_target == node_id:
            row["display_f"].pack_forget()
            row["edit_f"].pack(side=tk.LEFT, fill=tk.X, expand=True)
        else:
            row["edit_f"].pack_forget()
            row["display_f"].pack(side=tk.LEFT, fill=tk.X, expand=True)

            # Update position info
            pos = self.state.get_physical_position(node_id)
            if pos:
                coord, depth = pos
                pos_text = f"{coord.lat:.6f}, {coord.lon:.6f}, {depth:.1f}m"
            else:
                pos_text = "Not placed"

            pos_label = row["pos_label"]
            if isinstance(pos_label, ttk.Label):
                pos_label.config(text=pos_text)

    def _refresh_map(self) -> None:
        """Refresh map markers."""
        node_ids = self.state.get_all_node_ids()
        current_ids = (
            set(f"physical_{nid}" for nid in node_ids) | set(f"belief_{nid}" for nid in node_ids) | {"selection"}
        )
        stored_ids = set(self._markers.keys())

        # Remove old markers
        for marker_id in stored_ids - current_ids:
            self._delete_marker(marker_id)

        # Update markers
        for nid in node_ids:
            color = NODE_COLORS[int(nid) % len(NODE_COLORS)]

            # Physical position (filled circle)
            phys_pos = self.state.get_physical_position(nid)
            if phys_pos:
                coord, _ = phys_pos
                icon = self._get_circle_icon(color, transparent=False)
                self._update_or_create_marker(
                    f"physical_{nid}",
                    coord.lat,
                    coord.lon,
                    text=f"{nid} (Physical)",
                    icon=icon,
                )
            else:
                self._delete_marker(f"physical_{nid}")

            # Belief position (hollow circle)
            belief_pos = self.state.get_belief_position(nid)
            if belief_pos:
                coord, _ = belief_pos
                icon = self._get_circle_icon(color, transparent=True)
                self._update_or_create_marker(
                    f"belief_{nid}",
                    coord.lat,
                    coord.lon,
                    text=f"{nid} (Belief)",
                    icon=icon,
                )
            else:
                self._delete_marker(f"belief_{nid}")

        # Selection marker (grey circle when editing)
        if self._selection_marker_pos:
            icon = self._get_circle_icon("grey", transparent=True)
            self._update_or_create_marker(
                "selection",
                self._selection_marker_pos[0],
                self._selection_marker_pos[1],
                text="Selection",
                icon=icon,
            )
        else:
            self._delete_marker("selection")

    def _get_circle_icon(self, color: str, transparent: bool) -> ImageTk.PhotoImage:
        """Get or create a cached circle icon."""
        key = f"{color}_{transparent}"
        if key not in self._icon_cache:
            self._icon_cache[key] = _circle_icon(color, transparent)
        return self._icon_cache[key]

    def _update_or_create_marker(
        self,
        key: str,
        lat: float,
        lon: float,
        text: str,
        icon: ImageTk.PhotoImage,
    ) -> None:
        """Update or create a map marker."""
        if key in self._markers:
            marker = self._markers[key]
            marker.set_position(lat, lon)
            marker.set_text(text)
        else:
            marker = self._map.set_marker(lat, lon, text=text, icon=icon)
            self._markers[key] = marker

    def _delete_marker(self, key: str) -> None:
        """Delete a map marker."""
        if key in self._markers:
            marker = self._markers.pop(key)
            try:
                marker.delete()
            except Exception:
                pass


def launch_simulator(
    root: tk.Tk,
    host: str = "127.0.0.1",
    port: int = 5555,
    sound_speed: float = SOUND_SPEED_WATER_M_S,
) -> SimulatorWindow:
    """Launch the God View Simulator with the HybridBackend.

    Args:
        root: Tkinter root window
        host: Host to bind the metadata server to
        port: Port to bind the metadata server to
    """
    state = SimulatorState(sound_speed=validate_sound_speed(sound_speed))
    backend = HybridBackend(state, host=host, port=port)
    return SimulatorWindow(root, state, backend)
