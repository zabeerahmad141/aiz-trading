"""Small persistent cache for the latest real market snapshots."""
import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any


_CACHE_PATH = Path(os.getenv("MARKET_DATA_CACHE_PATH", "/app/data/market_data_cache.json"))
_CACHE_LOCK = threading.Lock()


def _read() -> dict[str, Any]:
    try:
        return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _write(data: dict[str, Any]) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_path = tempfile.mkstemp(dir=_CACHE_PATH.parent, prefix="market-cache-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, separators=(",", ":"))
        os.replace(temporary_path, _CACHE_PATH)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


def get_snapshot(kind: str, key: str) -> Any:
    with _CACHE_LOCK:
        return _read().get(kind, {}).get(key)


def set_snapshot(kind: str, key: str, value: Any) -> None:
    with _CACHE_LOCK:
        data = _read()
        data.setdefault(kind, {})[key] = value
        _write(data)
