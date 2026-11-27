"""Blocking serial helpers for the USB Relay integration.

Every function in this module does blocking I/O and must be run in the
executor (``hass.async_add_executor_job``).
"""

from __future__ import annotations

import logging
import os

import serial
import serial.tools.list_ports

from .const import (
    BY_ID_PATH,
    CH340_USB_ID,
    DEFAULT_BAUDRATE,
    MAX_RELAY_COUNT,
    SERIAL_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

READ_STATE_COMMAND = bytes([0xFF])


def resolve_by_id(port: str) -> str:
    """Return the stable /dev/serial/by-id/... link for a port, if there is one."""
    if port.startswith(BY_ID_PATH) or not os.path.isdir(BY_ID_PATH):
        return port

    real_port = os.path.realpath(port)
    for entry in os.listdir(BY_ID_PATH):
        full_path = os.path.join(BY_ID_PATH, entry)
        if os.path.realpath(full_path) == real_port:
            return full_path
    return port


def is_valid_state(response: bytes) -> bool:
    """Return True if a state response looks like a relay board's."""
    return 1 <= len(response) <= MAX_RELAY_COUNT and all(b in (0, 1) for b in response)


def build_switch_command(relay_idx: int, state: bool) -> bytes:
    """Build the command that switches a relay.

    Protocol: 0xA0, relay number (1..N), state (1 = on, 0 = off), checksum,
    where checksum = (0xA0 + relay number + state) & 0xFF.
    """
    header = 0xA0
    relay_num = (relay_idx + 1) & 0xFF
    state_byte = 0x01 if state else 0x00
    checksum = (header + relay_num + state_byte) & 0xFF
    return bytes([header, relay_num, state_byte, checksum])


def list_serial_ports() -> dict[str, str]:
    """Return {port: label} for every serial port, without opening any of them.

    CH340 adapters (the chip used by these relay boards) are listed first.
    """
    ports: list[tuple[bool, str, str]] = []
    for port_info in serial.tools.list_ports.comports():
        port = resolve_by_id(port_info.device)
        label = port
        if port_info.description and port_info.description != "n/a":
            label = f"{port} - {port_info.description}"
        is_ch340 = (port_info.vid, port_info.pid) == CH340_USB_ID
        ports.append((not is_ch340, port, label))
    return {port: label for _, port, label in sorted(ports)}


def probe_relay_board(port: str) -> int | None:
    """Query one serial port and return its relay count, or None if no board answers.

    Raises ``serial.SerialException`` / ``OSError`` if the port cannot be opened.
    """
    with serial.Serial(port, DEFAULT_BAUDRATE, timeout=SERIAL_TIMEOUT) as ser:
        ser.write(READ_STATE_COMMAND)
        response = ser.read(MAX_RELAY_COUNT)

    if not is_valid_state(response):
        _LOGGER.debug("No relay board answered on %s: %s", port, response.hex())
        return None
    _LOGGER.debug("USB relay board on %s with %d relays", port, len(response))
    return len(response)
