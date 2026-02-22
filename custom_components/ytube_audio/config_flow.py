"""Config flow for ytube-audio integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback, HomeAssistant

from .const import (
    CONF_CACHE_DIR,
    CONF_DEFAULT_FORMAT,
    CONF_PROXY_STREAM,
    DEFAULT_CACHE_DIR,
    DEFAULT_FORMAT,
    DOMAIN,
    FORMAT_BEST,
    FORMAT_M4A,
    FORMAT_MP3,
    FORMAT_OPUS,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_PROXY_STREAM, default=True): bool,
        vol.Optional(CONF_DEFAULT_FORMAT, default=DEFAULT_FORMAT): vol.In(
            [FORMAT_BEST, FORMAT_M4A, FORMAT_MP3, FORMAT_OPUS]
        ),
        vol.Optional(CONF_CACHE_DIR, default=DEFAULT_CACHE_DIR): str,
    }
)


class YTubeAudioConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ytube-audio."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return YTubeAudioOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title="ytube-audio",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class YTubeAudioOptionsFlow(OptionsFlow):
    """Handle options flow for ytube-audio."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            # Update the config entry data
            new_data = {**self.config_entry.data, **user_input}
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )
            return self.async_create_entry(title="", data=user_input)

        # Get current values
        current_proxy = self.config_entry.data.get(CONF_PROXY_STREAM, True)
        current_format = self.config_entry.data.get(CONF_DEFAULT_FORMAT, DEFAULT_FORMAT)
        current_cache = self.config_entry.data.get(CONF_CACHE_DIR, DEFAULT_CACHE_DIR)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_PROXY_STREAM, default=current_proxy): bool,
                    vol.Optional(CONF_DEFAULT_FORMAT, default=current_format): vol.In(
                        [FORMAT_BEST, FORMAT_M4A, FORMAT_MP3, FORMAT_OPUS]
                    ),
                    vol.Optional(CONF_CACHE_DIR, default=current_cache): str,
                }
            ),
        )
