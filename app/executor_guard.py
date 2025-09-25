from contextlib import contextmanager
from .cost_cap import CostTracker, load_budget_from_env, load_price_table_from_env

@contextmanager
def cost_guard():
    tracker = CostTracker(load_budget_from_env(), load_price_table_from_env())
    try:
        yield tracker
    finally:
        # place to emit logs/metrics about tracker.total_usd
        pass
