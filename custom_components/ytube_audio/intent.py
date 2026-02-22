"""Intent handlers for ytube-audio."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

INTENT_PLAY_YOUTUBE = "PlayYouTubeAudio"


class PlayYouTubeAudioIntent(intent.IntentHandler):
    """Handle PlayYouTubeAudio intents."""

    intent_type = INTENT_PLAY_YOUTUBE
    slot_schema = {
        "query": str,
        "media_player": str,
    }

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the intent handler."""
        self.hass = hass

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        """Handle the intent."""
        slots = intent_obj.slots
        query = slots.get("query", {}).get("value", "")
        media_player = slots.get("media_player", {}).get("value", "")

        _LOGGER.debug("PlayYouTubeAudio intent: query=%s, media_player=%s", query, media_player)

        if not query:
            response = intent_obj.create_response()
            response.async_set_speech("I didn't catch what you wanted to play.")
            return response

        search_url = f"ytsearch:{query}"

        try:
            service_data = {
                "url": search_url,
                "media_player": media_player if media_player else self._get_default_player(),
            }

            if not service_data["media_player"]:
                response = intent_obj.create_response()
                response.async_set_speech("Please specify which speaker to play on.")
                return response

            await self.hass.services.async_call(
                DOMAIN,
                "play_audio",
                service_data,
                blocking=True,
            )

            response = intent_obj.create_response()
            response.async_set_speech(f"Playing {query} from YouTube Audio.")
            return response

        except Exception as err:
            _LOGGER.error("Error handling PlayYouTubeAudio intent: %s", err)
            response = intent_obj.create_response()
            response.async_set_speech(f"Sorry, I couldn't play that. {err}")
            return response

    def _get_default_player(self) -> str | None:
        """Get a default media player if none specified."""
        states = self.hass.states.async_all("media_player")
        for state in states:
            if state.state == "playing" or state.state == "idle":
                return state.entity_id
        return states[0].entity_id if states else None


def async_register_intents(hass: HomeAssistant) -> None:
    """Register intent handlers."""
    intent.async_register(hass, PlayYouTubeAudioIntent(hass))
