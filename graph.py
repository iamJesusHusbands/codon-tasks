"""
Minimal LangGraph with a per-run cost budget:

- We keep the original "echo" node.
- We add a per-run CostTracker (budget) and pass it into the graph via state.
- The node simulates an LLM/tool call and reports usage to the tracker.
- If the run would exceed the cost cap, a CostCapExceeded error will be raised.

Run it:
    python graph.py
"""

from __future__ import annotations

import operator
from typing import Annotated, List, TypedDict, Any

# --- Telemetry: keeps your traces working as before ---
from app.telemetry import init_tracing
init_tracing()

# --- Cost-cap: new imports (per-thread/run budget) ---
# cost_guard() gives us a per-run CostTracker
from app.executor_guard import cost_guard
# If a run would overspend, this error is raised
from app.cost_cap import CostCapExceeded

# --- LangGraph core pieces ---
from langgraph.graph import StateGraph, END

# Different LangGraph versions expose the in-memory saver under slightly different names.
try:
    from langgraph.checkpoint import MemorySaver as InMemorySaver  # older versions
except Exception:
    try:
        from langgraph.checkpoint import InMemorySaver  # some versions expose directly
    except Exception:
        from langgraph.checkpoint.memory import MemorySaver as InMemorySaver  # newer path


# 1) Define the graph "state"
#    We mark "total=False" so keys are OPTIONAL (we can pass "tracker" only when we have one).
#    - messages: a list that accumulates with operator.add (LangGraph merges lists this way)
#    - tracker:  the per-run CostTracker we pass into the run; the node will use it
class EchoState(TypedDict, total=False):
    messages: Annotated[List[str], operator.add]
    tracker: Any   # we don't specify a strict type to keep it simple for beginners


# 2) Define a node (a function)
#    Nodes receive the current state and RETURN a partial state update.
#    Here we:
#      - Take the last incoming message and append an "echo: ..." response.
#      - (NEW) If a "tracker" is present, simulate that we called an LLM and report usage.
def echo_node(state: EchoState) -> dict:
    last = state["messages"][-1] if state.get("messages") else ""
    response = f"echo: {last}"

    # (NEW) If the run provided a CostTracker, "charge" it for this node's work.
    # In a real app, you'd call your LLM/tool, then read the provider's usage object
    # (prompt_tokens, completion_tokens, etc.) and pass those numbers below.
    tracker = state.get("tracker")
    if tracker is not None:
        # Simulate a small usage so you can test the cap easily.
        # Replace with REAL usage from your LLM client later:
        #   usage = llm_response.usage
        #   tracker.add_usage("gpt4o", usage.prompt_tokens, usage.completion_tokens)
        tracker.add_usage(model="gpt4o", prompt_tokens=200, completion_tokens=50)
        # NOTE: If this pushes the total cost >= cap, CostCapExceeded will be raised here
        # and the run will stop cleanly.

    # Return a partial update; LangGraph will merge this with the existing state
    return {"messages": [response]}


# 3) Build the graph (same as before)
graph = StateGraph(EchoState)
graph.add_node("echo", echo_node)
graph.set_entry_point("echo")
graph.add_edge("echo", END)

# 4) Compile with an in-memory checkpointer (same as before)
checkpointer = InMemorySaver()
app = graph.compile(checkpointer=checkpointer)


# 5) Demo: Run
#    We now wrap each run in a cost_guard() so it gets a per-run CostTracker,
#    and we pass that tracker into the initial state under the "tracker" key.
if __name__ == "__main__":
    cfg = {"configurable": {"thread_id": "demo-thread"}}

    # Each "with cost_guard()" gives ONE run its own budget & running total.
    # If your cap is tiny in .env, the exception below is a good sign—budget is working.
    try:
        with cost_guard() as tracker:
            # First user message
            result1 = app.invoke({"messages": ["hello"], "tracker": tracker}, config=cfg)
            print("First call result:", result1)

            # Second user message (same thread_id -> previous state is loaded)
            result2 = app.invoke({"messages": ["world"], "tracker": tracker}, config=cfg)
            print("Second call result:", result2)

        # You can also stream events with a fresh budget (new run)
        print("\nStreaming a single call:")
        with cost_guard() as tracker2:
            for event in app.stream({"messages": ["stream me"], "tracker": tracker2}, config=cfg):
                # event is a dict like {"echo": {"messages": [...]}} or {"__end__": {...}}
                print(event)

    except CostCapExceeded as e:
        # Friendly message if your small demo cap is hit
        print(f"\n⚠️ Cost cap hit: {e}")
        print("Increase COST_CAP_USD in your .env or reduce token usage to continue.")
