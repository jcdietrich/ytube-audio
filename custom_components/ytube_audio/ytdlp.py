"""yt-dlp processor for extracting audio URLs."""
from __future__ import annotations

import logging
import os
import tempfile
from typing import Any

from homeassistant.core import HomeAssistant

from .const import AUDIO_FORMATS, DEFAULT_FORMAT, FORMAT_MP3

_LOGGER = logging.getLogger(__name__)


class YtDlpProcessor:
    """Process YouTube URLs using yt-dlp to extract audio streams."""

    def __init__(self, hass: HomeAssistant, cache_dir: str) -> None:
        """Initialize the yt-dlp processor."""
        self.hass = hass
        self.cache_dir = cache_dir

    async def extract_audio_url(
        self, url: str, audio_format: str = DEFAULT_FORMAT
    ) -> tuple[str | None, str | None]:
        """Extract the audio URL from a YouTube video.
        
        Args:
            url: YouTube video URL or video ID
            audio_format: Desired format (best, m4a, mp3, opus)
            
        Returns:
            Tuple of (audio_url, content_type) or (None, None) if extraction fails
        """
        return await self.hass.async_add_executor_job(
            self._extract_audio_url_sync, url, audio_format
        )

    def _extract_audio_url_sync(
        self, url: str, audio_format: str = DEFAULT_FORMAT
    ) -> tuple[str | None, str | None]:
        """Synchronous extraction of audio URL."""
        try:
            import yt_dlp
        except ImportError:
            _LOGGER.error("yt-dlp is not installed. Please install it with: pip install yt-dlp")
            return None, None

        format_spec = AUDIO_FORMATS.get(audio_format, AUDIO_FORMATS[DEFAULT_FORMAT])
        
        ydl_opts = {
            "format": format_spec,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "cachedir": self.cache_dir,
            "noplaylist": True,
        }

        if audio_format == FORMAT_MP3:
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                _LOGGER.debug("Extracting info for URL: %s (format: %s)", url, audio_format)
                info = ydl.extract_info(url, download=False)
                
                if info is None:
                    _LOGGER.error("No info extracted for URL: %s", url)
                    return None, None

                audio_url = None
                content_type = None

                if "url" in info:
                    audio_url = info["url"]
                    content_type = self._get_content_type(info)
                elif "formats" in info:
                    selected_format = self._select_format(info["formats"], audio_format)
                    if selected_format:
                        audio_url = selected_format.get("url")
                        content_type = self._get_content_type(selected_format)

                if audio_url:
                    _LOGGER.debug("Extracted URL with content_type: %s", content_type)
                    return audio_url, content_type

                _LOGGER.error("Could not find audio URL in extracted info")
                return None, None

        except Exception as err:
            _LOGGER.error("Error extracting audio URL: %s", err)
            return None, None

    def _select_format(self, formats: list, audio_format: str) -> dict | None:
        """Select the best matching format from available formats."""
        audio_only = [
            f for f in formats
            if f.get("acodec") != "none" and f.get("vcodec") == "none"
        ]
        
        if not audio_only:
            return formats[-1] if formats else None

        if audio_format == "m4a":
            m4a_formats = [f for f in audio_only if f.get("ext") == "m4a"]
            if m4a_formats:
                return max(m4a_formats, key=lambda f: f.get("abr", 0) or 0)
        
        elif audio_format == "opus":
            opus_formats = [f for f in audio_only if f.get("acodec", "").startswith("opus")]
            if opus_formats:
                return max(opus_formats, key=lambda f: f.get("abr", 0) or 0)

        return max(audio_only, key=lambda f: f.get("abr", 0) or 0)

    def _get_content_type(self, format_info: dict) -> str:
        """Determine content type from format info."""
        ext = format_info.get("ext", "")
        acodec = format_info.get("acodec", "")
        
        if ext == "m4a" or acodec.startswith("mp4a"):
            return "audio/mp4"
        elif ext == "webm" or acodec.startswith("opus"):
            return "audio/webm"
        elif ext == "mp3":
            return "audio/mpeg"
        else:
            return "audio/webm"

    async def get_video_info(self, url: str) -> dict[str, Any] | None:
        """Get video metadata without extracting stream URL.
        
        Args:
            url: YouTube video URL or video ID
            
        Returns:
            Dictionary with video info or None if extraction fails
        """
        return await self.hass.async_add_executor_job(
            self._get_video_info_sync, url
        )

    def _get_video_info_sync(self, url: str) -> dict[str, Any] | None:
        """Synchronous extraction of video info."""
        try:
            import yt_dlp
        except ImportError:
            _LOGGER.error("yt-dlp is not installed")
            return None

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "noplaylist": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if info is None:
                    return None

                return {
                    "title": info.get("title"),
                    "duration": info.get("duration"),
                    "thumbnail": info.get("thumbnail"),
                    "uploader": info.get("uploader"),
                    "view_count": info.get("view_count"),
                }

        except Exception as err:
            _LOGGER.error("Error getting video info: %s", err)
            return None

    async def extract_playlist(self, url: str) -> list[dict[str, Any]]:
        """Extract all items from a playlist URL.
        
        Args:
            url: Playlist URL (YouTube, SoundCloud, etc.)
            
        Returns:
            List of dicts with url, title, duration, thumbnail for each item
        """
        return await self.hass.async_add_executor_job(
            self._extract_playlist_sync, url
        )

    def _extract_playlist_sync(self, url: str) -> list[dict[str, Any]]:
        """Synchronous extraction of playlist items."""
        try:
            import yt_dlp
        except ImportError:
            _LOGGER.error("yt-dlp is not installed")
            return []

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "noplaylist": False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                _LOGGER.debug("Extracting playlist: %s", url)
                info = ydl.extract_info(url, download=False)
                
                if info is None:
                    _LOGGER.error("No info extracted for playlist: %s", url)
                    return []

                entries = info.get("entries", [])
                
                if not entries:
                    if info.get("url") or info.get("id"):
                        return [{
                            "url": info.get("webpage_url") or info.get("url") or url,
                            "title": info.get("title"),
                            "duration": info.get("duration"),
                            "thumbnail": info.get("thumbnail"),
                        }]
                    return []

                items = []
                for entry in entries:
                    if entry is None:
                        continue
                    
                    item_url = entry.get("webpage_url") or entry.get("url")
                    if not item_url and entry.get("id"):
                        item_url = f"https://www.youtube.com/watch?v={entry['id']}"
                    
                    if item_url:
                        items.append({
                            "url": item_url,
                            "title": entry.get("title"),
                            "duration": entry.get("duration"),
                            "thumbnail": entry.get("thumbnail"),
                        })

                _LOGGER.debug("Extracted %d items from playlist", len(items))
                return items

        except Exception as err:
            _LOGGER.error("Error extracting playlist: %s", err)
            return []

    async def is_playlist(self, url: str) -> bool:
        """Check if a URL is a playlist.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL is a playlist, False otherwise
        """
        return await self.hass.async_add_executor_job(
            self._is_playlist_sync, url
        )

    def _is_playlist_sync(self, url: str) -> bool:
        """Synchronous check if URL is a playlist."""
        try:
            import yt_dlp
        except ImportError:
            return False

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "noplaylist": False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False, process=False)
                
                if info is None:
                    return False

                if info.get("_type") == "playlist":
                    return True
                
                if "entries" in info:
                    return True
                
                if "list" in url.lower() or "playlist" in url.lower():
                    return True

                return False

        except Exception:
            return False
