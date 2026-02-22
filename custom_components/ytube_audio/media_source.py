"""Media source for ytube-audio."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.media_player import BrowseError, MediaClass, MediaType
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.core import HomeAssistant

from .const import DEFAULT_FORMAT, DOMAIN

if TYPE_CHECKING:
    from .ytdlp import YtDlpProcessor

_LOGGER = logging.getLogger(__name__)

YOUTUBE_AUDIO_DOMAIN = "ytube_audio"


async def async_get_media_source(hass: HomeAssistant) -> YouTubeAudioMediaSource:
    """Set up YouTube Audio media source."""
    return YouTubeAudioMediaSource(hass)


class YouTubeAudioMediaSource(MediaSource):
    """Provide YouTube audio as a media source."""

    name = "ytube-audio"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the media source."""
        super().__init__(YOUTUBE_AUDIO_DOMAIN)
        self.hass = hass

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve a media item to a playable URL."""
        video_id = item.identifier

        if not video_id:
            raise Unresolvable("No video ID provided")

        processor = self._get_processor()
        if processor is None:
            raise Unresolvable("YouTube Audio integration not ready")

        audio_format = self._get_default_format()

        try:
            audio_url, content_type = await processor.extract_audio_url(
                video_id, audio_format
            )

            if not audio_url:
                raise Unresolvable(f"Could not extract audio for video: {video_id}")

            return PlayMedia(
                url=audio_url,
                mime_type=content_type or "audio/mp4",
            )

        except Exception as err:
            _LOGGER.error("Error resolving media: %s", err)
            raise Unresolvable(str(err)) from err

    async def async_browse_media(
        self,
        item: MediaSourceItem,
    ) -> BrowseMediaSource:
        """Browse media."""
        if item.identifier:
            return await self._async_browse_video(item.identifier)

        return BrowseMediaSource(
            domain=YOUTUBE_AUDIO_DOMAIN,
            identifier="",
            media_class=MediaClass.CHANNEL,
            media_content_type=MediaType.MUSIC,
            title="YouTube Audio",
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.MUSIC,
            children=[
                BrowseMediaSource(
                    domain=YOUTUBE_AUDIO_DOMAIN,
                    identifier="search",
                    media_class=MediaClass.DIRECTORY,
                    media_content_type=MediaType.MUSIC,
                    title="Search YouTube",
                    can_play=False,
                    can_expand=False,
                ),
            ],
        )

    async def _async_browse_video(self, video_id: str) -> BrowseMediaSource:
        """Browse a specific video."""
        processor = self._get_processor()
        
        if processor is None:
            raise BrowseError("YouTube Audio integration not ready")

        try:
            info = await processor.get_video_info(video_id)
            
            if info is None:
                raise BrowseError(f"Could not get info for video: {video_id}")

            return BrowseMediaSource(
                domain=YOUTUBE_AUDIO_DOMAIN,
                identifier=video_id,
                media_class=MediaClass.MUSIC,
                media_content_type=MediaType.MUSIC,
                title=info.get("title", video_id),
                can_play=True,
                can_expand=False,
                thumbnail=info.get("thumbnail"),
            )

        except Exception as err:
            _LOGGER.error("Error browsing video: %s", err)
            raise BrowseError(str(err)) from err

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
