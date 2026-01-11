import tkinter as tk

class BoxGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Click to Move Box")
        self.canvas = tk.Canvas(self.root, width=600, height=400, bg="white")
        self.canvas.pack()
        
        # Initial box position
        self.x = 50
        self.y = 200
        self.box_size = 30
        
        # Draw the box
        self.box = self.canvas.create_rectangle(
            self.x, self.y - self.box_size//2,
            self.x + self.box_size, self.y + self.box_size//2,
            fill="blue", outline="black", width=2
        )
        
        # Bind click event to canvas
        self.canvas.bind("<Button-1>", self.on_click)
        
    def on_click(self, event):
        """Move box right by a few pixels when clicked"""
        pixels = 10  # Move 10 pixels to the right
        self.x += pixels
        
        # Update box position
        self.canvas.coords(
            self.box,
            self.x, self.y - self.box_size//2,
            self.x + self.box_size, self.y + self.box_size//2
        )
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    gui = BoxGUI()
    gui2 = BoxGUI()
    gui.run()
    gui2.run()
