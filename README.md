# Testing acoustic modems

A collection of scripts and stuff for messing around with our acoustic modems.


## Get started with the exploratory GUI

Set it up:

```bash
cd gui
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

And then:

```bash
# Mock mode (simulation)
# in the root folder
python -m gui
# in the gui folder
python __main__.py

# Real mode (serial port)
# in the root folder
python -m gui --port /dev/ttyUSB0 --baud 9600
# in the root folder
python __main__.py --port /dev/ttyUSB0 --baud 9600
```
