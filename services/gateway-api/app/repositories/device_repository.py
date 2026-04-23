"""Device persistence adapter."""

from copy import deepcopy
from threading import RLock


class DeviceRepository:
    def __init__(self):
        self._items = {}
        self._lock = RLock()

    def list(self):
        with self._lock:
            return deepcopy(list(self._items.values()))

    def get(self, device_id: str):
        with self._lock:
            record = self._items.get(device_id)
            return deepcopy(record) if record is not None else None

    def upsert(self, record: dict):
        with self._lock:
            stored_record = deepcopy(record)
            self._items[record["device_id"]] = stored_record
            return deepcopy(stored_record)
