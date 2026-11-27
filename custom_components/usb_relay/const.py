"""Constants for the USB Relay integration."""

DOMAIN = "usb_relay"

CONF_PORT = "port"
CONF_RELAY_COUNT = "relay_count"

DEFAULT_BAUDRATE = 9600
DEFAULT_RELAY_COUNT = 8
MAX_RELAY_COUNT = 8
SERIAL_TIMEOUT = 0.5

BY_ID_PATH = "/dev/serial/by-id"

# USB vendor/product ID of the CH340 USB-to-serial chip.
CH340_USB_ID = (0x1A86, 0x7523)
