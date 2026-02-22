"""HTTP proxy for streaming YouTube audio through Home Assistant."""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from aiohttp import web
from aiohttp.hdrs import (
    ACCEPT_RANGES,
    CONTENT_LENGTH,
    CONTENT_RANGE,
    CONTENT_TYPE,
    RANGE,
)

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DEFAULT_FORMAT, DOMAIN

if TYPE_CHECKING:
    from .ytdlp import YtDlpProcessor

_LOGGER = logging.getLogger(__name__)

RANGE_REGEX = re.compile(r"bytes=(\d*)-(\d*)")


class YTubeAudioProxyView(HomeAssistantView):
    """View to proxy YouTube audio streams through Home Assistant."""

    url = "/api/ytube_audio/stream/{video_id}"
    name = "api:ytube_audio:stream"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the proxy view."""
        self.hass = hass

    async def get(self, request: web.Request, video_id: str) -> web.StreamResponse:
        """Handle GET request - stream audio through HA with Range support."""
        audio_format = request.query.get("format", self._get_default_format())
        range_header = request.headers.get(RANGE)
        
        _LOGGER.debug(
            "Proxy request for video_id: %s (format: %s, range: %s)", 
            video_id, audio_format, range_header
        )

        processor = self._get_processor()
        if processor is None:
            return web.Response(status=503, text="Integration not ready")

        try:
            audio_url, content_type = await processor.extract_audio_url(video_id, audio_format)
            if not audio_url:
                _LOGGER.error("Failed to extract audio URL for: %s", video_id)
                return web.Response(status=404, text="Could not extract audio")

            session = async_get_clientsession(self.hass)
            
            upstream_headers = {}
            if range_header:
                upstream_headers[RANGE] = range_header

            async with session.get(audio_url, headers=upstream_headers) as upstream_response:
                if upstream_response.status not in (200, 206):
                    _LOGGER.error(
                        "Upstream returned %s for %s", 
                        upstream_response.status, 
                        video_id
                    )
                    return web.Response(
                        status=upstream_response.status,
                        text="Upstream error"
                    )

                final_content_type = (
                    content_type 
                    or upstream_response.headers.get(CONTENT_TYPE, "audio/webm")
                )

                response_headers = {
                    CONTENT_TYPE: final_content_type,
                    ACCEPT_RANGES: "bytes",
                }

                content_length = upstream_response.headers.get(CONTENT_LENGTH)
                if content_length:
                    response_headers[CONTENT_LENGTH] = content_length

                content_range = upstream_response.headers.get(CONTENT_RANGE)
                if content_range:
                    response_headers[CONTENT_RANGE] = content_range

                status = 206 if upstream_response.status == 206 else 200

                response = web.StreamResponse(
                    status=status,
                    headers=response_headers,
                )

                await response.prepare(request)

                async for chunk in upstream_response.content.iter_chunked(65536):
                    await response.write(chunk)

                await response.write_eof()
                return response

        except Exception as err:
            _LOGGER.error("Error proxying audio: %s", err)
            return web.Response(status=500, text=str(err))

    def _get_processor(self) -> YtDlpProcessor | None:
        """Get the yt-dlp processor from hass.data."""
        if DOMAIN not in self.hass.data:
            return None
        
        for entry_data in self.hass.data[DOMAIN].values():
            if isinstance(entry_data, dict) and "processor" in entry_data:
                return entry_data["processor"]
        
        return None

    def _get_default_format(self) -> str:
        """Get the default audio format from config."""
        if DOMAIN not in self.hass.data:
            return DEFAULT_FORMAT
        
        for entry_data in self.hass.data[DOMAIN].values():
            if isinstance(entry_data, dict) and "default_format" in entry_data:
                return entry_data["default_format"]
        
        return DEFAULT_FORMAT


def async_register_proxy_view(hass: HomeAssistant) -> None:
    """Register the proxy view with Home Assistant."""
    hass.http.register_view(YTubeAudioProxyView(hass))
