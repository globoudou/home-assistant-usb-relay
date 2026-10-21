"""Tests for the USB Relay integration, with a simulated relay board."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
import serial
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.usb_relay.const import DOMAIN
from custom_components.usb_relay.helpers import (
    build_switch_command,
    detect_usb_relays,
)

PORT = "/dev/ttyUSB0"


class FakeBoard:
    """A CH340 relay board speaking the 0xFF / 0xA0 protocol."""

    def __init__(self, relay_count: int = 4) -> None:
        self.relays = [0] * relay_count
        self.writes: list[bytes] = []
        self.fail = False
        self._out = b""

    def serial(self, port, baudrate=9600, timeout=None):
        if self.fail:
            raise serial.SerialException("device unplugged")
        board = self

        class _Conn:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def write(self, data: bytes) -> None:
                board.writes.append(bytes(data))
                if data == b"\xff":
                    board._out = bytes(board.relays)
                elif len(data) == 4 and data[0] == 0xA0:
                    assert data[3] == (data[0] + data[1] + data[2]) & 0xFF
                    board.relays[data[1] - 1] = data[2]

            def read(self, size: int) -> bytes:
                out, board._out = board._out[:size], board._out[size:]
                return out

        return _Conn()


@pytest.fixture
def board():
    fake = FakeBoard()
    with patch("serial.Serial", side_effect=fake.serial):
        yield fake


async def _setup(hass: HomeAssistant, relay_count: int = 4) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"USB Relay ({PORT})",
        unique_id=PORT,
        data={"port": PORT, "relay_count": relay_count},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def test_switch_command() -> None:
    assert build_switch_command(1, True) == bytes([0xA0, 0x02, 0x01, 0xA3])
    assert build_switch_command(0, False) == bytes([0xA0, 0x01, 0x00, 0xA1])


def test_detect(board: FakeBoard) -> None:
    ports = [SimpleNamespace(device=PORT), SimpleNamespace(device="/dev/ttyS0")]

    def fake_serial(port, *args, **kwargs):
        if port != PORT:
            raise serial.SerialException("not a relay")
        return board.serial(port)

    with (
        patch("serial.tools.list_ports.comports", return_value=ports),
        patch("serial.Serial", side_effect=fake_serial),
    ):
        assert detect_usb_relays() == {PORT: 4}


async def test_setup_and_switch(hass: HomeAssistant, board: FakeBoard) -> None:
    board.relays[2] = 1
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED

    states = {
        f"switch.usb_relay_relay_{i}": hass.states.get(f"switch.usb_relay_relay_{i}")
        for i in range(1, 5)
    }
    assert all(states.values())
    assert states["switch.usb_relay_relay_3"].state == "on"
    assert states["switch.usb_relay_relay_1"].state == "off"

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.usb_relay_relay_2"}, blocking=True
    )
    assert board.relays == [0, 1, 1, 0]
    assert bytes([0xA0, 0x02, 0x01, 0xA3]) in board.writes
    assert hass.states.get("switch.usb_relay_relay_2").state == "on"

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.usb_relay_relay_3"}, blocking=True
    )
    assert board.relays == [0, 1, 0, 0]
    assert hass.states.get("switch.usb_relay_relay_3").state == "off"

    # Unique IDs keep the pre-1.3.2 format, and the relays share one device.
    ent_reg = er.async_get(hass)
    assert ent_reg.async_get("switch.usb_relay_relay_1").unique_id == f"usb_relay::{PORT}::1"
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert len(devices) == 1

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_retry_when_unplugged(hass: HomeAssistant, board: FakeBoard) -> None:
    board.fail = True
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_legacy_entry_gets_unique_id(hass: HomeAssistant, board: FakeBoard) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={"port": PORT, "relay_count": 2})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.unique_id == PORT


async def test_config_flow(hass: HomeAssistant, board: FakeBoard) -> None:
    with patch(
        "custom_components.usb_relay.config_flow.detect_usb_relays",
        return_value={PORT: 4},
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_port"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"port": PORT})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"relay_count": 4})
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"port": PORT, "relay_count": 4}
    assert result["result"].unique_id == PORT


async def test_config_flow_no_device(hass: HomeAssistant) -> None:
    with patch("custom_components.usb_relay.config_flow.detect_usb_relays", return_value={}):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_config_flow_already_configured(hass: HomeAssistant, board: FakeBoard) -> None:
    await _setup(hass)
    with patch(
        "custom_components.usb_relay.config_flow.detect_usb_relays",
        return_value={PORT: 4},
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
