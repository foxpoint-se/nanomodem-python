import serial

# adjust these to match Termite settings
PORT = "COM10"        # e.g. COM3 or "/dev/ttyUSB0"
BAUD = 9600
TIMEOUT = 4          # seconds

ping_cmd = b"$P003"       # ASCII bytes, exactly what you typed in Termite
ack_cmd = b"$M00304bajs"       # ASCII bytes, exactly what you typed in Termite

cmd = ack_cmd

with serial.Serial(PORT, BAUD, timeout=TIMEOUT) as ser:
    # send command
    ser.write(cmd)

    # read response (adjust size/logic if protocol specifies)
    response = ser.read(ser.in_waiting or 1)

    if response:
        print("RX (raw):", response)
        try:
            print("RX (text):", response.decode("ascii", errors="replace"))
        except Exception:
            pass