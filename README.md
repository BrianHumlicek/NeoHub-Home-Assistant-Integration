# This repository is currently under development, and is NOT fully functional yet.
#
# NeoHub Integration for Home Assistant

A Home Assistant integration for [NeoHub](https://github.com/BrianHumlicek/NeoHub) - connects DSC Neo alarm panels to Home Assistant via WebSocket.

This integration uses the [`pyneohub`](https://github.com/BrianHumlicek/NeoHub-Home-Assistant-Integration) Python library for all communication with the alarm panel.

## Architecture

- **`pyneohub`** - Standalone Python library on PyPI that handles WebSocket communication with NeoHub
- **Home Assistant Integration** - Lightweight glue code that bridges `pyneohub` with Home Assistant's entity system

## Features

- **Alarm Control Panel** entities for each partition (arm away, arm home, arm night, disarm)
- **Binary Sensor** entities for each zone (door, window, motion, smoke, etc.)
- Real-time push updates via WebSocket — no polling
- Automatic reconnection with exponential backoff
- HACS compatible

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots in the top right → **Custom repositories**
3. Add this repository URL and select **Integration** as the category
4. Search for **NeoHub** and install
5. Restart Home Assistant

### Manual

Copy the `custom_components/neohub` directory into your Home Assistant `config/custom_components/` directory and restart.

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **NeoHub**
3. Enter your NeoHub connection details:
   - **Host**: hostname or IP address of NeoHub server
   - **Port**: WebSocket port (default `8080`)
   - **Use SSL**: enable for `wss://` connections
   - **Access Token**: optional bearer token for authentication

## Entity Model

| Concept   | HA Entity Type        | Unique ID Format                                        |
|-----------|-----------------------|---------------------------------------------------------|
| Session   | Device                | `{session_id}`                                          |
| Partition | Alarm Control Panel   | `{session_id}_partition_{partition_number}`              |
| Zone      | Binary Sensor         | `{session_id}_zone_{zone_number}`                       |

Zones are session-level entities that can be associated with one or more partitions. Each zone appears as a single binary sensor with its partition associations listed in the entity attributes.

## Alarm Panel States

| API Status     | HA State        |
|----------------|-----------------|
| `disarmed`     | Disarmed        |
| `armed_away`   | Armed Away      |
| `armed_stay`   | Armed Home      |
| `armed_night`  | Armed Night     |
| `exit_delay`   | Arming          |
| `entry_delay`  | Pending         |
| `triggered`    | Triggered       |

---

## WebSocket API Specification

This section defines the WebSocket protocol between this integration and NeoHub. The endpoint is:

```
ws://{host}:{port}/api/ws
```

Authentication is via an optional `Authorization: Bearer {token}` header on the WebSocket upgrade request.

### Client → Server Messages

#### `get_full_state`

Request the complete state of all sessions, partitions, and zones. Sent on initial connection and after every reconnect.

```json
{
  "type": "get_full_state"
}
```

#### `arm_away`

```json
{
  "type": "arm_away",
  "session_id": "abc123",
  "partition_number": 1,
  "code": "1234"
}
```

#### `arm_home`

```json
{
  "type": "arm_home",
  "session_id": "abc123",
  "partition_number": 1,
  "code": "1234"
}
```

#### `arm_night`

```json
{
  "type": "arm_night",
  "session_id": "abc123",
  "partition_number": 1,
  "code": "1234"
}
```

#### `disarm`

```json
{
  "type": "disarm",
  "session_id": "abc123",
  "partition_number": 1,
  "code": "1234"
}
```

> `code` may be `null` if the panel does not require a code for the given action.

### Server → Client Messages

#### `full_state`

Sent in response to `get_full_state`. Contains the complete hierarchy.

```json
{
  "type": "full_state",
  "sessions": [
    {
      "session_id": "abc123",
      "name": "Home Panel",
      "partitions": [
        {
          "partition_number": 1,
          "name": "Main",
          "status": "armed_away"
        },
        {
          "partition_number": 2,
          "name": "Garage",
          "status": "disarmed"
        }
      ],
      "zones": [
        {
          "zone_number": 1,
          "name": "Front Door",
          "device_class": "door",
          "open": false,
          "partitions": [1, 2]
        },
        {
          "zone_number": 2,
          "name": "Living Room Motion",
          "device_class": "motion",
          "open": false,
          "partitions": [1]
        }
      ]
    }
  ]
}
```

**`status`** values: `disarmed`, `armed_away`, `armed_stay`, `armed_night`, `exit_delay`, `entry_delay`, `triggered`

**`device_class`** values: `door`, `window`, `motion`, `smoke`, `gas`, `moisture`, `vibration`, `safety`

#### `partition_update`

Pushed whenever a partition's state changes.

```json
{
  "type": "partition_update",
  "session_id": "abc123",
  "partition_number": 1,
  "status": "disarmed"
}
```

#### `zone_update`

Pushed whenever a zone's state changes.

```json
{
  "type": "zone_update",
  "session_id": "abc123",
  "zone_number": 1,
  "open": true
}
```

#### `error`

```json
{
  "type": "error",
  "message": "Invalid code"
}
```
