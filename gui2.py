import tkinter as tk
from typing import Callable, Optional

class Modem:
    def __init__(self, id: str, x: int = 100, y: int = 100):
        self.id = id
        self.x = x
        self.y = y
        self.box_id: Optional[int] = None  # Canvas ID for the rectangle
        self.label_id: Optional[int] = None  # Canvas ID for the text label
        self.size = 50  # Size of the rectangle

    def draw(self, canvas) -> None:
        """Draw the modem as a rectangle on the canvas."""
        if self.box_id is not None:
            self._update_position(canvas)
        else:
            self.box_id = canvas.create_rectangle(
                self.x - self.size//2, self.y - self.size//2,
                self.x + self.size//2, self.y + self.size//2,
                fill="lightblue", outline="black", width=2,
                tags="modem"
            )
            # Add ID label
            self.label_id = canvas.create_text(
                self.x, self.y,
                text=self.id, fill="black",
                tags="modem"
            )

    def _update_position(self, canvas) -> None:
        """Update the visual position of the modem on canvas."""
        if self.box_id is None:
            return
        canvas.coords(
            self.box_id,
            self.x - self.size//2, self.y - self.size//2,
            self.x + self.size//2, self.y + self.size//2
        )
        # Update label position
        if self.label_id is not None:
            canvas.coords(self.label_id, self.x, self.y)

    def set_id(self, id: str) -> str:
        self.id = id
        return f"#{id}"

    def command(self, command: str) -> str:
        if command.startswith("$A"):
            resp = self.set_id(command[2:])
            return resp
        return ""


class GUI:
    def __init__(self, on_submit: Callable[[str], None]):
        self.root = tk.Tk()
        self.root.title("GUI")
        self.on_input_submit = on_submit
        
        # Store modems and track dragging
        self.modems: list[Modem] = []
        self.dragged_modem: Optional[Modem] = None
        
        # Left side: canvas (3/4)
        self.canvas = tk.Canvas(self.root, width=800, height=600, bg="white")
        self.canvas.pack(side='left', fill='both', expand=True)
        
        # Bind mouse events for dragging
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        
        # Right side: chat panel (1/4)
        chat_frame = tk.Frame(self.root, width=200)
        chat_frame.pack(side='right', fill='both')
        chat_frame.pack_propagate(False)
        
        # Chat view
        self.chat = tk.Text(chat_frame, state='disabled')
        self.chat.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Input frame
        input_frame = tk.Frame(chat_frame)
        input_frame.pack(fill='x', padx=5, pady=5)
        
        # Input field
        self.entry = tk.Entry(input_frame)
        self.entry.pack(side='left', fill='x', expand=True)
        self.entry.bind('<Return>', self.on_submit)
        
        # Submit button
        submit_btn = tk.Button(input_frame, text="Send", command=self.on_submit)
        submit_btn.pack(side='right', padx=(5, 0))
    
    def add_modem(self, modem: Modem) -> None:
        """Add a modem to the canvas and draw it."""
        self.modems.append(modem)
        modem.draw(self.canvas)
    
    def _find_modem_at(self, x: int, y: int) -> Optional[Modem]:
        """Find the modem at the given canvas coordinates."""
        for modem in self.modems:
            if (modem.x - modem.size//2 <= x <= modem.x + modem.size//2 and
                modem.y - modem.size//2 <= y <= modem.y + modem.size//2):
                return modem
        return None
    
    def _on_canvas_click(self, event) -> None:
        """Handle mouse click on canvas - start dragging if clicking on a modem."""
        self.dragged_modem = self._find_modem_at(event.x, event.y)
    
    def _on_canvas_drag(self, event) -> None:
        """Handle mouse drag - move the modem if one is being dragged."""
        if self.dragged_modem is None:
            return
        self.dragged_modem.x = event.x
        self.dragged_modem.y = event.y
        self.dragged_modem._update_position(self.canvas)
    
    def _on_canvas_release(self, event) -> None:
        """Handle mouse release - stop dragging."""
        self.dragged_modem = None
    
    def on_submit(self, event=None) -> None:
        """Handle input submission."""
        text = self.entry.get()
        if text:
            self.chat.config(state='normal')
            self.chat.insert('end', "> " + text + '\n')

            resp = self.on_input_submit(text)
            if resp:
                self.chat.insert('end', resp + '\n')
    
            self.chat.config(state='disabled')
            self.chat.see('end')
            self.entry.delete(0, 'end')
    
    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    host_modem = Modem("1", x=150, y=200)
    target_modem = Modem("2", x=400, y=200)

    def handle_command(command: str) -> str:
        return host_modem.command(command)

    gui = GUI(on_submit=handle_command)
    gui.add_modem(host_modem)
    gui.add_modem(target_modem)
    gui.run()
