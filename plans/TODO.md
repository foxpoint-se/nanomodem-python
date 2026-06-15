# TODO

## Driver / transport layering

- [ ] Expose raw V3 commands ($P, $B, $U, $M, $E, $A…) on driver + transport
- [ ] Stop hardcoding `request_range()` → ping; let consumer pick command ($M vs $P)
- [ ] Split hardware responses (#R, #B…) from codec payload decoding
- [ ] Node owns codec for encode/decode; transport moves bytes only

## AcousticNode API

- [ ] `NodeUpdate` + `update_known_node()`
- [ ] Callbacks: `on_range_measured`, per-node update/delete, `on_position_inferred`

## MockEther enhancements

- [ ] Configurable propagation delay simulation
- [ ] Packet loss simulation (drop probability)
- [ ] Occasional timeout simulation (target unreachable)
- [ ] Acoustic noise / range measurement error

## Node capabilities

- [ ] `track_node` capability (beacon tracking a submerged unit)
- [ ] On-change callback for position updates (for GUI reactivity)
- [ ] Periodic broadcast timer (vs. only on position change)

## Network status

- [ ] Heartbeat mechanism for online/offline detection
- [ ] Auto-registration of new nodes joining the network
- [ ] Node list with last-seen timestamps
- [ ] Alerting when a node goes offline

## Commands and statuses

- [ ] Supply voltage query ($Vxxx)
- [ ] Address configuration ($Axxx)
- [ ] Echo test ($Exxx)

## NanomodemTransport

- [ ] Wire NanomodemTransport into demo scenario main loop (e.g. `text_mock_demo.py`)
- [ ] Application-level timeout for $M (unicast with ack)
- [ ] Unicast data send_to / send_to_with_ack methods
- [ ] Handle serial disconnection and reconnection

## General

- [ ] Logging configuration (file output, log levels)
- [ ] Configuration file (YAML/TOML) for node setup
- [ ] ROS transport implementation (not just conceptual)
- [ ] Multi-machine deployment guide
