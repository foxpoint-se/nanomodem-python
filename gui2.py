import tkinter as tk
from typing import Callable

class Modem:
    def __init__(self, id: str) -> None:
        self.id = id

    def set_id(self, id: str) -> str:
        self.id = id
        return f"#{id}" 

    def command(self, command: str) -> str:
        if command.startswith("$A"):
            resp = self.set_id(command[2:])
            return resp

class Node:
    def __init__(self, modem: Modem):
        self.modem = modem

    def send_command_to_modem(self, command: str) -> str:
        return self.modem.command(command)


class GUI:
    def __init__(self, on_submit: Callable[[str], None]):
        self.root = tk.Tk()
        self.root.title("GUI")

        self.on_input_submit = on_submit
        
        # Left side: canvas (3/4)
        self.canvas = tk.Canvas(self.root, width=800, height=600, bg="white")
        self.canvas.pack(side='left', fill='both', expand=True)
        
        # Right side: chat panel (1/4)
        chat_frame = tk.Frame(self.root, width=200)
        chat_frame.pack(side='right', fill='both')
        chat_frame.pack_propagate(False)  # Maintain width
        
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
    
    def on_submit(self, event=None):
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
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    host_node = Node(Modem("1"))
    target_node = Node(Modem("2"))

    gui = GUI(on_submit=host_node.send_command_to_modem)
    gui.run()