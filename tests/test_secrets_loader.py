import os
import pytest
from app.secrets_loader import EnvSecretsBackend, secrets

def test_env_backend_returns_value(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "abc123")
    backend = EnvSecretsBackend()
    assert backend.get("OPENAI_API_KEY") == "abc123"

def test_env_backend_missing_raises(monkeypatch):
    monkeypatch.delenv("MISSING_KEY", raising=False)
    backend = EnvSecretsBackend()
    with pytest.raises(KeyError):
        backend.get("MISSING_KEY")

def test_module_singleton_uses_env_backend_by_default(monkeypatch):
    monkeypatch.setenv("SECRETS_BACKEND", "env")
    monkeypatch.setenv("FOO", "bar")
    # The module-level 'secrets' was created at import time. In a larger suite, you
    # might reload the module to re-run the factory, but for this tiny test we'll
    # just call it assuming default 'env'.
    assert secrets.get("FOO") == "bar"
