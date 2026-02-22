"""Queue management for ytube-audio."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

_LOGGER = logging.getLogger(__name__)


@dataclass
class QueueItem:
    """Represents an item in the playback queue."""
    
    url: str
    title: str | None = None
    thumbnail: str | None = None
    duration: int | None = None


@dataclass
class PlayerQueue:
    """Queue for a specific media player."""
    
    items: list[QueueItem] = field(default_factory=list)
    current_index: int = -1
    repeat: bool = False
    shuffle: bool = False
    
    @property
    def current_item(self) -> QueueItem | None:
        """Get the current queue item."""
        if 0 <= self.current_index < len(self.items):
            return self.items[self.current_index]
        return None
    
    @property
    def next_item(self) -> QueueItem | None:
        """Get the next queue item."""
        next_idx = self.current_index + 1
        if next_idx < len(self.items):
            return self.items[next_idx]
        if self.repeat and self.items:
            return self.items[0]
        return None
    
    @property
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self.items) == 0


class QueueManager:
    """Manage playback queues for media players."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the queue manager."""
        self.hass = hass
        self._queues: dict[str, PlayerQueue] = {}
        self._unsubscribe_callbacks: dict[str, Any] = {}
        self._play_callback: Any = None

    def _fire_queue_updated(self, entity_id: str) -> None:
        """Fire an event when queue is updated."""
        self.hass.bus.async_fire(
            "ytube_audio_queue_updated",
            {"entity_id": entity_id, **self.get_queue_info(entity_id)}
        )

    def set_play_callback(self, callback: Any) -> None:
        """Set the callback function to play a URL."""
        self._play_callback = callback

    def get_queue(self, entity_id: str) -> PlayerQueue:
        """Get or create a queue for a media player."""
        if entity_id not in self._queues:
            self._queues[entity_id] = PlayerQueue()
            self._setup_state_listener(entity_id)
        return self._queues[entity_id]

    def _setup_state_listener(self, entity_id: str) -> None:
        """Set up state change listener for auto-advance."""
        @callback
        def state_changed(event):
            """Handle media player state changes."""
            new_state = event.data.get("new_state")
            old_state = event.data.get("old_state")
            
            if new_state is None:
                return

            if (
                old_state is not None
                and old_state.state == "playing"
                and new_state.state == "idle"
            ):
                asyncio.create_task(self._handle_playback_ended(entity_id))

        self._unsubscribe_callbacks[entity_id] = async_track_state_change_event(
            self.hass, [entity_id], state_changed
        )

    async def _handle_playback_ended(self, entity_id: str) -> None:
        """Handle when playback ends - play next in queue."""
        queue = self.get_queue(entity_id)
        
        if queue.next_item is None:
            _LOGGER.debug("Queue ended for %s", entity_id)
            return

        if queue.repeat and queue.current_index >= len(queue.items) - 1:
            queue.current_index = 0
        else:
            queue.current_index += 1

        next_item = queue.current_item
        if next_item and self._play_callback:
            _LOGGER.debug("Auto-playing next: %s on %s", next_item.url, entity_id)
            await self._play_callback(next_item.url, entity_id)

    async def add_to_queue(
        self,
        entity_id: str,
        url: str,
        title: str | None = None,
        play_now: bool = False,
    ) -> int:
        """Add an item to the queue.
        
        Returns the position in the queue.
        """
        queue = self.get_queue(entity_id)
        item = QueueItem(url=url, title=title)
        queue.items.append(item)
        position = len(queue.items) - 1
        
        _LOGGER.debug("Added to queue[%d]: %s for %s", position, url, entity_id)

        if play_now or queue.current_index == -1:
            queue.current_index = position
            if self._play_callback:
                await self._play_callback(url, entity_id)

        self._fire_queue_updated(entity_id)
        return position

    async def play_next(self, entity_id: str) -> bool:
        """Skip to the next item in the queue."""
        queue = self.get_queue(entity_id)
        
        if queue.next_item is None:
            return False

        if queue.repeat and queue.current_index >= len(queue.items) - 1:
            queue.current_index = 0
        else:
            queue.current_index += 1

        item = queue.current_item
        if item and self._play_callback:
            await self._play_callback(item.url, entity_id)
            self._fire_queue_updated(entity_id)
            return True
        return False

    async def play_previous(self, entity_id: str) -> bool:
        """Go back to the previous item in the queue."""
        queue = self.get_queue(entity_id)
        
        if queue.current_index <= 0:
            if queue.repeat and queue.items:
                queue.current_index = len(queue.items) - 1
            else:
                return False
        else:
            queue.current_index -= 1

        item = queue.current_item
        if item and self._play_callback:
            await self._play_callback(item.url, entity_id)
            self._fire_queue_updated(entity_id)
            return True
        return False

    async def play_index(self, entity_id: str, index: int) -> bool:
        """Play a specific index in the queue."""
        queue = self.get_queue(entity_id)
        
        if not 0 <= index < len(queue.items):
            return False

        queue.current_index = index
        item = queue.current_item
        if item and self._play_callback:
            await self._play_callback(item.url, entity_id)
            return True
        return False

    def clear_queue(self, entity_id: str) -> None:
        """Clear the queue for a media player."""
        if entity_id in self._queues:
            self._queues[entity_id] = PlayerQueue()
        _LOGGER.debug("Cleared queue for %s", entity_id)
        self._fire_queue_updated(entity_id)

    def remove_from_queue(self, entity_id: str, index: int) -> bool:
        """Remove an item from the queue by index."""
        queue = self.get_queue(entity_id)
        
        if not 0 <= index < len(queue.items):
            return False

        queue.items.pop(index)
        
        if index < queue.current_index:
            queue.current_index -= 1
        elif index == queue.current_index:
            queue.current_index = min(queue.current_index, len(queue.items) - 1)

        self._fire_queue_updated(entity_id)
        return True

    def set_repeat(self, entity_id: str, repeat: bool) -> None:
        """Set repeat mode for a queue."""
        queue = self.get_queue(entity_id)
        queue.repeat = repeat
        self._fire_queue_updated(entity_id)

    def set_shuffle(self, entity_id: str, shuffle: bool) -> None:
        """Set shuffle mode for a queue."""
        queue = self.get_queue(entity_id)
        queue.shuffle = shuffle
        
        if shuffle and queue.items:
            import random
            current = queue.current_item
            remaining = [i for i in queue.items if i != current]
            random.shuffle(remaining)
            if current:
                queue.items = [current] + remaining
                queue.current_index = 0
        
        self._fire_queue_updated(entity_id)

    def get_queue_info(self, entity_id: str) -> dict[str, Any]:
        """Get queue information for a media player."""
        queue = self.get_queue(entity_id)
        return {
            "items": [
                {
                    "url": item.url,
                    "title": item.title,
                    "thumbnail": item.thumbnail,
                    "duration": item.duration,
                }
                for item in queue.items
            ],
            "current_index": queue.current_index,
            "current_item": {
                "url": queue.current_item.url,
                "title": queue.current_item.title,
            } if queue.current_item else None,
            "repeat": queue.repeat,
            "shuffle": queue.shuffle,
            "length": len(queue.items),
        }

    def cleanup(self) -> None:
        """Clean up listeners."""
        for unsub in self._unsubscribe_callbacks.values():
            unsub()
        self._unsubscribe_callbacks.clear()
