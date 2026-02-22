"""Config flow for YouTube Audio Player integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant

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
    """Handle a config flow for YouTube Audio Player."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title="YouTube Audio Player",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
