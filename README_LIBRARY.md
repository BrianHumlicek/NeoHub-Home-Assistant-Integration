# pyneohub

Python library for NeoHub - WebSocket bridge for DSC Neo alarm panels.

## Features

- Async WebSocket client
- Automatic reconnection with exponential backoff
- Callback-based event system
- No Home Assistant dependencies
- Full type hints

## Installation

```bash
pip install pyneohub
```

## Usage

```python
import asyncio
from pyneohub import NeoHubClient

async def main():
    client = NeoHubClient(
        host="192.168.1.100",
        port=8080,
        ssl=False,
        access_token="your_token_here"
    )
    
    # Register callbacks
    def on_connect():
        print("Connected!")
    
    def on_full_state(data):
        print(f"Received full state: {data}")
    
    def on_partition_update(data):
        print(f"Partition update: {data}")
    
    def on_zone_update(data):
        print(f"Zone update: {data}")
    
    client.register_connection_callback(on_connect)
    client.register_full_state_callback(on_full_state)
    client.register_partition_update_callback(on_partition_update)
    client.register_zone_update_callback(on_zone_update)
    
    # Connect
    try:
        await client.connect()
    except Exception as err:
        print(f"Connection failed: {err}")
        return
    
    # Wait for state
    await asyncio.sleep(2)
    
    # Send commands
    await client.arm_away("session_id", partition_number=1, code="1234")
    
    # Keep running
    await asyncio.sleep(60)
    
    # Disconnect
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

## API Reference

### NeoHubClient

#### Constructor

```python
NeoHubClient(
    host: str,
    port: int,
    *,
    ssl: bool = False,
    access_token: str | None = None
)
```

#### Properties

- `connected: bool` - Connection status
- `state: dict[str, Any]` - Current state keyed by session_id

#### Methods

##### Connection Management

- `async connect() -> bool` - Connect to the WebSocket server. Raises `DscNeoConnectionError` on failure.
- `async disconnect() -> None` - Disconnect from the server

##### Callback Registration

All registration methods return an unregister function.

- `register_connection_callback(callback: Callable[[], None])` - Called on connect
- `register_disconnection_callback(callback: Callable[[], None])` - Called on disconnect
- `register_full_state_callback(callback: Callable[[dict], None])` - Called on full_state message
- `register_partition_update_callback(callback: Callable[[dict], None])` - Called on partition updates
- `register_zone_update_callback(callback: Callable[[dict], None])` - Called on zone updates
- `register_error_callback(callback: Callable[[str], None])` - Called on server errors

##### Commands

- `async arm_away(session_id: str, partition_number: int, code: str | None = None)`
- `async arm_home(session_id: str, partition_number: int, code: str | None = None)`
- `async arm_night(session_id: str, partition_number: int, code: str | None = None)`
- `async disarm(session_id: str, partition_number: int, code: str | None = None)`

## License

MIT
