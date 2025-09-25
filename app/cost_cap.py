"""
cost_cap.py
-----------
Purpose: Give each request/run a dollar *budget* for calling LLMs/tools.
Track usage (tokens) -> convert to dollars using a price table -> stop
when the *cap* would be exceeded.

Key ideas:
- Budget (cap, warning threshold, enforce mode)
- Price table (model -> (input_per_1k, output_per_1k)) loaded from JSON (preferred)
  with ENV fallback so the app still runs if JSON is missing.
- CostTracker (adds up dollars as you report usage)

Tracker per request/run via `executor_guard.cost_guard()`,
then call `tracker.add_usage(model, prompt_tokens, completion_tokens)` after each LLM call.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple, Optional
import os


# --- Exception ---------------------------------------------------------------

class CostCapExceeded(RuntimeError):
    """
    Raised when a run *would* spend more than the configured dollar cap.
    Attach 'attempted' (the total *after* adding a new charge) and 'cap'.
    """
    def __init__(self, attempted: float, cap: float, detail: str = ""):
        super().__init__(f"Cost cap exceeded: attempted ${attempted:.4f} > cap ${cap:.4f}. {detail}")
        self.attempted = attempted
        self.cap = cap
        self.detail = detail


# --- Budget model ------------------------------------------------------------

@dataclass
class Budget:
    """
    Holds the money limits and behavior:

    - cap_usd:           Max dollars allowed for *this* run/request.
                         Use 0.0 to disable enforcement (no cap).
    - warn_threshold_pct:When total >= cap * this %, you can warn (e.g., 0.8 = 80%).
    - enforce_mode:      "strict" = raise error at/over cap.
                         "soft"   = never raise; only track and let it pass.
    """
    cap_usd: float
    warn_threshold_pct: float = 0.8
    enforce_mode: str = "strict"


def _env_float(name: str, default: float) -> float:
    """Read a float from env, falling back to default if missing/blank."""
    value = os.environ.get(name)
    return float(value) if value not in (None, "") else default


def load_budget_from_env() -> Budget:
    """
    Build a Budget from environment variables so you can change limits without code changes.

    .env examples:
      COST_CAP_USD=0.50
      COST_WARN_THRESHOLD_PCT=0.80
      COST_ENFORCE=strict      # or "soft"
    """
    return Budget(
        cap_usd=_env_float("COST_CAP_USD", 0.0),
        warn_threshold_pct=_env_float("COST_WARN_THRESHOLD_PCT", 0.8),
        enforce_mode=os.environ.get("COST_ENFORCE", "strict").lower(),
    )


# --- Price table loaders -----------------------------------------------------
# Preferred: JSON file
# Fallback: environment variables (PRICE__MODEL__INPUT/OUTPUT)

def load_price_table_from_env() -> Dict[str, Tuple[float, float]]:
    """
    Read model prices from environment variables.
    Format:
      PRICE__GPT4O__INPUT=0.005
      PRICE__GPT4O__OUTPUT=0.015

    Returns a dict: {"gpt4o": (0.005, 0.015), ...}
    """
    table: Dict[str, Tuple[float, float]] = {}
    for k, v in os.environ.items():
        if k.startswith("PRICE__") and k.endswith("__INPUT"):
            model_key = k[len("PRICE__"):-len("__INPUT")]  # e.g. 'GPT4O'
            model_lc = model_key.lower()
            in_price = float(v)
            out_price = float(os.environ.get(f"PRICE__{model_key}__OUTPUT", "0") or 0)
            table[model_lc] = (in_price, out_price)
    return table


def load_price_table_auto() -> Dict[str, Tuple[float, float]]:
    """
    Try JSON registry first; if that fails, fall back to env vars.
    This keeps local dev resilient if the JSON file is missing or malformed.

    .env example to point at JSON:
      PRICE_REGISTRY_PATH=config/model_prices.json
    """
    # Local import to avoid hard dependency if you only want env prices.
    try:
        from app.price_loader import load_price_table_from_json
        return load_price_table_from_json()  # has caching + alias handling
    except Exception:
        # Fallback so the app still boots
        return load_price_table_from_env()


# If set to "1", unknown models will raise an error instead of being treated as free ($0.00).
PRICE_STRICT: bool = os.environ.get("PRICE_STRICT", "0") == "1"


# --- Cost tracker ------------------------------------------------------------

class CostTracker:
    """
    Tracks how much this run/request has 'spent' so far.
    You call add_usage(...) after each LLM/tool call.

    Math:
      dollars = (prompt_tokens / 1000) * input_price_per_1k
              + (completion_tokens / 1000) * output_price_per_1k
    """
    def __init__(self, budget: Budget, price_table: Optional[Dict[str, Tuple[float, float]]] = None):
        self.budget = budget
        # Price table maps model name -> (input_per_1k, output_per_1k)
        # If not provided, load from JSON (preferred) or env fallback.
        self.price_table: Dict[str, Tuple[float, float]] = price_table or load_price_table_auto()
        self.total_usd: float = 0.0  # running total for this run/request

    def add_usage(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Add a charge for one LLM/tool call.

        model: string name (we look it up lowercased in the price table)
        prompt_tokens:    tokens sent to the model (a.k.a. input)
        completion_tokens:tokens generated by the model (a.k.a. output)

        Returns the *new* running total after adding this charge.
        Might raise CostCapExceeded if this would cross the cap and enforce_mode is 'strict'.
        """
        key = (model or "").lower()

        # Look up model pricing
        if key in self.price_table:
            per_in, per_out = self.price_table[key]
        else:
            if PRICE_STRICT:
                # Strict mode = fail fast if a model isn't priced
                raise KeyError(f"Model '{model}' not found in price registry")
            # Lenient mode = treat unknown models as free to avoid blocking dev
            per_in, per_out = (0.0, 0.0)

        # Convert tokens -> dollars (per 1K tokens)
        cost = (prompt_tokens / 1000.0) * per_in + (completion_tokens / 1000.0) * per_out

        # Add to running total and enforce cap if needed
        context = f"model={model}, prompt={prompt_tokens}, completion={completion_tokens}"
        return self._add_cost(cost, context)

    def add_cost_dollars(self, usd: float, context: str = "") -> float:
        """
        Convenience: directly add a dollar amount (useful for tools billed per-call).
        Example: a retrieval API that costs $0.002 per query, regardless of tokens.
        """
        return self._add_cost(float(usd), context)

    def _add_cost(self, delta: float, context: str) -> float:
        """
        Core guard logic:
        - Calculate what the total *would be* after adding 'delta'
        - If a cap is configured and enforce_mode is 'strict', raise at attempted >= cap
        - Otherwise, commit the new total
        """
        attempted = self.total_usd + float(delta)
        cap = self.budget.cap_usd

        # Only enforce if a positive cap is set (0 = disabled)
        if cap > 0:
            # We choose a simple policy: block when attempted >= cap
            if attempted >= cap and self.budget.enforce_mode == "strict":
                raise CostCapExceeded(attempted=attempted, cap=cap, detail=context)

        # Commit new total
        self.total_usd = attempted
        return self.total_usd

    def near_threshold(self) -> bool:
        """
        Returns True if we've reached the warning threshold (e.g., >= 80% of cap).
        Useful for emitting a header, log, or trace attribute to warn callers/UI.
        """
        return (self.budget.cap_usd > 0) and (
            self.total_usd >= (self.budget.cap_usd * self.budget.warn_threshold_pct)
        )
