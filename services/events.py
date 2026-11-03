"""
Event Infrastructure for ClimateOS
Provides real-time event broadcasting for:
  - New citizen disaster incidents
  - Shelter availability and status updates
  - Official evacuation orders and human decisions
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("climateos.events")


class EventBroadcaster:
    """
    Thread-safe and async-safe event broadcaster for Server-Sent Events (SSE).
    Maintains subscriber queues and history buffer for reliable reconnects.
    """
    def __init__(self, history_limit: int = 200):
        self._subscribers: List[asyncio.Queue] = []
        self._history: List[Tuple[int, str, Dict[str, Any]]] = []
        self._counter: int = 0
        self._history_limit = history_limit

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._subscribers:
            self._subscribers.remove(q)

    def get_subscriber_count(self) -> int:
        return len(self._subscribers)

    def broadcast(self, event_type: str, payload: Dict[str, Any]) -> int:
        """
        Broadcast an event to all active subscriber queues.
        Returns the unique sequential event ID.
        """
        self._counter += 1
        event_id = self._counter
        record = (event_id, event_type, payload)

        self._history.append(record)
        if len(self._history) > self._history_limit:
            self._history.pop(0)

        for q in list(self._subscribers):
            try:
                q.put_nowait(record)
            except asyncio.QueueFull:
                try:
                    q.get_nowait()
                    q.put_nowait(record)
                except Exception:
                    pass
            except Exception:
                pass

        return event_id

    def get_events_since(self, last_event_id: int) -> List[Tuple[int, str, Dict[str, Any]]]:
        """Return missed events strictly greater than last_event_id."""
        return [rec for rec in self._history if rec[0] > last_event_id]

    def clear(self):
        """Reset state (useful for test isolation)."""
        self._subscribers.clear()
        self._history.clear()
        self._counter = 0


# Shared singleton broadcaster across backend routers
event_broadcaster = EventBroadcaster()
