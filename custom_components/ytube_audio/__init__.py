"""YouTube Audio Player integration for Home Assistant."""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant.components.media_player import (
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_PLAY_MEDIA,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import get_url

from .const import (
    ATTR_FORMAT,
    ATTR_INDEX,
    ATTR_MEDIA_PLAYER,
    ATTR_PLAY_NOW,
    ATTR_PROXY,
    ATTR_REPEAT,
    ATTR_SHUFFLE,
    ATTR_TIMESTAMP,
    ATTR_URL,
    AUDIO_FORMATS,
    CONF_CACHE_DIR,
    CONF_DEFAULT_FORMAT,
    CONF_PROXY_STREAM,
    DEFAULT_CACHE_DIR,
    DEFAULT_FORMAT,
    DOMAIN,
    SERVICE_ADD_TO_QUEUE,
    SERVICE_CLEAR_QUEUE,
    SERVICE_GET_QUEUE,
    SERVICE_NEXT_TRACK,
    SERVICE_PLAY_AUDIO,
    SERVICE_PREVIOUS_TRACK,
    SERVICE_REMOVE_FROM_QUEUE,
    SERVICE_SEEK,
    SERVICE_SET_REPEAT,
    SERVICE_SET_SHUFFLE,
)
from .http_proxy import async_register_proxy_view
from .intent import async_register_intents
from .queue import QueueManager
from .ytdlp import YtDlpProcessor

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLAY_AUDIO_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_URL): cv.string,
        vol.Required(ATTR_MEDIA_PLAYER): vol.Any(cv.entity_id, vol.All(cv.ensure_list, [cv.entity_id])),
        vol.Optional(ATTR_PROXY, default=True): cv.boolean,
        vol.Optional(ATTR_FORMAT): vol.In(list(AUDIO_FORMATS.keys())),
        vol.Optional(ATTR_TIMESTAMP): vol.Any(cv.positive_float, cv.string),
    }
)

SEEK_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDIA_PLAYER): vol.Any(cv.entity_id, vol.All(cv.ensure_list, [cv.entity_id])),
        vol.Required(ATTR_TIMESTAMP): vol.Any(cv.positive_float, cv.string),
    }
)

ADD_TO_QUEUE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_URL): cv.string,
        vol.Required(ATTR_MEDIA_PLAYER): cv.entity_id,
        vol.Optional(ATTR_PLAY_NOW, default=False): cv.boolean,
    }
)

QUEUE_PLAYER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDIA_PLAYER): cv.entity_id,
    }
)

REMOVE_FROM_QUEUE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDIA_PLAYER): cv.entity_id,
        vol.Required(ATTR_INDEX): cv.positive_int,
    }
)

SET_REPEAT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDIA_PLAYER): cv.entity_id,
        vol.Required(ATTR_REPEAT): cv.boolean,
    }
)

SET_SHUFFLE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDIA_PLAYER): cv.entity_id,
        vol.Required(ATTR_SHUFFLE): cv.boolean,
    }
)


def parse_timestamp(timestamp: str | float) -> float:
    """Parse timestamp from seconds or MM:SS / HH:MM:SS format."""
    if isinstance(timestamp, (int, float)):
        return float(timestamp)
    
    parts = timestamp.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    else:
        return float(timestamp)

YOUTUBE_VIDEO_ID_REGEX = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|"
    r"youtube\.com/v/|youtube\.com/shorts/|music\.youtube\.com/watch\?v=)"
    r"([a-zA-Z0-9_-]{11})"
)


def extract_video_id(url: str) -> str:
    """Extract video ID from YouTube URL or return as-is if already an ID."""
    if len(url) == 11 and re.match(r"^[a-zA-Z0-9_-]+$", url):
        return url
    
    match = YOUTUBE_VIDEO_ID_REGEX.search(url)
    if match:
        return match.group(1)
    
    return url


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the YouTube Audio component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up YouTube Audio from a config entry."""
    cache_dir = entry.data.get(CONF_CACHE_DIR, DEFAULT_CACHE_DIR)
    default_proxy = entry.data.get(CONF_PROXY_STREAM, True)
    default_format = entry.data.get(CONF_DEFAULT_FORMAT, DEFAULT_FORMAT)
    
    processor = YtDlpProcessor(hass, cache_dir)
    queue_manager = QueueManager(hass)
    
    hass.data[DOMAIN][entry.entry_id] = {
        "processor": processor,
        "default_format": default_format,
        "queue_manager": queue_manager,
    }

    async_register_proxy_view(hass)
    async_register_intents(hass)

    async def play_url_on_player(url: str, entity_id: str) -> None:
        """Helper to play a URL on a single player (used by queue)."""
        use_proxy = default_proxy
        audio_format = default_format
        
        if use_proxy:
            video_id = extract_video_id(url)
            base_url = get_url(hass, prefer_external=False)
            audio_url = f"{base_url}/api/ytube_audio/stream/{video_id}?format={audio_format}"
        else:
            audio_url, _ = await processor.extract_audio_url(url, audio_format)
            if not audio_url:
                _LOGGER.error("Failed to extract audio URL from: %s", url)
                return

        await hass.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            SERVICE_PLAY_MEDIA,
            {
                ATTR_ENTITY_ID: entity_id,
                ATTR_MEDIA_CONTENT_ID: audio_url,
                ATTR_MEDIA_CONTENT_TYPE: MediaType.MUSIC,
            },
            blocking=True,
        )

    queue_manager.set_play_callback(play_url_on_player)

    async def handle_play_audio(call: ServiceCall) -> None:
        """Handle the play_audio service call."""
        url = call.data[ATTR_URL]
        media_players = call.data[ATTR_MEDIA_PLAYER]
        use_proxy = call.data.get(ATTR_PROXY, default_proxy)
        audio_format = call.data.get(ATTR_FORMAT, default_format)
        
        if isinstance(media_players, str):
            media_players = [media_players]

        _LOGGER.debug(
            "Processing YouTube URL: %s for players: %s (proxy=%s, format=%s)", 
            url, media_players, use_proxy, audio_format
        )

        try:
            if use_proxy:
                video_id = extract_video_id(url)
                base_url = get_url(hass, prefer_external=False)
                audio_url = f"{base_url}/api/ytube_audio/stream/{video_id}?format={audio_format}"
                _LOGGER.debug("Using proxy URL: %s", audio_url)
            else:
                audio_url, _ = await processor.extract_audio_url(url, audio_format)
                
                if not audio_url:
                    _LOGGER.error("Failed to extract audio URL from: %s", url)
                    return

                _LOGGER.debug("Extracted direct audio URL: %s", audio_url[:100] + "...")

            tasks = []
            for player in media_players:
                tasks.append(
                    hass.services.async_call(
                        MEDIA_PLAYER_DOMAIN,
                        SERVICE_PLAY_MEDIA,
                        {
                            ATTR_ENTITY_ID: player,
                            ATTR_MEDIA_CONTENT_ID: audio_url,
                            ATTR_MEDIA_CONTENT_TYPE: MediaType.MUSIC,
                        },
                        blocking=True,
                    )
                )
            
            await asyncio.gather(*tasks)
            _LOGGER.info("Started playback on %d media player(s)", len(media_players))

            timestamp = call.data.get(ATTR_TIMESTAMP)
            if timestamp is not None:
                seek_position = parse_timestamp(timestamp)
                _LOGGER.debug("Seeking to %s seconds", seek_position)
                await asyncio.sleep(0.5)
                
                seek_tasks = []
                for player in media_players:
                    seek_tasks.append(
                        hass.services.async_call(
                            MEDIA_PLAYER_DOMAIN,
                            "media_seek",
                            {
                                ATTR_ENTITY_ID: player,
                                "seek_position": seek_position,
                            },
                            blocking=True,
                        )
                    )
                await asyncio.gather(*seek_tasks)

        except Exception as err:
            _LOGGER.error("Error playing audio: %s", err)
            raise

    async def handle_seek(call: ServiceCall) -> None:
        """Handle the seek service call."""
        media_players = call.data[ATTR_MEDIA_PLAYER]
        timestamp = call.data[ATTR_TIMESTAMP]
        
        if isinstance(media_players, str):
            media_players = [media_players]

        seek_position = parse_timestamp(timestamp)
        _LOGGER.debug("Seeking to %s seconds on %s", seek_position, media_players)

        tasks = []
        for player in media_players:
            tasks.append(
                hass.services.async_call(
                    MEDIA_PLAYER_DOMAIN,
                    "media_seek",
                    {
                        ATTR_ENTITY_ID: player,
                        "seek_position": seek_position,
                    },
                    blocking=True,
                )
            )
        
        await asyncio.gather(*tasks)

    async def handle_add_to_queue(call: ServiceCall) -> None:
        """Handle the add_to_queue service call."""
        url = call.data[ATTR_URL]
        entity_id = call.data[ATTR_MEDIA_PLAYER]
        play_now = call.data.get(ATTR_PLAY_NOW, False)
        
        playlist_items = await processor.extract_playlist(url)
        
        if len(playlist_items) > 1:
            _LOGGER.info("Adding %d items from playlist to queue", len(playlist_items))
            for i, item in enumerate(playlist_items):
                should_play = play_now and i == 0
                await queue_manager.add_to_queue(
                    entity_id, 
                    item["url"], 
                    title=item.get("title"),
                    play_now=should_play
                )
        else:
            await queue_manager.add_to_queue(entity_id, url, play_now=play_now)

    async def handle_clear_queue(call: ServiceCall) -> None:
        """Handle the clear_queue service call."""
        entity_id = call.data[ATTR_MEDIA_PLAYER]
        queue_manager.clear_queue(entity_id)

    async def handle_next_track(call: ServiceCall) -> None:
        """Handle the next_track service call."""
        entity_id = call.data[ATTR_MEDIA_PLAYER]
        await queue_manager.play_next(entity_id)

    async def handle_previous_track(call: ServiceCall) -> None:
        """Handle the previous_track service call."""
        entity_id = call.data[ATTR_MEDIA_PLAYER]
        await queue_manager.play_previous(entity_id)

    async def handle_remove_from_queue(call: ServiceCall) -> None:
        """Handle the remove_from_queue service call."""
        entity_id = call.data[ATTR_MEDIA_PLAYER]
        index = call.data[ATTR_INDEX]
        queue_manager.remove_from_queue(entity_id, index)

    async def handle_set_repeat(call: ServiceCall) -> None:
        """Handle the set_repeat service call."""
        entity_id = call.data[ATTR_MEDIA_PLAYER]
        repeat = call.data[ATTR_REPEAT]
        queue_manager.set_repeat(entity_id, repeat)

    async def handle_set_shuffle(call: ServiceCall) -> None:
        """Handle the set_shuffle service call."""
        entity_id = call.data[ATTR_MEDIA_PLAYER]
        shuffle = call.data[ATTR_SHUFFLE]
        queue_manager.set_shuffle(entity_id, shuffle)

    def handle_get_queue(call: ServiceCall) -> dict:
        """Handle the get_queue service call."""
        entity_id = call.data[ATTR_MEDIA_PLAYER]
        return queue_manager.get_queue_info(entity_id)

    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY_AUDIO,
        handle_play_audio,
        schema=PLAY_AUDIO_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEEK,
        handle_seek,
        schema=SEEK_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_TO_QUEUE,
        handle_add_to_queue,
        schema=ADD_TO_QUEUE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_QUEUE,
        handle_clear_queue,
        schema=QUEUE_PLAYER_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_NEXT_TRACK,
        handle_next_track,
        schema=QUEUE_PLAYER_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_PREVIOUS_TRACK,
        handle_previous_track,
        schema=QUEUE_PLAYER_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_FROM_QUEUE,
        handle_remove_from_queue,
        schema=REMOVE_FROM_QUEUE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_REPEAT,
        handle_set_repeat,
        schema=SET_REPEAT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SHUFFLE,
        handle_set_shuffle,
        schema=SET_SHUFFLE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_QUEUE,
        handle_get_queue,
        schema=QUEUE_PLAYER_SCHEMA,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    entry_data = hass.data[DOMAIN].get(entry.entry_id, {})
    if "queue_manager" in entry_data:
        entry_data["queue_manager"].cleanup()

    hass.services.async_remove(DOMAIN, SERVICE_PLAY_AUDIO)
    hass.services.async_remove(DOMAIN, SERVICE_SEEK)
    hass.services.async_remove(DOMAIN, SERVICE_ADD_TO_QUEUE)
    hass.services.async_remove(DOMAIN, SERVICE_CLEAR_QUEUE)
    hass.services.async_remove(DOMAIN, SERVICE_NEXT_TRACK)
    hass.services.async_remove(DOMAIN, SERVICE_PREVIOUS_TRACK)
    hass.services.async_remove(DOMAIN, SERVICE_REMOVE_FROM_QUEUE)
    hass.services.async_remove(DOMAIN, SERVICE_SET_REPEAT)
    hass.services.async_remove(DOMAIN, SERVICE_SET_SHUFFLE)
    hass.services.async_remove(DOMAIN, SERVICE_GET_QUEUE)
    hass.data[DOMAIN].pop(entry.entry_id)
    return True
