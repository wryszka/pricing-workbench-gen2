"""Cache layer for AI/agent responses.

Two modes, toggled via `/api/admin/ai-mode`:

  - `live`: always call the real serving endpoint.
  - `cached`: try the on-disk cache first; on miss, call live and write
    the response back so a follow-up hit lands fast and identical (default).

Cache is keyed by a stable hash of `(endpoint, question, custom_inputs)`
and persisted to a UC Volume so it survives app restarts and is shared
across replicas. Reads AND writes go through the Databricks SDK Files API
(the app container has no /Volumes FUSE mount), so the app SP needs
WRITE VOLUME on `governance_packs` — granted by 00_setup/grant_app_sp.py.

The mode flag is held both in-process (for hot reads) and in a tiny
sidecar file on the volume (so a freshly-started replica picks it up).
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import threading
from typing import Any

from server.config import get_catalog, get_schema, get_workspace_client

logger = logging.getLogger(__name__)

VOL_DIR    = "/Volumes/{catalog}/{schema}/governance_packs"
CACHE_FILE = "ai_response_cache.json"
MODE_FILE  = "ai_response_mode.txt"

_VALID_MODES = {"live", "cached"}
# Default to `cached` so demo cadence (consistent + instant) is the
# baseline. Operators flip to `live` when they want to demonstrate the
# real round-trip, and that choice persists to the volume so the next
# app restart picks it back up. `AI_RESPONSE_MODE` env var still wins
# if explicitly set.
_DEFAULT_MODE = os.environ.get("AI_RESPONSE_MODE", "cached").strip().lower()
if _DEFAULT_MODE not in _VALID_MODES:
    _DEFAULT_MODE = "cached"

_lock = threading.RLock()
_mode_cache: str | None = None
_response_cache: dict[str, Any] | None = None
# Last persist failure (None = last write succeeded or nothing written yet).
# Surfaced by /api/admin/ai-mode so a missing WRITE VOLUME grant is visible
# instead of silently degrading the cache to per-process memory.
_last_write_error: str | None = None


def _vol_path() -> str:
    return VOL_DIR.format(catalog=get_catalog(), schema=get_schema())



def _vol_write(path: str, data: bytes) -> None:
    """Upload bytes to a UC Volume path via the SDK Files API.

    The FUSE mount under /Volumes/... is read-only for new files (open()
    in write mode fails with ENOENT even when the directory exists), so
    we route writes through `w.files.upload` which talks to the metastore."""
    w = get_workspace_client()
    w.files.upload(file_path=path, contents=io.BytesIO(data), overwrite=True)


def _vol_read(path: str) -> bytes | None:
    """Read a UC Volume file via the SDK Files API (the app container has no
    /Volumes FUSE mount, so open() never sees persisted files). Returns None
    when the file doesn't exist yet."""
    from databricks.sdk.errors import NotFound
    try:
        resp = get_workspace_client().files.download(file_path=path)
    except NotFound:
        return None
    return resp.contents.read()


def _load_responses() -> dict[str, Any]:
    global _response_cache
    if _response_cache is not None:
        return _response_cache
    path = f"{_vol_path()}/{CACHE_FILE}"
    try:
        raw = _vol_read(path)
        _response_cache = json.loads(raw) if raw else {}
    except Exception as e:
        logger.warning("ai_cache: could not load %s — starting empty: %s", path, e)
        _response_cache = {}
    return _response_cache


def _save_responses() -> None:
    global _last_write_error
    if _response_cache is None:
        return
    path = f"{_vol_path()}/{CACHE_FILE}"
    try:
        payload = json.dumps(_response_cache, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        _vol_write(path, payload)
        _last_write_error = None
    except Exception as e:
        _last_write_error = f"{type(e).__name__}: {str(e)[:300]}"
        logger.error("ai_cache: could not persist cache to %s (app SP needs WRITE VOLUME): %s", path, e)


def _load_mode() -> str:
    global _mode_cache
    if _mode_cache is not None:
        return _mode_cache
    path = f"{_vol_path()}/{MODE_FILE}"
    try:
        raw = _vol_read(path)
        m = raw.decode("utf-8").strip().lower() if raw else ""
        _mode_cache = m if m in _VALID_MODES else _DEFAULT_MODE
    except Exception as e:
        logger.warning("ai_cache: could not read mode file — defaulting to %s: %s",
                       _DEFAULT_MODE, e)
        _mode_cache = _DEFAULT_MODE
    return _mode_cache


def _persist_mode(mode: str) -> None:
    global _last_write_error
    path = f"{_vol_path()}/{MODE_FILE}"
    try:
        _vol_write(path, mode.encode("utf-8"))
        _last_write_error = None
    except Exception as e:
        _last_write_error = f"{type(e).__name__}: {str(e)[:300]}"
        logger.error("ai_cache: could not persist mode to %s (app SP needs WRITE VOLUME): %s", path, e)


def persistence_status() -> dict:
    """Whether the cache is actually reaching the volume — for /api/admin/ai-mode."""
    return {"persisted": _last_write_error is None, "last_write_error": _last_write_error,
            "path": f"{_vol_path()}/{CACHE_FILE}"}


def get_mode() -> str:
    with _lock:
        return _load_mode()


def set_mode(mode: str) -> str:
    mode = (mode or "").strip().lower()
    if mode not in _VALID_MODES:
        raise ValueError(f"mode must be one of {sorted(_VALID_MODES)}, got {mode!r}")
    with _lock:
        global _mode_cache
        _mode_cache = mode
        _persist_mode(mode)
        return mode


def _stable_dict(d: Any) -> Any:
    """Recursively sort dict keys so the JSON dump is canonical."""
    if isinstance(d, dict):
        return {k: _stable_dict(d[k]) for k in sorted(d)}
    if isinstance(d, list):
        return [_stable_dict(x) for x in d]
    return d


def cache_key(endpoint: str, question: str, custom_inputs: dict | None) -> str:
    payload = {
        "endpoint":      endpoint,
        "question":      question.strip(),
        "custom_inputs": _stable_dict(custom_inputs or {}),
    }
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def get_cached(key: str) -> dict | None:
    with _lock:
        entry = _load_responses().get(key)
        if not entry:
            return None
        # Return a deep-ish copy so callers mutating the result don't poison cache.
        return json.loads(json.dumps(entry["response"]))


def put_cached(key: str, response: dict,
               endpoint: str, question: str, custom_inputs: dict | None) -> None:
    with _lock:
        cache = _load_responses()
        cache[key] = {
            "endpoint":      endpoint,
            "question":      question,
            "custom_inputs": custom_inputs or {},
            "response":      response,
        }
        _save_responses()


def list_entries() -> list[dict]:
    with _lock:
        cache = _load_responses()
        return [
            {
                "key":      k,
                "endpoint": v.get("endpoint"),
                "persona":  (v.get("custom_inputs") or {}).get("persona"),
                "question": (v.get("question") or "")[:120],
            }
            for k, v in cache.items()
        ]


def clear_cache() -> int:
    with _lock:
        cache = _load_responses()
        n = len(cache)
        cache.clear()
        _save_responses()
        return n
