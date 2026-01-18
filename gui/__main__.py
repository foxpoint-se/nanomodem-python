import tkinter as tk
from tkinter import ttk
import argparse
import threading
import queue
import math
from typing import Optional, Protocol, Union, TYPE_CHECKING, cast
from trilateration import trilaterate

# Constants for distance calculation
PIXELS_PER_METER = 100  # Scale: 100 pixels = 1 meter
SOUND_SPEED = 1500  # m/s (default: water, can be changed via GUI)

if TYPE_CHECKING:
    import serial

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class SerialInterface(Protocol):
    """Protocol for serial communication interface."""
    def write(self, data: str) -> None: ...
    def read(self) -> Optional[str]: ...


class MockSerialInterface:
    """Mock interface for computer ↔ host modem communication (simulated)."""
    def __init__(self):
        self.outgoing_queue: list[str] = []  # Messages from computer to modem
        self.incoming_queue: list[str] = []   # Messages from modem to computer
    
    def write(self, data: str) -> None:
        """Computer sends data to modem."""
        self.outgoing_queue.append(data)
    
    def read(self) -> Optional[str]:
        """Computer reads data from modem."""
        if self.incoming_queue:
            return self.incoming_queue.pop(0)
        return None
    
    def modem_read(self) -> Optional[str]:
        """Modem reads data from computer."""
        if self.outgoing_queue:
            return self.outgoing_queue.pop(0)
        return None
    
    def modem_write(self, data: str) -> None:
        """Modem sends data to computer."""
        self.incoming_queue.append(data)


class RealSerialInterface:
    """Real serial interface using pyserial."""
    def __init__(self, port: str, baud: int = 9600) -> None:
        if not SERIAL_AVAILABLE:
            raise ImportError("pyserial not installed. Install with: pip install pyserial")
        
        self.ser: 'serial.Serial' = serial.Serial(port, baud, timeout=0.1)
        self.message_queue: queue.Queue[str] = queue.Queue()
        self.running: bool = True
        
        # Start background thread to read from serial using blocking reads
        self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.reader_thread.start()
    
    def _read_loop(self) -> None:
        """Background thread that blocks on readline() until data arrives."""
        while self.running:
            try:
                # Blocking read - OS wakes thread when data arrives
                line = self.ser.readline()
                if line:
                    decoded = line.decode('ascii', errors='replace').strip()
                    if decoded:
                        self.message_queue.put(decoded)
            except Exception:
                # Handle serial errors gracefully
                if self.running:
                    continue
                break
    
    def write(self, data: str) -> None:
        """Computer sends data to modem."""
        self.ser.write(data.encode('ascii'))
    
    def read(self) -> Optional[str]:
        """Computer reads data from modem (non-blocking, from queue)."""
        try:
            return self.message_queue.get_nowait()
        except queue.Empty:
            return None
    
    def close(self) -> None:
        """Close the serial connection."""
        self.running = False
        if hasattr(self, 'ser'):
            self.ser.close()


class AcousticBus:
    """Bus for modem ↔ modem acoustic communication."""
    def __init__(self):
        self.modems: dict[str, 'Modem'] = {}  # ID -> Modem mapping
    
    def register(self, modem: 'Modem') -> None:
        """Register a modem with the bus."""
        self.modems[modem.id] = modem
    
    def send(self, message: str, from_modem: 'Modem') -> Optional[str]:
        """Send message from one modem to another, return response."""
        # Parse target ID from command
        target_id = self._extract_target_id(message)
        if target_id is None:
            return None
        
        # Find target modem (try exact match, then try without leading zeros)
        target_modem = self.modems.get(target_id)
        if target_modem is None:
            # Try without leading zeros
            target_id_stripped = target_id.lstrip('0') or '0'
            target_modem = self.modems.get(target_id_stripped)
        
        if target_modem is None:
            return None
        
        # Deliver message to target modem and get response
        return target_modem.handle_acoustic_message(message, from_modem)
    
    def _extract_target_id(self, message: str) -> Optional[str]:
        """Extract target modem ID from command string."""
        # $P123 -> "123"
        # $P002 -> "002"
        # $M123 -> "123"
        if len(message) >= 5 and message[0] == '$':
            # Commands like $P, $M, $U, $V, $T, $E
            if message[1] in 'PMUVTE':
                # Extract ID (3 digits after command prefix)
                return message[2:5]
        return None


class Modem:
    def __init__(self, id: str, acoustic_bus: AcousticBus, 
                 serial_interface: Optional[Union[MockSerialInterface, 'RealSerialInterface']] = None,
                 x: int = 100, y: int = 100, track_position: bool = False) -> None:
        self.id = id
        self.acoustic_bus = acoustic_bus
        self.serial_interface = serial_interface
        self.x = x
        self.y = y
        self.track_position = track_position
        self.box_id: Optional[int] = None  # Canvas ID for the rectangle
        self.label_id: Optional[int] = None  # Canvas ID for the text label
        self.canvas: Optional[tk.Canvas] = None  # Reference to canvas for updates
        self.viz_canvas: Optional[tk.Canvas] = None  # Reference to visualization canvas
        self.viz_circle_id: Optional[int] = None  # Canvas ID for visualization circle
        self.viz_canvas_height: Optional[int] = None  # For coordinate conversion
        self.size = 50  # Size of the rectangle
        self.viz_size = 8  # Size of circle in visualization (radius)
        
        # Register with acoustic bus
        acoustic_bus.register(self)

    def init_on_canvas(self, canvas: tk.Canvas, canvas_height: Optional[int] = None) -> None:
        """Initialize the modem's visual representation on the canvas."""
        self.canvas = canvas  # Store canvas reference
        self.canvas_height = canvas_height  # Store for y-coordinate flipping
        if self.box_id is not None:
            self._update_position(canvas)
        else:
            # Convert logical y (0 at bottom) to canvas y (0 at top)
            canvas_y = self._to_canvas_y(self.y)
            self.box_id = canvas.create_rectangle(
                self.x - self.size//2, canvas_y - self.size//2,
                self.x + self.size//2, canvas_y + self.size//2,
                fill="lightblue", outline="black", width=2,
                tags="modem"
            )
            # Add ID label
            self.label_id = canvas.create_text(
                self.x, canvas_y,
                text=self.id, fill="black",
                tags="modem"
            )

    def _to_canvas_y(self, logical_y: int, use_viz: bool = False) -> int:
        """Convert logical y coordinate (0 at bottom) to canvas y (0 at top)."""
        canvas_height = self.viz_canvas_height if use_viz else self.canvas_height
        if canvas_height is None:
            return logical_y
        return canvas_height - logical_y

    def _update_position(self, canvas: tk.Canvas) -> None:
        """Update the visual position of the modem on canvas."""
        if self.box_id is None:
            return
        # Convert logical y (0 at bottom) to canvas y (0 at top)
        canvas_y = self._to_canvas_y(self.y)
        canvas.coords(
            self.box_id,
            self.x - self.size//2, canvas_y - self.size//2,
            self.x + self.size//2, canvas_y + self.size//2
        )
        # Update label position
        if self.label_id is not None:
            canvas.coords(self.label_id, self.x, canvas_y)

    def update_label(self) -> None:
        """Update the label text to reflect current ID."""
        if self.label_id is not None and self.canvas is not None:
            self.canvas.itemconfig(self.label_id, text=self.id)

    def init_on_viz_canvas(self, viz_canvas: tk.Canvas, canvas_height: int) -> None:
        """Initialize the modem's visualization circle on the visualization canvas."""
        if not self.track_position:
            return
        
        self.viz_canvas = viz_canvas
        self.viz_canvas_height = canvas_height
        
        # Convert logical y (0 at bottom) to canvas y (0 at top)
        canvas_y = self._to_canvas_y(self.y, use_viz=True)
        
        # Draw small circle
        self.viz_circle_id = viz_canvas.create_oval(
            self.x - self.viz_size, canvas_y - self.viz_size,
            self.x + self.viz_size, canvas_y + self.viz_size,
            fill="blue", outline="darkblue", width=1,
            tags="viz_modem"
        )

    def _update_viz_position(self) -> None:
        """Update the visualization circle position."""
        if not self.track_position or self.viz_circle_id is None or self.viz_canvas is None:
            return
        
        # Convert logical y (0 at bottom) to canvas y (0 at top)
        canvas_y = self._to_canvas_y(self.y, use_viz=True)
        
        # Update circle position
        self.viz_canvas.coords(
            self.viz_circle_id,
            self.x - self.viz_size, canvas_y - self.viz_size,
            self.x + self.viz_size, canvas_y + self.viz_size
        )

    def set_id(self, id: str) -> str:
        self.id = id
        self.update_label()
        return f"#{id}"

    def process_serial_command(self, command: str) -> Optional[str]:
        """Process command received from serial interface."""
        if not self.serial_interface or not isinstance(self.serial_interface, MockSerialInterface):
            return None
        
        # Echo command back immediately
        self.serial_interface.modem_write(command)
        
        # Handle local commands
        if command.startswith("$A"):
            resp = self.set_id(command[2:])
            self.serial_interface.modem_write(resp)
            return resp
        
        # Handle acoustic commands (ping)
        if command.startswith("$P"):
            response = self.acoustic_bus.send(command, self)
            if response:
                self.serial_interface.modem_write(response)
                return response
            else:
                # Timeout case - would send #TO after 4 seconds
                # For now, just return None
                return None
        
        return None

    def _respond_to_ping(self, from_modem: 'Modem') -> str:
        """Respond to ping with timestamp calculated from distance."""
        # Calculate distance in pixels
        dx = from_modem.x - self.x
        dy = from_modem.y - self.y
        distance_pixels = math.sqrt(dx * dx + dy * dy)
        
        # Convert to meters
        distance_meters = distance_pixels / PIXELS_PER_METER
        
        # Calculate timestamp using spec formula: R = yyyyy * c * 3.125e-5
        # Solving for yyyyy: yyyyy = R / (c * 3.125e-5)
        timestamp = int(round(distance_meters / (SOUND_SPEED * 3.125e-5)))
        timestamp_str = f"{timestamp:05d}"
        
        # Format ID as 3 digits
        formatted_id = self.id.zfill(3) if len(self.id) < 3 else self.id[:3]
        response = f"#R{formatted_id}T{timestamp_str}"
        return response

    def handle_acoustic_message(self, message: str, from_modem: 'Modem') -> Optional[str]:
        """Handle message received via acoustic bus."""
        # Handle ping command
        if message.startswith("$P"):
            return self._respond_to_ping(from_modem)
        return None
    
    @staticmethod
    def parse_ping_response(response: str) -> Optional[tuple[str, float]]:
        """Parse ping response #RxxxTyyyyy and return (target_id, distance_meters)."""
        # Format: #RxxxTyyyyy
        if not response.startswith("#R") or "T" not in response:
            return None
        
        try:
            # Extract parts: #RxxxTyyyyy
            parts = response[2:].split("T")
            if len(parts) != 2:
                return None
            
            target_id = parts[0]
            timestamp_str = parts[1]
            
            if len(timestamp_str) != 5:
                return None
            
            # Parse timestamp
            timestamp = int(timestamp_str)
            
            # Calculate distance using spec formula: R = yyyyy * c * 3.125e-5
            distance_meters = timestamp * SOUND_SPEED * 3.125e-5
            
            return (target_id, distance_meters)
        except (ValueError, IndexError):
            return None

    def command(self, command: str) -> str:
        """Legacy method - redirects to process_serial_command."""
        result = self.process_serial_command(command)
        return result if result else ""


class GUI:
    def __init__(self, serial_interface: Union[MockSerialInterface, RealSerialInterface], 
                 host_modem: Optional[Modem] = None) -> None:
        self.root = tk.Tk()
        self.root.title("Acoustic Modem GUI")
        self.serial_interface = serial_interface
        self.host_modem = host_modem
        self.is_mock_mode = host_modem is not None
        
        # Store modems and track dragging (for simulation window)
        self.modems: list[Modem] = []
        self.dragged_modem: Optional[Modem] = None
        self.canvas: Optional[tk.Canvas] = None  # Canvas in simulation window
        self.viz_canvas: Optional[tk.Canvas] = None  # Canvas in visualization area
        
        # Track distance circles per target modem (target_id -> circle_id)
        self.distance_circles: dict[str, int] = {}
        
        # Track distance measurements for trilateration (target_id -> distance_meters)
        self.distance_measurements: dict[str, float] = {}
        
        # Track estimated position dot (red dot showing trilateration result)
        self.estimated_position_dot: Optional[int] = None
        
        # Message history for arrow key navigation
        self.message_history: list[str] = []
        self.history_index: int = -1  # -1 means at end (no history selected)
        
        # Poll for serial responses
        self._poll_serial()
        
        # Main window layout: Visualization (left) + Terminal (right)
        # Left side: Visualization area with canvas
        viz_frame = tk.Frame(self.root, width=1000, height=600)
        viz_frame.pack(side='left', fill='both', expand=True)
        viz_frame.pack_propagate(False)
        
        # Visualization canvas (same size as simulation window)
        self.viz_canvas = tk.Canvas(viz_frame, width=1000, height=600, bg="white")
        self.viz_canvas.pack(fill='both', expand=True)
        
        # Store visualization canvas dimensions for coordinate conversion
        self.viz_canvas_width = 1000
        self.viz_canvas_height = 600
        
        # Draw scales on visualization canvas
        self._draw_viz_scale()
        
        # Right side: Terminal/Chat panel
        chat_frame = tk.Frame(self.root, width=400, height=600)
        chat_frame.pack(side='right', fill='both')
        chat_frame.pack_propagate(False)
        
        # Chat view
        self.chat = tk.Text(chat_frame, state='disabled')
        self.chat.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Sound speed selector
        speed_frame = tk.Frame(chat_frame)
        speed_frame.pack(fill='x', padx=5, pady=(5, 0))
        tk.Label(speed_frame, text="Sound speed:").pack(side='left', padx=(0, 5))
        self.speed_var = tk.StringVar(value="1500 m/s (water)")
        speed_combo = ttk.Combobox(speed_frame, textvariable=self.speed_var, 
                                   values=["1500 m/s (water)", "340 m/s (air)"],
                                   state="readonly", width=18)
        speed_combo.pack(side='left')
        speed_combo.bind("<<ComboboxSelected>>", self._on_speed_change)
        
        # Input frame
        input_frame = tk.Frame(chat_frame)
        input_frame.pack(fill='x', padx=5, pady=5)
        
        # Input field
        self.entry = tk.Entry(input_frame)
        self.entry.pack(side='left', fill='x', expand=True)
        self.entry.bind('<Return>', self.on_submit)
        self.entry.bind('<Up>', self._on_arrow_up)
        self.entry.bind('<Down>', self._on_arrow_down)
        
        # Submit button
        submit_btn = tk.Button(input_frame, text="Send", command=self.on_submit)
        submit_btn.pack(side='right', padx=(5, 0))
        
        # Create simulation window (only in mock mode)
        if self.is_mock_mode:
            self._create_simulation_window()
    
    def _create_simulation_window(self) -> None:
        """Create the simulation window with canvas for mock mode."""
        self.sim_window = tk.Toplevel(self.root)
        self.sim_window.title("Simulation - Modem Positions")
        self.sim_window.geometry("1000x600")
        
        # Canvas for simulation
        self.canvas = tk.Canvas(self.sim_window, width=1000, height=600, bg="white")
        self.canvas.pack(fill='both', expand=True)
        
        # Store canvas dimensions for coordinate conversion
        self.canvas_width = 1000
        self.canvas_height = 600
        
        # Draw scale/ruler
        self._draw_scale()
        
        # Bind mouse events for dragging
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
    
    def _flip_y(self, y: int) -> int:
        """Convert y coordinate from logical (0 at bottom) to canvas (0 at top)."""
        return self.canvas_height - y
    
    def _unflip_y(self, canvas_y: int) -> int:
        """Convert y coordinate from canvas (0 at top) to logical (0 at bottom)."""
        return self.canvas_height - canvas_y
    
    def add_modem(self, modem: Modem) -> None:
        """Add a modem to the canvas and initialize its visual representation."""
        if not self.is_mock_mode or not self.canvas:
            return
        self.modems.append(modem)
        # Modem y coordinates are in logical system (0 at bottom)
        modem.init_on_canvas(self.canvas, self.canvas_height)
        
        # Initialize visualization if modem tracks position
        if modem.track_position and self.viz_canvas:
            modem.init_on_viz_canvas(self.viz_canvas, self.viz_canvas_height)
    
    def _draw_scale(self) -> None:
        """Draw scale/ruler on simulation canvas showing meters (y-axis flipped: zero at bottom)."""
        if not self.canvas:
            return
        
        canvas_width = self.canvas_width
        canvas_height = self.canvas_height
        
        # Scale parameters
        tick_length = 10
        label_offset = 15
        
        # Draw X-axis scale (bottom) - same scale as Y
        max_meters_x = int(canvas_width / PIXELS_PER_METER) + 1
        for meter in range(0, max_meters_x):
            x = meter * PIXELS_PER_METER
            if x <= canvas_width:
                # Draw tick mark
                self.canvas.create_line(x, canvas_height, x, canvas_height - tick_length, 
                                       fill="gray", width=1, tags="scale")
                # Draw label
                self.canvas.create_text(x, canvas_height - tick_length - label_offset, 
                                       text=f"{meter}m", fill="gray", tags="scale")
        
        # Draw Y-axis scale (left) - flipped: zero at bottom, increasing upward
        max_meters_y = int(canvas_height / PIXELS_PER_METER) + 1
        for meter in range(0, max_meters_y):
            # Flip y coordinate: zero at bottom
            y_canvas = canvas_height - (meter * PIXELS_PER_METER)
            if y_canvas >= 0:
                # Draw tick mark
                self.canvas.create_line(0, y_canvas, tick_length, y_canvas, 
                                       fill="gray", width=1, tags="scale")
                # Draw label
                self.canvas.create_text(tick_length + label_offset, y_canvas, 
                                       text=f"{meter}m", fill="gray", tags="scale")
    
    def _draw_viz_scale(self) -> None:
        """Draw scale/ruler on visualization canvas showing meters (y-axis flipped: zero at bottom)."""
        if not self.viz_canvas:
            return
        
        canvas_width = self.viz_canvas_width
        canvas_height = self.viz_canvas_height
        
        # Scale parameters
        tick_length = 10
        label_offset = 15
        
        # Draw X-axis scale (bottom) - same scale as Y
        max_meters_x = int(canvas_width / PIXELS_PER_METER) + 1
        for meter in range(0, max_meters_x):
            x = meter * PIXELS_PER_METER
            if x <= canvas_width:
                # Draw tick mark
                self.viz_canvas.create_line(x, canvas_height, x, canvas_height - tick_length, 
                                           fill="gray", width=1, tags="viz_scale")
                # Draw label
                self.viz_canvas.create_text(x, canvas_height - tick_length - label_offset, 
                                           text=f"{meter}m", fill="gray", tags="viz_scale")
        
        # Draw Y-axis scale (left) - flipped: zero at bottom, increasing upward
        max_meters_y = int(canvas_height / PIXELS_PER_METER) + 1
        for meter in range(0, max_meters_y):
            # Flip y coordinate: zero at bottom
            y_canvas = canvas_height - (meter * PIXELS_PER_METER)
            if y_canvas >= 0:
                # Draw tick mark
                self.viz_canvas.create_line(0, y_canvas, tick_length, y_canvas, 
                                           fill="gray", width=1, tags="viz_scale")
                # Draw label
                self.viz_canvas.create_text(tick_length + label_offset, y_canvas, 
                                           text=f"{meter}m", fill="gray", tags="viz_scale")
    
    def _find_modem_by_id(self, target_id: str) -> Optional[Modem]:
        """Find a modem by its ID (handles 3-digit format with leading zeros)."""
        # Try exact match first
        for modem in self.modems:
            # Format modem ID as 3 digits for comparison
            formatted_id = modem.id.zfill(3) if len(modem.id) < 3 else modem.id[:3]
            if formatted_id == target_id:
                return modem
            # Also try without leading zeros
            if modem.id.lstrip('0') == target_id.lstrip('0'):
                return modem
        return None
    
    def _handle_distance_measurement(self, target_id: str, distance_meters: float) -> None:
        """Handle a new distance measurement by drawing/updating circle in visualization."""
        if not self.viz_canvas:
            return
        
        # Find target modem
        target_modem = self._find_modem_by_id(target_id)
        if not target_modem or not target_modem.track_position:
            return  # Can't visualize if target not tracked
        
        # Store distance measurement for trilateration
        self.distance_measurements[target_id] = distance_meters
        
        # Clear old circle for this target if it exists
        if target_id in self.distance_circles:
            old_circle_id = self.distance_circles[target_id]
            self.viz_canvas.delete(old_circle_id)
        
        # Draw new circle
        self._draw_distance_circle(target_modem, distance_meters, target_id)
        
        # Check if we have enough measurements for trilateration
        self._check_and_perform_trilateration()
    
    def _draw_distance_circle(self, target_modem: Modem, distance_meters: float, target_id: str) -> None:
        """Draw a circle around target modem representing the measured distance."""
        if not self.viz_canvas:
            return
        
        # Convert distance to pixels
        radius_pixels = distance_meters * PIXELS_PER_METER
        
        # Get target position (logical coordinates: 0 at bottom)
        center_x = target_modem.x
        center_y_logical = target_modem.y
        
        # Convert to canvas coordinates (flip y-axis)
        center_y_canvas = self.viz_canvas_height - center_y_logical
        
        # Draw circle (outline only, grey)
        circle_id = self.viz_canvas.create_oval(
            center_x - radius_pixels, center_y_canvas - radius_pixels,
            center_x + radius_pixels, center_y_canvas + radius_pixels,
            outline="gray", width=2, tags="distance_circle"
        )
        
        # Store circle ID for this target
        self.distance_circles[target_id] = circle_id
    
    def _check_and_perform_trilateration(self) -> None:
        """Check if we have 3+ distance measurements and perform trilateration."""
        if len(self.distance_measurements) < 3:
            return
        
        # Get beacon positions and distances
        beacon_positions: list[tuple[float, float]] = []
        distances: list[float] = []
        
        for target_id, distance in self.distance_measurements.items():
            target_modem = self._find_modem_by_id(target_id)
            if target_modem and target_modem.track_position:
                # Convert pixel coordinates to meters
                beacon_x_meters = target_modem.x / PIXELS_PER_METER
                beacon_y_meters = target_modem.y / PIXELS_PER_METER
                beacon_positions.append((beacon_x_meters, beacon_y_meters))
                distances.append(distance)
        
        if len(beacon_positions) < 3:
            return
        
        try:
            # Perform trilateration
            estimated_pos = trilaterate(beacon_positions, distances)
            est_x, est_y = estimated_pos
            
            # Print result to chat
            self.chat.config(state='normal')
            self.chat.insert('end', f"Trilateration: Estimated host position at ({est_x:.2f}, {est_y:.2f}) meters\n")
            self.chat.config(state='disabled')
            self.chat.see('end')
            
            # Draw/update red dot for estimated position
            self._draw_estimated_position(est_x, est_y)
        except Exception as e:
            # Print error if trilateration fails
            self.chat.config(state='normal')
            self.chat.insert('end', f"Trilateration error: {e}\n")
            self.chat.config(state='disabled')
            self.chat.see('end')
    
    def _draw_estimated_position(self, x_meters: float, y_meters: float) -> None:
        """Draw or update red dot showing estimated host position from trilateration."""
        if not self.viz_canvas:
            return
        
        # Convert meters to pixels
        x_pixels = x_meters * PIXELS_PER_METER
        y_pixels_logical = y_meters * PIXELS_PER_METER
        
        # Convert to canvas coordinates (flip y-axis)
        y_pixels_canvas = self.viz_canvas_height - y_pixels_logical
        
        # Size same as beacon dots
        dot_size = 8
        
        # Delete old dot if it exists
        if self.estimated_position_dot is not None:
            self.viz_canvas.delete(self.estimated_position_dot)
        
        # Draw red dot
        self.estimated_position_dot = self.viz_canvas.create_oval(
            x_pixels - dot_size, y_pixels_canvas - dot_size,
            x_pixels + dot_size, y_pixels_canvas + dot_size,
            fill="red", outline="darkred", width=1,
            tags="estimated_position"
        )
    
    def _find_modem_at(self, canvas_x: int, canvas_y: int) -> Optional[Modem]:
        """Find the modem at the given canvas coordinates."""
        # Convert canvas y to logical y for comparison
        logical_y = self._unflip_y(canvas_y)
        for modem in self.modems:
            # Modem stores logical y, so compare with converted y
            if (modem.x - modem.size//2 <= canvas_x <= modem.x + modem.size//2 and
                modem.y - modem.size//2 <= logical_y <= modem.y + modem.size//2):
                return modem
        return None
    
    def _on_canvas_click(self, event) -> None:
        """Handle mouse click on canvas - start dragging if clicking on a modem."""
        self.dragged_modem = self._find_modem_at(event.x, event.y)
    
    def _on_canvas_drag(self, event) -> None:
        """Handle mouse drag - move the modem if one is being dragged."""
        if self.dragged_modem is None:
            return
        # Convert canvas coordinates to logical coordinates
        self.dragged_modem.x = event.x
        self.dragged_modem.y = self._unflip_y(event.y)
        self.dragged_modem._update_position(self.canvas)
        
        # Update visualization position if modem tracks position
        if self.dragged_modem.track_position:
            self.dragged_modem._update_viz_position()
    
    def _on_canvas_release(self, event) -> None:
        """Handle mouse release - stop dragging."""
        self.dragged_modem = None
    
    def _on_speed_change(self, event=None) -> None:
        """Handle sound speed selection change."""
        global SOUND_SPEED
        selection = self.speed_var.get()
        if "1500" in selection:
            SOUND_SPEED = 1500
        elif "340" in selection:
            SOUND_SPEED = 340
    
    def _on_arrow_up(self, event) -> None:
        """Navigate backward through message history."""
        if not self.message_history:
            return
        
        # If at end, save current text (if any)
        if self.history_index == -1:
            current_text = self.entry.get()
            if current_text:
                # Don't save if it's the same as last message
                if not self.message_history or current_text != self.message_history[-1]:
                    self.message_history.append(current_text)
        
        # Move backward in history
        if self.history_index > 0:
            self.history_index -= 1
        elif self.history_index == -1:
            self.history_index = len(self.message_history) - 1
        
        # Display the message
        if 0 <= self.history_index < len(self.message_history):
            self.entry.delete(0, 'end')
            self.entry.insert(0, self.message_history[self.history_index])
        
        return "break"  # Prevent default behavior
    
    def _on_arrow_down(self, event) -> None:
        """Navigate forward through message history."""
        if not self.message_history or self.history_index == -1:
            return
        
        # Move forward in history
        self.history_index += 1
        
        # If at end, clear the field
        if self.history_index >= len(self.message_history):
            self.history_index = -1
            self.entry.delete(0, 'end')
        else:
            # Display the message
            self.entry.delete(0, 'end')
            self.entry.insert(0, self.message_history[self.history_index])
        
        return "break"  # Prevent default behavior
    
    def _poll_serial(self) -> None:
        """Poll serial interface for incoming messages from modem."""
        if self.is_mock_mode:
            # Mock mode: process commands through host modem
            if isinstance(self.serial_interface, MockSerialInterface):
                command = self.serial_interface.modem_read()
                if command and self.host_modem:
                    self.host_modem.process_serial_command(command)
        
        # Check for responses from modem to computer (works in both modes)
        response = self.serial_interface.read()
        if response:
            self.chat.config(state='normal')
            self.chat.insert('end', response + '\n')
            
            # Check if it's a ping response and display distance
            ping_info = Modem.parse_ping_response(response)
            if ping_info:
                target_id, distance_meters = ping_info
                # Remove leading zeros from target_id for display
                display_id = target_id.lstrip('0') or '0'
                distance_str = f"Host is {distance_meters:.2f} meters from unit {display_id}\n"
                self.chat.insert('end', distance_str)
                
                # Visualize distance measurement
                self._handle_distance_measurement(target_id, distance_meters)
            
            self.chat.config(state='disabled')
            self.chat.see('end')
        
        # Schedule next poll
        self.root.after(50, self._poll_serial)
    
    def on_submit(self, event=None) -> None:
        """Handle input submission."""
        text = self.entry.get()
        if text:
            self.chat.config(state='normal')
            self.chat.insert('end', "> " + text + '\n')
            self.chat.config(state='disabled')
            self.chat.see('end')
            
            # Add to history (avoid duplicates if same as last message)
            if not self.message_history or text != self.message_history[-1]:
                self.message_history.append(text)
            self.history_index = -1  # Reset to end of history
            
            # Send command to modem via serial interface
            self.serial_interface.write(text)
            
            self.entry.delete(0, 'end')
    
    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Acoustic Modem GUI")
    parser.add_argument("--port", type=str, default="mock",
                        help="Serial port (e.g., COM3, /dev/ttyUSB0) or 'mock' for simulation")
    parser.add_argument("--baud", type=int, default=9600,
                        help="Baud rate for serial communication (default: 9600)")
    
    args = parser.parse_args()
    # Type the args namespace for proper type checking
    port: str = args.port
    baud: int = args.baud
    
    if port.lower() == "mock":
        # Mock mode: simulated modems with acoustic bus
        acoustic_bus = AcousticBus()
        serial_interface = MockSerialInterface()
        
        # Create modems (y coordinates in logical system: 0 at bottom)
        # Canvas is 600px high, so y=400 means 400px from bottom (4 meters)
        host_modem = Modem("host", acoustic_bus, serial_interface, x=150, y=400, track_position=False)
        beacon_modem_1 = Modem("002", acoustic_bus, x=400, y=400, track_position=True)
        beacon_modem_2 = Modem("003", acoustic_bus, x=600, y=200, track_position=True)
        beacon_modem_3 = Modem("004", acoustic_bus, x=800, y=500, track_position=True)
        
        # Create GUI with modems
        gui = GUI(serial_interface, host_modem)
        gui.add_modem(host_modem)
        gui.add_modem(beacon_modem_1)
        gui.add_modem(beacon_modem_2)
        gui.add_modem(beacon_modem_3)
    else:
        # Real mode: actual serial communication
        try:
            serial_interface = RealSerialInterface(port, baud)
            print(f"Connected to {port} at {baud} baud")
        except Exception as e:
            print(f"Error opening serial port: {e}")
            exit(1)
        
        # Create GUI without modems (direct serial communication)
        gui = GUI(serial_interface, host_modem=None)
    
    try:
        gui.run()
    except KeyboardInterrupt:
        pass
    finally:
        if hasattr(serial_interface, 'close'):
            serial_interface.close()
