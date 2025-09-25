# app/price_loader.py
import json
import os
import time
from pathlib import Path
from typing import Dict, Tuple, Any, Iterable

# Simple TTL + mtime cache so we don't re-read on every request
_PRICE_CACHE: Dict[str, Tuple[float, float]] | None = None
_PRICE_CACHE_MTIME: float | None = None
_PRICE_CACHE_TTL_SECS = 300  # 5 minutes

def _normalize(name: str) -> str:
    return (name or "").strip().lower()

def _iter_records(blob: Any) -> Iterable[dict]:
    """
    Accepts either:
      - list of objects (recommended), or
      - object map: {"openai:gpt-4o": {...}, ...}
    Yields a normalized record dict.
    """
    if isinstance(blob, list):
        for rec in blob:
            if isinstance(rec, dict):
                yield rec
    elif isinstance(blob, dict):
        # convert "provider:model": {...} style into records
        for key, val in blob.items():
            if not isinstance(val, dict):
                continue
            provider, _, model = key.partition(":")
            rec = {"provider": provider, "model": model, **val}
            yield rec

def _record_active(rec: dict) -> bool:
    # Basic "active" filter; feel free to extend with effective_from/to
    if "active" in rec and not rec["active"]:
        return False
    # If you add date windows, check them here.
    return True

def _build_table(records: Iterable[dict]) -> Dict[str, Tuple[float, float]]:
    """
    Returns: {"gpt-4o": (input_per_1k, output_per_1k), "gpt4o": (... alias ...)}
    """
    table: Dict[str, Tuple[float, float]] = {}

    for rec in records:
        if not _record_active(rec):
            continue

        model = _normalize(rec.get("model", ""))
        if not model:
            continue

        try:
            in_price = float(rec["input_per_1k_usd"])
            out_price = float(rec["output_per_1k_usd"])
        except Exception:
            # Skip malformed rows rather than breaking the app
            continue

        table[model] = (in_price, out_price)

        # Map aliases to the same tuple
        aliases = rec.get("aliases") or []
        if isinstance(aliases, list):
            for alias in aliases:
                alias_key = _normalize(str(alias))
                if alias_key:
                    table[alias_key] = (in_price, out_price)

    return table

def load_price_table_from_json(path: str | Path | None = None) -> Dict[str, Tuple[float, float]]:
    """
    Load prices from a JSON file and cache by TTL + file mtime.
    Returns: {"<model-lower>": (input_per_1k, output_per_1k)}
    """
    global _PRICE_CACHE, _PRICE_CACHE_MTIME

    path = Path(path or os.environ.get("PRICE_REGISTRY_PATH", "config/model_prices.json"))
    if not path.exists():
        raise FileNotFoundError(f"Price registry not found at: {path}")

    # TTL check
    now = time.time()
    if _PRICE_CACHE is not None and _PRICE_CACHE_MTIME is not None:
        if (now - _PRICE_CACHE_MTIME) < _PRICE_CACHE_TTL_SECS:
            return _PRICE_CACHE

    # mtime check
    mtime = path.stat().st_mtime
    if _PRICE_CACHE is not None and _PRICE_CACHE_MTIME == mtime:
        return _PRICE_CACHE

    # (Re)load file
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    table = _build_table(_iter_records(data))

    # Update cache (we store file mtime, not 'now', for instant reload on file edit)
    _PRICE_CACHE = table
    _PRICE_CACHE_MTIME = mtime
    return table
