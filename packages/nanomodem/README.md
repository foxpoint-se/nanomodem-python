# nanomodem

Core library for underwater acoustic positioning — wire protocol, transports, and LBL positioning.

Install from git:

```bash
pip install "git+https://github.com/foxpoint-se/nanomodem-python.git#subdirectory=packages/nanomodem"
```

```python
from nanomodem import PositioningNode, BasicPositionCodec
from nanomodem.core.transports import InMemoryBus, InMemoryTransport
```
