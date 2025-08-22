# tests/test_graph.py
import pytest
from graph import build_app

def test_graph_compiles():
    app = build_app()
    assert app is not None

    from graph import build_app

def test_state_evolves_once():
    app = build_app()
    initial = {"count": 0}
    final = app.invoke(initial)  # run the graph
    assert final["count"] == 1