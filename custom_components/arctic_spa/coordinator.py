"""WebSocket connection to the spa's local Customer Portal server (port 8765).

The spa does not broadcast on a timer: send {"query": 0} to get a snapshot. The
coordinator keeps a persistent WebSocket open (auto-reconnecting) and re-queries
on an interval; a background reader merges the pushed envelopes into the state.
Commands are sent as plain JSON on the same socket.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import timedelta
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    QUERY,
    SCAN_INTERVAL_SECONDS,
    TELEMETRY_SECTIONS,
)

_LOGGER = logging.getLogger(__name__)

_RECONNECT_BACKOFF = (2, 5, 10, 30, 60)
_WS_HEARTBEAT = 25.0       # aiohttp ping to detect a dead TCP link
_QUERY_REPLY_TIMEOUT = 5.0  # how long to wait for a `live` after a query


class SpaWebSocketClient:
    """Persistent auto-reconnecting WebSocket to ws://<host>:<port>."""

    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        self._hass = hass
        self._host = host
        self._port = port
        self._url = f"ws://{host}:{port}"
        self.sections: dict[str, dict[str, Any]] = {}
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._supervisor: asyncio.Task | None = None
        self._running = False
        self._connected = asyncio.Event()
        self._live_event = asyncio.Event()

    async def async_start(self) -> None:
        self._running = True
        self._supervisor = self._hass.async_create_background_task(
            self._run(), name=f"{DOMAIN}_ws_{self._host}"
        )

    async def async_stop(self) -> None:
        self._running = False
        if self._supervisor:
            self._supervisor.cancel()
        if self._ws is not None and not self._ws.closed:
            await self._ws.close()

    @property
    def connected(self) -> bool:
        return self._ws is not None and not self._ws.closed

    async def _run(self) -> None:
        attempt = 0
        session = async_get_clientsession(self._hass)
        while self._running:
            try:
                async with session.ws_connect(
                    self._url, heartbeat=_WS_HEARTBEAT
                ) as ws:
                    self._ws = ws
                    self._connected.set()
                    attempt = 0
                    _LOGGER.debug("Connected to spa %s", self._url)
                    await ws.send_str(json.dumps(QUERY))
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            self._handle(msg.data)
                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001 - keep the supervisor alive
                _LOGGER.debug("Spa WebSocket error: %s", err)
            finally:
                self._ws = None
                self._connected.clear()
            if not self._running:
                break
            delay = _RECONNECT_BACKOFF[min(attempt, len(_RECONNECT_BACKOFF) - 1)]
            attempt += 1
            await asyncio.sleep(delay)

    def _handle(self, raw: str) -> None:
        try:
            payload = json.loads(raw)
        except ValueError:
            return
        if not isinstance(payload, dict) or payload.get("action") != "publish":
            return
        section = payload.get("topic")
        data = payload.get("data")
        if section in TELEMETRY_SECTIONS and isinstance(data, dict):
            self.sections.setdefault(section, {}).update(data)
            if section == "live":
                self._live_event.set()

    async def async_query(self) -> dict[str, dict[str, Any]]:
        """Request a fresh snapshot and return the merged state."""
        try:
            await asyncio.wait_for(self._connected.wait(), timeout=10)
        except asyncio.TimeoutError as err:
            raise UpdateFailed("spa not reachable") from err
        self._live_event.clear()
        assert self._ws is not None
        await self._ws.send_str(json.dumps(QUERY))
        try:
            await asyncio.wait_for(self._live_event.wait(), timeout=_QUERY_REPLY_TIMEOUT)
        except asyncio.TimeoutError:
            # Keep last-known data; a later query or push may catch up.
            _LOGGER.debug("No live reply within %ss", _QUERY_REPLY_TIMEOUT)
        return {k: dict(v) for k, v in self.sections.items()}

    async def async_send_command(self, payload: dict[str, Any]) -> None:
        try:
            await asyncio.wait_for(self._connected.wait(), timeout=10)
        except asyncio.TimeoutError:
            _LOGGER.warning("Cannot send command, spa not connected")
            return
        assert self._ws is not None
        body = json.dumps(payload)
        _LOGGER.debug("Sending command: %s", body)
        await self._ws.send_str(body)


class SpaCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Polls the spa with {"query": 0} on an interval; data is merged sections."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: SpaWebSocketClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.entry = entry
        self.client = client

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        return await self.client.async_query()

    def get(self, section: str, field: str) -> Any:
        data = self.data or {}
        return data.get(section, {}).get(field)

    async def async_send_command(self, payload: dict[str, Any]) -> None:
        await self.client.async_send_command(payload)
        # A command changes state; re-query shortly so HA reflects it quickly.
        await asyncio.sleep(0.4)
        self.async_set_updated_data(await self.client.async_query())
