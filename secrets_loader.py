# secrets_loader.py
"""
A tiny, pluggable secrets loader with 3 backends:
- Env (works today): read from process environment variables.
- Vault (stub): method signatures ready, raise NotImplementedError for now.
- AWS Secrets Manager (stub): signatures ready, raise NotImplementedError.

Usage from anywhere:
    from secrets_loader import secrets
    api_key = secrets.get("OPENAI_API_KEY")

Backend is selected via env var:
    SECRETS_BACKEND = "env" | "vault" | "aws-sm"
"""

from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional


# ---------- Base interface ----------

class SecretsBackend:
    """A minimal contract all backends must follow."""

    def get(self, key: str, *, version: Optional[str] = None) -> str:
        """
        Return the secret value for 'key'.
        """
        raise NotImplementedError


# ---------- Working backend: ENV ----------

@dataclass
class EnvSecretsBackend(SecretsBackend):
    """
    Reads secrets from environment variables.
    """

    def get(self, key: str, *, version: Optional[str] = None) -> str:
        value = os.getenv(key)
        if value is None or value == "":
            raise KeyError(f"Secret '{key}' is not set in environment")
        return value


# ---------- Stub backends to fill later ----------

@dataclass
class VaultSecretsBackend(SecretsBackend):
    """
    Stub for HashiCorp Vault.
    Later:
      - pip install hvac
      - auth with VAULT_TOKEN / method team uses
      - read from KV path (mount + path)
    """
    addr: str
    token: str
    kv_mount: str = "kv"
    kv_path: str = ""

    def get(self, key: str, *, version: Optional[str] = None) -> str:
        # TODO: real implementation using hvac
        # Pseudocode:
        # import hvac
        # client = hvac.Client(url=self.addr, token=self.token)
        # secret = client.secrets.kv.v2.read_secret_version(
        #     mount_point=self.kv_mount,
        #     path=self.kv_path,
        #     version=int(version) if version else None,
        # )
        # return secret["data"]["data"][key]
        raise NotImplementedError("Vault backend not implemented yet")


@dataclass
class AWSSecretsManagerBackend(SecretsBackend):
    """
    Stub for AWS Secrets Manager.
    Later:
      - pip install boto3
      - use AWS creds/role
      - read a JSON secret and return the requested key
    """
    region: str
    prefix: str = ""

    def get(self, key: str, *, version: Optional[str] = None) -> str:
        # TODO: real implementation using boto3
        # Pseudocode:
        # import json, boto3
        # client = boto3.client("secretsmanager", region_name=self.region)
        # name = f"{self.prefix}{key}"
        # kwargs = {"SecretId": name}
        # if version: kwargs["VersionStage"] = version  # or VersionId depending on your scheme
        # resp = client.get_secret_value(**kwargs)
        # value = resp.get("SecretString") or resp.get("SecretBinary")
        # if SecretString is JSON: return json.loads(value).get("value") or similar
        raise NotImplementedError("AWS Secrets Manager backend not implemented yet")


# ---------- Factory + singleton facade ----------

def _make_backend() -> SecretsBackend:
    backend = (os.getenv("SECRETS_BACKEND") or "env").strip().lower()
    if backend == "env":
        return EnvSecretsBackend()
    if backend == "vault":
        return VaultSecretsBackend(
            addr=os.getenv("VAULT_ADDR", ""),
            token=os.getenv("VAULT_TOKEN", ""),
            kv_mount=os.getenv("VAULT_KV_MOUNT", "kv"),
            kv_path=os.getenv("VAULT_KV_PATH", ""),
        )
    if backend in ("aws", "aws-sm", "aws_sm", "awssecretsmanager"):
        return AWSSecretsManagerBackend(
            region=os.getenv("AWS_REGION", "us-east-1"),
            prefix=os.getenv("AWS_SECRETS_PREFIX", ""),
        )
    # Fallback to env and warn
    print(f"[secrets_loader] Unknown SECRETS_BACKEND='{backend}', falling back to env")
    return EnvSecretsBackend()


class SecretsClient:
    """
    Thin wrapper so you can add helpers later (like get_json, get_bytes, etc.).
    """
    def __init__(self, backend: SecretsBackend):
        self._backend = backend

    def get(self, key: str, *, version: Optional[str] = None) -> str:
        return self._backend.get(key, version=version)


# Create a module-level singleton you can import anywhere
secrets = SecretsClient(_make_backend())
