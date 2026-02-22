"""Sensor platform for yt-dlp Audio Player queue."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up queue sensors."""
    # We'll create sensors dynamically when queues are created
    pass


class QueueSensor(SensorEntity):
    """Sensor representing a media player's queue."""

    def __init__(
        self,
        hass: HomeAssistant,
        entity_id: str,
        queue_manager,
    ) -> None:
        """Initialize the queue sensor."""
        self.hass = hass
        self._media_player = entity_id
        self._queue_manager = queue_manager
        self._attr_unique_id = f"ytube_audio_queue_{entity_id.replace('.', '_')}"
        self._attr_name = f"yt-dlp Queue ({entity_id.split('.')[-1]})"

    @property
    def native_value(self) -> int:
        """Return the queue length."""
        queue_info = self._queue_manager.get_queue_info(self._media_player)
        return queue_info.get("length", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return queue details as attributes."""
        return self._queue_manager.get_queue_info(self._media_player)

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:playlist-music"
