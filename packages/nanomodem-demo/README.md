# nanomodem-demo

GUI demo applications and scenarios for the nanomodem library.

When installing from GitHub, pip cannot resolve the library from the same repo (unlike `uv sync` in the dev workspace). Install both packages:

```bash
pip install "git+https://github.com/foxpoint-se/nanomodem-python.git#subdirectory=packages/nanomodem"
pip install "git+https://github.com/foxpoint-se/nanomodem-python.git#subdirectory=packages/nanomodem-demo"
```

Console scripts: `nanomodem-demo`, `nanomodem-controller`, `nanomodem-bridge`, `nanomodem-simulator`.
