# CHANGELOG

<!-- version list -->

## Unreleased

### Breaking

- Split monolithic package into uv workspace: `packages/nanomodem` (library) and `packages/nanomodem-demo` (GUI apps).
- Removed `nanomodem.demo` import path; use `nanomodem_demo` and install `nanomodem-demo` separately.
- Deprecated `[demo]` extra on the library; install `nanomodem-demo` from git `#subdirectory=packages/nanomodem-demo` instead.
- Removed root package re-exports; import from submodules (e.g., `from nanomodem.node import AcousticNode`).

## v1.2.0 (2026-06-13)

### Bug Fixes

- Address Copilot review on mock sync, UI races, and ack parsing
  ([`ab7f3a3`](https://github.com/foxpoint-se/nanomodem-python/commit/ab7f3a348e12b8a6aa02561a1f8fc8be826b6dbb))

- Address Copilot review on shutdown and relay parsing
  ([`06ef155`](https://github.com/foxpoint-se/nanomodem-python/commit/06ef155af09d70c87f072773badeb4524f6a50ba))

- Address Copilot review on simulator startup and metadata client
  ([`b916cd5`](https://github.com/foxpoint-se/nanomodem-python/commit/b916cd58f95fc4ca6d3d836b47f4b53cf851017d))

- Address second Copilot review batch on bridge and tests
  ([`4b1f230`](https://github.com/foxpoint-se/nanomodem-python/commit/4b1f230af3d656ac4c54c176da34ed2ebb6d1a26))

- Serial god-view scenario startup and simulator UI threading
  ([`ab920d2`](https://github.com/foxpoint-se/nanomodem-python/commit/ab920d2fbd4bcfc837d0756219db8a2ae1c453d7))

- Stop transports when controller window closes
  ([`1c9dace`](https://github.com/foxpoint-se/nanomodem-python/commit/1c9dace9a1fc2a1eb74905b0d7c12d72ae8f8cce))

- Track belief on outbound broadcasts and lock broker port writes
  ([`696b071`](https://github.com/foxpoint-se/nanomodem-python/commit/696b071b88df19cd1d06133c1b57ca9b448b055e))

### Chores

- Tidy plans and document god-view serial scenario
  ([`36644cb`](https://github.com/foxpoint-se/nanomodem-python/commit/36644cb095d38192b0816abdb5af5ebe24b1722e))

### Features

- God view simulator with unified metadata channel
  ([`4884983`](https://github.com/foxpoint-se/nanomodem-python/commit/48849836766b340f1417b9ba5071fe68441cd715))

- Relay test/quality simulation and parse v3 test broadcasts
  ([`1f4f047`](https://github.com/foxpoint-se/nanomodem-python/commit/1f4f04735ab1fcc276eafbf9230f244f0238827d))

- Transport-agnostic controller and serial logging
  ([`d9395d1`](https://github.com/foxpoint-se/nanomodem-python/commit/d9395d1d05ad10ef571fde8e7131e9a4b0b9753e))

- V3 modem status, test, and quality commands end-to-end
  ([`2c70882`](https://github.com/foxpoint-se/nanomodem-python/commit/2c70882822c7673f8f1d48a16f1563b5d3b41aa1))

### Testing

- Poll for network transport events instead of fixed sleep
  ([`670253d`](https://github.com/foxpoint-se/nanomodem-python/commit/670253d55fe702ba4ff2b3ce4632345cb69e9ce0))


## v1.1.0 (2026-03-28)

### Bug Fixes

- Correctly simulate modem broadcast relay per user guide spec
  ([`b8f30e9`](https://github.com/foxpoint-se/nanomodem-python/commit/b8f30e9857a832d81d5b7ed05e4e28ba04b363f5))

- Initiate bridge scenario nodes with no start position
  ([`7214678`](https://github.com/foxpoint-se/nanomodem-python/commit/7214678ebecc3947fb25f43ab1cdda67f90b7814))

### Chores

- Make lock file version stay in sync with toml version automatically
  ([`d8ab6dd`](https://github.com/foxpoint-se/nanomodem-python/commit/d8ab6dd74e81ecbc8a10f571641f2e333afc3914))

- Sync version in lock file with toml
  ([`a8a0b11`](https://github.com/foxpoint-se/nanomodem-python/commit/a8a0b11204bcc9fecedeaace1e6e18062ad52791))

- Use correct make target in ci
  ([`cf8444b`](https://github.com/foxpoint-se/nanomodem-python/commit/cf8444b09a54be0ff50efbb6c1a5f39fe256340b))

### Documentation

- Add plan for creating an integration test suite, without hardware
  ([`ec50240`](https://github.com/foxpoint-se/nanomodem-python/commit/ec50240196eb24d1dc088108ef6961c4b3f2da41))

- Add some complementary things to plan
  ([`ba4dc01`](https://github.com/foxpoint-se/nanomodem-python/commit/ba4dc01a0422c90c54563b18d4b2f02c04da2972))

- Add todos
  ([`8aec664`](https://github.com/foxpoint-se/nanomodem-python/commit/8aec664516b963e1f64acc251222691c8f5d1e59))

- Add todos
  ([`443da18`](https://github.com/foxpoint-se/nanomodem-python/commit/443da183e994a56a16dc5ed77822eb7b37cdee3a))

- Better description of what this is
  ([`bbe7b0d`](https://github.com/foxpoint-se/nanomodem-python/commit/bbe7b0df0d48561d564a61ec0e0e874c81dd6f27))

- Everything in "generalise plan" is complete
  ([`70450cd`](https://github.com/foxpoint-se/nanomodem-python/commit/70450cd96de546b5e1449810f0096a7bcfae7c75))

- Everything in plan is complete
  ([`56a864f`](https://github.com/foxpoint-se/nanomodem-python/commit/56a864feddfd34338c608ed4948f09d419b15bbf))

- Mark todos as done
  ([`03461e1`](https://github.com/foxpoint-se/nanomodem-python/commit/03461e18fbd1a77667594508769044a46a7a1e0b))

- Mark todos as done
  ([`9a4d3d7`](https://github.com/foxpoint-se/nanomodem-python/commit/9a4d3d7f9649280b56d27a4afe5524a2e890f4a9))

- Mark todos as done
  ([`1caf750`](https://github.com/foxpoint-se/nanomodem-python/commit/1caf7502f170d13089a5506faf298814f7a68ee4))

- Update plan
  ([`9015859`](https://github.com/foxpoint-se/nanomodem-python/commit/9015859272c7204638bd19bbdc1dee1a3889674f))

- Update readme to reflect current state
  ([`bc16d62`](https://github.com/foxpoint-se/nanomodem-python/commit/bc16d6252c65570bffbadf09e71a847168d6844f))

### Features

- Add serial bridge scenario for full-stack integration testing
  ([`ce3c10e`](https://github.com/foxpoint-se/nanomodem-python/commit/ce3c10e0a753b2b8c1ed13a5bf0e7880e56d937c))

- Add serial broker for virtual hardware integration testing
  ([`808cdb0`](https://github.com/foxpoint-se/nanomodem-python/commit/808cdb0c9a17d6b759b7a0e1e6e2bf056dd5f399))

- Replace on_state_changed with typed callbacks and auto-sync position to sim
  ([`92035a5`](https://github.com/foxpoint-se/nanomodem-python/commit/92035a54ad48d76937835b3c8a84cbd990caefce))

### Refactoring

- Consolidate demo things into demo folder and install target
  ([`c4442c8`](https://github.com/foxpoint-se/nanomodem-python/commit/c4442c883a5788f9c6054ff82abc73ba32012b0e))

- Get rid of some "type: ignore"
  ([`7d8f249`](https://github.com/foxpoint-se/nanomodem-python/commit/7d8f249b3d4a210e078df45de695757dec3ef50a))


## v1.0.0 (2026-03-28)

- Initial Release
