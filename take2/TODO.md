# TODO

## Visualization

- [ ] GUI with OpenStreetMap (lat/lon coordinates)
- [ ] Two windows: state visualization + state setting (simulation)
- [ ] Depth slider for simulated depth
- [ ] Buttons for executing functions (range to node, broadcast position)
- [ ] Draggable beacon nodes on the simulation canvas
- [ ] Estimated position marker on the visualization canvas
- [ ] Range circles around beacons

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

- [ ] Supply voltage query ($? and $Vxxx)
- [ ] Address configuration ($Axxx)
- [ ] Test message ($Txxx)
- [ ] Echo test ($Exxx)
- [ ] Quality indicator ($Q)

## NanomodemTransport

- [ ] Wire NanomodemTransport into __main__.py main loop
- [ ] Application-level timeout for $M (unicast with ack)
- [ ] Unicast data send_to / send_to_with_ack methods
- [ ] Handle serial disconnection and reconnection

## General

- [ ] Logging configuration (file output, log levels)
- [ ] Configuration file (YAML/TOML) for node setup
- [ ] ROS transport implementation (not just conceptual)
- [ ] Multi-machine deployment guide
