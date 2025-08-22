# tests/test_graph.py

# Import the compiled app from your graph.py.
from graph import app

def test_graph_compiles():
    """
    Goal: prove the graph compiled successfully and got a runnable app.
    If compilation had failed, importing `app` or calling its methods would error.
    """
    # Basic checks
    assert app is not None
    assert hasattr(app, "invoke")  # compiled graphs expose .invoke()


def test_state_evolves_single_call():
    """
    Goal: prove running the graph changes state.
    Node:
      - reads the last incoming message
      - appends a response "echo: <last>"
    Because your state reducer is `operator.add` on a List[str],
    LangGraph MERGES (concatenates) the lists.
    So after one call with ["hello"], we expect:
      ["hello", "echo: hello"]
    """
    cfg = {"configurable": {"thread_id": "t-single"}}
    final_state = app.invoke({"messages": ["hello"]}, config=cfg)

    # The final messages should contain the original input and the echo reply
    assert isinstance(final_state, dict)
    assert "messages" in final_state
    assert final_state["messages"] == ["hello", "echo: hello"]
    assert final_state["messages"][-1] == "echo: hello"


def test_state_persists_across_calls_same_thread():
    """
    Goal: prove the in-memory checkpointer keeps state when reusing the SAME thread_id.
    Sequence (same thread_id):
      1) invoke({"messages": ["hello"]})
         -> ["hello", "echo: hello"]
      2) invoke({"messages": ["world"]})
         Previous state is loaded and MERGED with new input:
         before node: ["hello", "echo: hello", "world"]
         node adds:   ["echo: world"]
         final:       ["hello", "echo: hello", "world", "echo: world"]
    """
    cfg = {"configurable": {"thread_id": "t-same"}}

    s1 = app.invoke({"messages": ["hello"]}, config=cfg)
    assert s1["messages"] == ["hello", "echo: hello"]

    s2 = app.invoke({"messages": ["world"]}, config=cfg)
    assert s2["messages"] == ["hello", "echo: hello", "world", "echo: world"]
    assert s2["messages"][-1] == "echo: world"


def test_state_is_isolated_across_threads():
    """
    Goal: prove different thread_ids have independent histories.
    Using a NEW thread_id should NOT bring over messages from another thread.
    First call in a new thread with ["hello"] should give exactly:
      ["hello", "echo: hello"]
    """
    cfg_other = {"configurable": {"thread_id": "t-other"}}
    s = app.invoke({"messages": ["hello"]}, config=cfg_other)
    assert s["messages"] == ["hello", "echo: hello"]
