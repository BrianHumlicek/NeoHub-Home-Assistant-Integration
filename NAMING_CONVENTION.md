# Final Naming Convention

## Summary

Following the Z-Wave JS pattern with clear separation between bridge and device layers.

## Naming Rules

### Rule 1: NeoHub* → Bridge/Server Layer
Anything that deals with **NeoHub** (the WebSocket bridge server):
```python
# Library (pyneohub)
NeoHubClient            # WebSocket client
NeoHubError             # Base exception
NeoHubConnectionError   # Connection errors

# Integration (custom_components/neohub)
NeoHubCoordinator       # Manages NeoHub connection
NeoHubConfigFlow        # Configures NeoHub
```

### Rule 2: Dsc* → Device/Entity Layer
Anything that represents **DSC alarm panel** components:
```python
# Integration entities
DscAlarmPanel           # Partition entity (alarm_control_panel)
DscZoneSensor           # Zone entity (binary_sensor)
```

### Rule 3: Display Names
What users see in Home Assistant UI:
- Integration name: **"DSC Neo"** (distinguishes from legacy DSC integrations)
- Config flow: "Connect to NeoHub"
- Domain (internal): `neohub`

## Examples

### Good ✅
```python
# NeoHub layer
coordinator = NeoHubCoordinator(...)
client = NeoHubClient(host, port)

# DSC device layer
panel = DscAlarmPanel(coordinator, session_id, partition_number)
zone = DscZoneSensor(coordinator, session_id, zone_number)
```

### Avoid ❌
```python
# Don't mix naming layers
NeoZoneSensor       # ❌ Zone is a DSC concept, not NeoHub
DscClient           # ❌ Client connects to NeoHub, not DSC
NeoHubPanel         # ❌ Panel is a DSC device, not NeoHub
```

## Rationale

| Concept | Why This Name | Why Not Other |
|---------|---------------|---------------|
| `NeoHubClient` | Connects to NeoHub server | Not `DscClient` - doesn't connect directly to DSC |
| `DscAlarmPanel` | Represents DSC partition | Not `NeoPanel` - it's a DSC device concept |
| `DscZoneSensor` | Represents DSC zone | Not `NeoZone` - it's a DSC device concept |
| Domain: `neohub` | Technical name of the bridge | Avoids conflict with future direct DSC integration |
| Display: "DSC Neo" | What users search for | Distinguishes from legacy DSC integrations |

## Comparison to Z-Wave JS

| Z-Wave JS | Our Integration |
|-----------|-----------------|
| `zwave_js` domain | `neohub` domain |
| Display: "Z-Wave" | Display: "DSC Neo" |
| `ZwaveJSCoordinator` | `NeoHubCoordinator` |
| `ZWaveLightEntity` | `DscAlarmPanel`, `DscZoneSensor` |

Both follow the pattern: bridge is named after the server/protocol, entities are named after what they represent.
