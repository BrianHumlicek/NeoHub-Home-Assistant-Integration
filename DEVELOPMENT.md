# Development Guide

## Architecture

This project follows Home Assistant's best practices by separating domain logic into a standalone library:

- **`pyneohub/`** - Standalone Python library (would be published to PyPI)
- **`custom_components/dsc_neo/`** - Home Assistant integration (lightweight wrapper)

## Library Development (`pyneohub`)

The `pyneohub` library is a pure Python async WebSocket client with no Home Assistant dependencies.

### Local Development

For testing the integration with local library changes:

```bash
# Install the library in editable mode
pip install -e .

# Or install it in your Home Assistant venv
/path/to/homeassistant/venv/bin/pip install -e .
```

### Publishing to PyPI

1. Update version in `pydscneo/__init__.py` and `pyproject.toml`
2. Build the package:
   ```bash
   python -m build
   ```
3. Upload to PyPI:
   ```bash
   python -m twine upload dist/*
   ```

### Library Structure

```
pyneohub/
├── __init__.py          # Public API
├── client.py            # NeoHubClient class
```

**Key Design Principles:**
- Callback-based event system
- No Home Assistant imports
- Handles reconnection automatically
- All domain logic (WebSocket protocol, state management)

## Integration Development (`custom_components/dsc_neo`)

The Home Assistant integration is lightweight "glue code":

### Structure

```
custom_components/neohub/
├── __init__.py                 # Config entry setup/teardown
├── manifest.json               # Metadata + pydscneo dependency
├── config_flow.py              # UI configuration
├── coordinator.py              # Translates pydscneo callbacks → HA dispatchers
├── alarm_control_panel.py      # Partition entities
├── binary_sensor.py            # Zone entities
├── const.py                    # Constants
├── strings.json                # UI strings
└── translations/en.json        # Translations
```

### Coordinator Pattern

`NeoHubCoordinator` wraps `NeoHubClient` and:
1. Registers callbacks with the library
2. Translates callbacks into Home Assistant dispatcher signals
3. Manages the client lifecycle

### Testing Locally

1. Copy `custom_components/neohub/` to your HA config directory
2. If testing library changes, install `pyneohub` in editable mode
3. Restart Home Assistant
4. Add the integration via UI

## Development Workflow

### Working on Library Code

1. Make changes to `pyneohub/`
2. Test with a standalone script or pytest
3. Once stable, publish to PyPI
4. Update `manifest.json` version

### Working on Integration Code

1. Make changes to `custom_components/neohub/`
2. Test in Home Assistant dev environment
3. For HACS: tag a release on GitHub

## Publishing

### Library (pyneohub)

- Publish to PyPI: https://pypi.org/project/pyneohub/
- Repository: https://github.com/BrianHumlicek/DSC-Neo-Integration

### Integration

- Publish via HACS
- Repository: https://github.com/BrianHumlicek/DSC-Neo-Integration
- Users install from HACS, which downloads the integration
- Home Assistant automatically installs `pydscneo` from PyPI (via `requirements` in manifest.json)

## Example: Adding a New Feature

**Scenario:** Add support for bypassing zones

### 1. Update Library

`pyneohub/client.py`:
```python
async def bypass_zone(
    self, session_id: str, zone_number: int, code: str | None = None
) -> None:
    """Send a bypass zone command."""
    await self._send({
        "type": "bypass_zone",
        "session_id": session_id,
        "zone_number": zone_number,
        "code": code,
    })
```

Publish new library version to PyPI.

### 2. Update Integration

`custom_components/neohub/manifest.json`:
```json
{
  "requirements": ["pyneohub==0.2.0"]
}
```

`custom_components/neohub/binary_sensor.py`:
```python
async def async_bypass(self, code: str | None = None) -> None:
    """Bypass this zone."""
    await self._coordinator.client.bypass_zone(
        self._session_id, self._zone_number, code
    )
```

## References

- [Home Assistant Integration Manifest](https://developers.home-assistant.io/docs/creating_integration_manifest)
- [Home Assistant Requirements](https://developers.home-assistant.io/docs/creating_integration_manifest/#requirements)
- [zwave-js Integration](https://github.com/home-assistant/core/tree/dev/homeassistant/components/zwave_js) - Good example of library + integration pattern
