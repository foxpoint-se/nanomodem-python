# CHANGELOG

<!-- version list -->

## v4.1.0 (2026-07-03)

### Bug Fixes

- Address Copilot review on CLI callback and error handling
  ([`017a6ef`](https://github.com/foxpoint-se/nanomodem-python/commit/017a6ef473e3a01972aaf357fcf7e4d0250b1aca))

- Address follow-up review on transport API and CLI help
  ([`645e7c1`](https://github.com/foxpoint-se/nanomodem-python/commit/645e7c1cce92b1783a65a437b6118c56cd6459a1))

- Tighten CLI review follow-ups on deps and error hints
  ([`a8e94dc`](https://github.com/foxpoint-se/nanomodem-python/commit/a8e94dc5e1b1c1714f77a9ea606d83ad366a2dbd))

- Validate CLI node ids and sound speed before startup
  ([`6aeb2ca`](https://github.com/foxpoint-se/nanomodem-python/commit/6aeb2cad53abe4dd5542a9b9e102188dad830bb7))

### Features

- **nanomodem-cli**: Add one-shot status and ping commands
  ([`2657c42`](https://github.com/foxpoint-se/nanomodem-python/commit/2657c420c058d1a2f40655fc594873131890e77e))


## v4.0.0 (2026-07-02)

### Refactoring

- **nanomodem-demo**: Rename God View transport for clarity
  ([`0e573ac`](https://github.com/foxpoint-se/nanomodem-python/commit/0e573acd6660b056707f8a0b78cbc60310660f37))

### Breaking Changes

- **nanomodem-demo**: NetworkMockTransport removed; use SimulatorJsonTransport from
  nanomodem_demo.transports.


## v3.0.0 (2026-06-28)

### Bug Fixes

- Address Copilot review on sender id, spec imports, and log text
  ([`544fef7`](https://github.com/foxpoint-se/nanomodem-python/commit/544fef77deb7206ed10356b63c8fb42dd41cff5a))

- Allow zero-byte payloads in broadcast and unicast wire regexes
  ([`a82bc1f`](https://github.com/foxpoint-se/nanomodem-python/commit/a82bc1f672ddeb93e4927b97e63437a2deb3f86a))

- Emit local ack events from InMemoryBus command handlers
  ([`a8a032b`](https://github.com/foxpoint-se/nanomodem-python/commit/a8a032b88a00bcf42957c69c26da3dcb9ffd0679))

- End-anchor driver regexes and cap wire payload length at 99 bytes
  ([`97ecc82`](https://github.com/foxpoint-se/nanomodem-python/commit/97ecc82e45eca3131a0df9e2251aa358ba37caa1))

- Enforce wire byte counts in driver and strict 32-byte decode
  ([`1c86b43`](https://github.com/foxpoint-se/nanomodem-python/commit/1c86b43873e870096093e307edbafbd06cc5b024))

- Harden ModemNode event handling and position codec encoding
  ([`0fc0c90`](https://github.com/foxpoint-se/nanomodem-python/commit/0fc0c902804ed8a71ce10892ba5742a77fd04729))

- Keep core free of positioning deps and log wire sender id
  ([`d743605`](https://github.com/foxpoint-se/nanomodem-python/commit/d743605f1a1f4a5ce776a5af0e4194140ebb7ff4))

- Lazy-load positioning exports from nanomodem package root
  ([`5cf6039`](https://github.com/foxpoint-se/nanomodem-python/commit/5cf6039471b253796cc4183a7a7582860a1c87b4))

- Log InMemoryBus address collision on SetAddressCommand
  ([`4939458`](https://github.com/foxpoint-se/nanomodem-python/commit/4939458febd58d01d28719974f2fe8837508e9b9))

- Raise on unsupported ModemCommand in driver format_command
  ([`f8a0dc2`](https://github.com/foxpoint-se/nanomodem-python/commit/f8a0dc21e344a543ed0daf9e70c6f89b5bbe289e))

- Reject BasicPositionCodec payloads that are not exactly 32 bytes
  ([`4549bee`](https://github.com/foxpoint-se/nanomodem-python/commit/4549bee3b4e25bb9cf781fc48f66735613bc4432))

- Rekey in-memory transport on set-address and log all modem events
  ([`6297705`](https://github.com/foxpoint-se/nanomodem-python/commit/6297705ca25f787240dcaa0ff4063ecdde052cb4))

- Simulate all ModemCommand variants in InMemoryBus
  ([`8081cc0`](https://github.com/foxpoint-se/nanomodem-python/commit/8081cc0866982c107c95d5e555d897974ebb2102))

- Tolerate replacement chars when encoding broadcast/unicast payloads
  ([`2a7f94f`](https://github.com/foxpoint-se/nanomodem-python/commit/2a7f94fd79669211b83513bc9e2f74bd44d4cd9c))

### Chores

- Sync uv.lock workspace package versions
  ([`ed0ea77`](https://github.com/foxpoint-se/nanomodem-python/commit/ed0ea7772c4543d9522feb9f9585db723d2d7a2d))

### Features

- Remove legacy AcousticNode API in favor of core/positioning stack
  ([`34e8e3a`](https://github.com/foxpoint-se/nanomodem-python/commit/34e8e3a27b8ceb17d3daed516ca6ed92d579e08c))

- **core**: Add codec-free NanomodemV3Driver
  ([`00d57fc`](https://github.com/foxpoint-se/nanomodem-python/commit/00d57fc9313f19d835d6800627dea4042a2da8b5))

- **core**: Add ModemCommand and ModemEvent wire types
  ([`767485e`](https://github.com/foxpoint-se/nanomodem-python/commit/767485e242eb3e93842dddd719c9f1c3e9bf2000))

- **core**: Add ModemNode with generic PayloadCodec
  ([`e05f54b`](https://github.com/foxpoint-se/nanomodem-python/commit/e05f54b9486583d3ae0f02d4faee177ea1f0b43c))

- **core**: Add WireTransport implementations for serial and in-memory
  ([`5dd1881`](https://github.com/foxpoint-se/nanomodem-python/commit/5dd18815cacbe7ab5f6877134db426318e2f9e2c))

- **positioning**: Add PositioningNode and move LBL types
  ([`afa025d`](https://github.com/foxpoint-se/nanomodem-python/commit/afa025db334dc54d7102ed1d27bb4648be53a247))

### Refactoring

- Add core and positioning package skeleton
  ([`fded14d`](https://github.com/foxpoint-se/nanomodem-python/commit/fded14d1b69a3466f407de43713453755954c6e3))

- **demo**: Move God View simulator glue out of core
  ([`b096cd8`](https://github.com/foxpoint-se/nanomodem-python/commit/b096cd878a5d270a77aefa392369e0ed4df33297))

### Breaking Changes

- The public API has been redesigned for cleaner separation.


## v2.0.0 (2026-06-16)

### Bug Fixes

- Catch TclError when updating map markers
  ([`9313a3c`](https://github.com/foxpoint-se/nanomodem-python/commit/9313a3c8ce5504320ceb08ade9ef468a17acf868))

- Derive __version__ from package metadata
  ([`ed3bf76`](https://github.com/foxpoint-se/nanomodem-python/commit/ed3bf76589de0726251c7fece16ca9c3f772bbb5))

- Stop PTY reader on I/O errors instead of continuing
  ([`d373ad9`](https://github.com/foxpoint-se/nanomodem-python/commit/d373ad9fe3cf2c81075ebb05fe835a545387a250))

### Chores

- Mark workspace migration as breaking release
  ([`65d3428`](https://github.com/foxpoint-se/nanomodem-python/commit/65d34283f2c01b59969cddb310377b276fb015c6))

### Documentation

- Align docs and verify targets with submodule imports
  ([`e01cd73`](https://github.com/foxpoint-se/nanomodem-python/commit/e01cd73b6d49aa4174de23a83fecd7b84da3a14e))

- Clarify two-step pip install from GitHub
  ([`573a49c`](https://github.com/foxpoint-se/nanomodem-python/commit/573a49cb4f2cee560eedd8fdab6df9ca9a682455))

### Refactoring

- Replace Any with sim_types in network message paths
  ([`c4df0a5`](https://github.com/foxpoint-se/nanomodem-python/commit/c4df0a5964cc8d379df43b902baddd2097dfe387))

- Require submodule imports instead of root re-exports
  ([`a37dd4a`](https://github.com/foxpoint-se/nanomodem-python/commit/a37dd4a1c365e7280c59e2a0f9dc8a0794064b50))

- Split repo into uv workspace with separate lib and demo packages
  ([`602bb19`](https://github.com/foxpoint-se/nanomodem-python/commit/602bb19f55a6b629392b70631e41a865f751db61))

- Type remaining simulator backend JSON payloads
  ([`a66f838`](https://github.com/foxpoint-se/nanomodem-python/commit/a66f838284ae65bc266c86e65ba21e0574a4d196))

### Breaking Changes

- Split into nanomodem and nanomodem-demo packages. Removed root re-exports and nanomodem.demo; use
  nanomodem_demo and submodule imports instead. The [demo] extra is removed.


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
