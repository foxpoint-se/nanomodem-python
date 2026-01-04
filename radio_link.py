import serial
import threading
import time

class RadioLink:
    def __init__(self, port, baud=9600):
        self.ser = serial.Serial(port, baud, timeout=0.1)
        self.running = True

        self.listener = threading.Thread(
            target=self._listen,
            daemon=True
        )
        self.listener.start()

    def _listen(self):
        buffer = b""
        while self.running:
            data = self.ser.read(self.ser.in_waiting or 1)
            if data:
                buffer += data

                # simple framing: print when line seems complete
                if b"#R" in buffer or buffer.endswith(b"\n"):
                    print("\nRX:", buffer.decode(errors="replace"))
                    buffer = b""
            else:
                time.sleep(0.01)

    def send(self, msg):
        if isinstance(msg, str):
            msg = msg.encode("ascii")
        self.ser.write(msg)
        print("TX:", msg)

    def close(self):
        self.running = False
        self.listener.join(timeout=1)
        self.ser.close()