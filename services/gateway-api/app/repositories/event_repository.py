"""Event persistence adapter."""

from copy import deepcopy
from threading import RLock


class EventRepository:
    def __init__(self):
        self._items = []
        self._lock = RLock()

    def list(self):
        with self._lock:
            return deepcopy(self._items)

    def add(self, record: dict):
        with self._lock:
            stored_record = deepcopy(record)
            self._items.insert(0, stored_record)
            return deepcopy(stored_record)
