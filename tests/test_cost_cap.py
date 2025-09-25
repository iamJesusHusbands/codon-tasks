import os
from app.cost_cap import CostTracker, Budget

def test_allows_under_cap(monkeypatch):
    monkeypatch.setenv("COST_CAP_USD", "0.02")
    tracker = CostTracker(Budget(0.02, 0.8, "strict"), {"gpt4o": (0.005, 0.015)})
    total = tracker.add_usage("gpt4o", prompt_tokens=1000, completion_tokens=0)  # $0.005
    assert total < 0.02

def test_blocks_over_cap(monkeypatch):
    monkeypatch.setenv("COST_CAP_USD", "0.006")
    tracker = CostTracker(Budget(0.006, 0.8, "strict"), {"gpt4o": (0.005, 0.015)})
    try:
        tracker.add_usage("gpt4o", prompt_tokens=2000, completion_tokens=0)  # $0.010
        assert False, "should have raised"
    except Exception as e:
        assert "Cost cap exceeded" in str(e)
