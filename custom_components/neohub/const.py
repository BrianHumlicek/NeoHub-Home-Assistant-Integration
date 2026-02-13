"""Constants for the DSC Neo (via NeoHub) integration."""

DOMAIN = "neohub"

CONF_SSL = "ssl"
CONF_ACCESS_TOKEN = "access_token"

DEFAULT_PORT = 8080
DEFAULT_SSL = False

SIGNAL_STATE_UPDATED = f"{DOMAIN}_state_updated"
SIGNAL_CONNECTION_STATE = f"{DOMAIN}_connection_state"
