"""Python library for NeoHub - WebSocket bridge for DSC Neo alarm panels."""

from .client import NeoHubClient, NeoHubConnectionError, NeoHubError

__version__ = "0.1.0"

__all__ = [
    "NeoHubClient",
    "NeoHubConnectionError",
    "NeoHubError",
]
