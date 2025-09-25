# tests/test_price_loader_json.py
import json
import os
import pytest

# Price loader (reads JSON file)
from app.price_loader import load_price_table_from_json

# Auto loader + tracker/budget come from cost_cap
from app.cost_cap import load_price_table_auto, CostTracker, Budget, CostCapExceeded


def test_load_price_table_from_json_basic_and_aliases(tmp_path, monkeypatch):
    """
    Ensures the JSON loader reads records, applies aliases, and returns
    a dict of model -> (input_per_1k, output_per_1k) in lowercase keys.
    """
    data = [
        {
            "provider": "openai",
            "model": "gpt-4o",
            "input_per_1k_usd": 0.005,
            "output_per_1k_usd": 0.015,
            "active": True,
            "aliases": ["gpt4o"]
        },
        {
            "provider": "anthropic",
            "model": "claude-3-5-sonnet",
            "input_per_1k_usd": 0.003,
            "output_per_1k_usd": 0.015,
            "active": True
        }
    ]
    p = tmp_path / "prices.json"
    p.write_text(json.dumps(data), encoding="utf-8")

    # Point loader to our temp file
    monkeypatch.setenv("PRICE_REGISTRY_PATH", str(p))

    table = load_price_table_from_json()

    assert table["gpt-4o"] == (0.005, 0.015)
    # alias should map to same tuple
    assert table["gpt4o"] == (0.005, 0.015)
    assert table["claude-3-5-sonnet"] == (0.003, 0.015)


def test_load_price_table_from_json_ignores_inactive_and_malformed(tmp_path, monkeypatch):
    """
    Inactive entries and malformed rows should be skipped (not crash the app).
    """
    data = [
        {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "input_per_1k_usd": 0.002,
            "output_per_1k_usd": 0.006,
            "active": False  # should be ignored
        },
        {
            "provider": "misc",
            "model": "broken-model",
            # missing prices -> malformed -> should be ignored
        },
        {
            "provider": "anthropic",
            "model": "claude-3-haiku",
            "input_per_1k_usd": 0.001,
            "output_per_1k_usd": 0.005,
            "active": True
        }
    ]
    p = tmp_path / "prices.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setenv("PRICE_REGISTRY_PATH", str(p))

    table = load_price_table_from_json()

    assert "gpt-4o-mini" not in table   # inactive ignored
    assert "broken-model" not in table  # malformed ignored
    assert table["claude-3-haiku"] == (0.001, 0.005)


def test_load_price_table_auto_falls_back_to_env_when_json_missing(tmp_path, monkeypatch):
    """
    If JSON file is missing/unreadable, the auto loader should fall back to ENV prices.
    """
    # Point to a non-existent file to force JSON failure
    monkeypatch.setenv("PRICE_REGISTRY_PATH", str(tmp_path / "missing.json"))

    # Provide env-based prices as fallback
    monkeypatch.setenv("PRICE__GPT4O__INPUT", "0.005")
    monkeypatch.setenv("PRICE__GPT4O__OUTPUT", "0.015")

    table = load_price_table_auto()
    # env loader lowercases keys; we used GPT4O in variable name
    assert table["gpt4o"] == (0.005, 0.015)


def test_cost_tracker_enforces_cap_in_strict_mode(monkeypatch):
    """
    When the attempted total meets/exceeds cap in strict mode, raise CostCapExceeded.
    """
    budget = Budget(cap_usd=0.006, warn_threshold_pct=0.8, enforce_mode="strict")
    price_table = {"gpt4o": (0.005, 0.015)}  # per 1K tokens
    tracker = CostTracker(budget, price_table)

    # 2k prompt tokens at $0.005/1k => $0.010, which exceeds the $0.006 cap
    with pytest.raises(CostCapExceeded):
        tracker.add_usage("gpt4o", prompt_tokens=2000, completion_tokens=0)


def test_cost_tracker_soft_mode_does_not_block(monkeypatch):
    """
    In soft mode, going over the cap should NOT raise, but total should accumulate.
    """
    budget = Budget(cap_usd=0.006, warn_threshold_pct=0.8, enforce_mode="soft")
    price_table = {"gpt4o": (0.005, 0.015)}
    tracker = CostTracker(budget, price_table)

    total = tracker.add_usage("gpt4o", prompt_tokens=2000, completion_tokens=0)  # $0.010
    assert total >= 0.010  # no exception in soft mode


def test_cost_tracker_unknown_model_behavior_strict_and_lenient(tmp_path, monkeypatch):
    """
    If PRICE_STRICT=1, unknown models raise KeyError.
    If PRICE_STRICT=0 (default), unknown models are treated as $0.00.
    """
    price_table = {}  # deliberately empty
    budget = Budget(cap_usd=1.0)

    # Strict
    monkeypatch.setenv("PRICE_STRICT", "1")
    tracker_strict = CostTracker(budget, price_table)
    with pytest.raises(KeyError):
        tracker_strict.add_usage("unknown-model", prompt_tokens=1000, completion_tokens=0)

    # Lenient (unset means 0 by default, but we set explicitly)
    monkeypatch.setenv("PRICE_STRICT", "0")
    tracker_lenient = CostTracker(budget, price_table)
    total = tracker_lenient.add_usage("unknown-model", prompt_tokens=1000, completion_tokens=0)
    assert total == 0.0  # treated as free in lenient mode
