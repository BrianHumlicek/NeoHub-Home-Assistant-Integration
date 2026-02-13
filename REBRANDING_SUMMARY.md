# Rebranding Summary: Z-Wave JS Pattern

## What Users See

| Location | Display Name |
|----------|--------------|
| Integration List | **DSC Neo** (with DSC logo) |
| Config Flow Title | "Connect to NeoHub" |
| Config Flow Description | "Configure your NeoHub connection to integrate DSC Neo alarm panels." |
| Device Name | Whatever the panel reports (e.g., "Home Panel") |
| Entities | User-friendly names from the panel |

## Technical Names (Backend)

| Component | Technical Name |
|-----------|----------------|
| Domain | `neohub` |
| Folder | `custom_components/dsc_neo` → rename to `custom_components/neohub` |
| Library Package | `pyneohub` |
| Library Folder | `pydscneo/` → rename to `pyneohub/` |
| Coordinator Class | `NeoHubCoordinator` |
| Client Class | `NeoHubClient` |

## Next Steps (Manual)

1. **Rename folders:**
   ```
   custom_components/dsc_neo → custom_components/neohub
   pydscneo → pyneohub
   ```

2. **Add DSC logo:**
   - Download official DSC logo
   - Save as `custom_components/neohub/icon.png` (256x256px)
   - Optionally `logo.png` for larger branding

3. **Test the integration:**
   - Restart Home Assistant
   - Add integration: should show "DSC Neo" with logo
   - Config flow: should say "Connect to NeoHub"

## Result

Just like Z-Wave JS:
- **Repository:** "NeoHub Integration" 
- **PyPI Package:** `pyneohub`
- **User sees:** "DSC Neo" 🎯
- **Code uses:** `neohub` domain
- **No conflicts** with potential future direct DSC Neo integrations
