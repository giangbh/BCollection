import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class RuntimeSettings:
    mode: str
    database_path: Path

    @classmethod
    def from_env(cls):
        mode = os.getenv("BCOLLECTION_MODE", "demo").lower()
        if mode not in {"demo", "test", "integration", "demo-http"}:
            raise ValueError("BCOLLECTION_MODE must be demo, test, demo-http or integration")
        configured_path = os.getenv("BCOLLECTION_DB_PATH")
        if mode in {"integration", "demo-http"} and not configured_path:
            raise ValueError(f"{mode} requires an explicit BCOLLECTION_DB_PATH")
        path = Path(configured_path).expanduser() if configured_path else REPO_ROOT / ".runtime" / mode / "bcollection.sqlite3"
        return cls(mode=mode, database_path=path.resolve())

    def validate_adapters(self):
        # Explicitly reject mixed mock/HTTP profiles; never silently fall back.
        for prefix, url_name in (
            ("CORE_BANKING", "CORE_BANKING_API_URL"),
            ("LOS", "LOS_API_URL"),
            ("CIC", "CIC_GATEWAY_URL"),
        ):
            mode = os.getenv(f"{prefix}_MODE", "mock").lower()
            expected = "http" if self.mode in {"integration", "demo-http"} else "mock"
            if mode != expected:
                raise ValueError(f"{prefix}_MODE must be {expected} for {self.mode}")
            if self.mode in {"integration", "demo-http"}:
                url = urlparse(os.getenv(url_name, ""))
                if url.scheme not in {"http", "https"} or not url.netloc:
                    raise ValueError(f"{self.mode} requires an explicit valid {url_name}")
                if url.username or url.password or url.query or url.fragment:
                    raise ValueError("Base URLs cannot contain credentials, query or fragment")
                if self.mode == "demo-http" and (url.scheme != "http" or url.hostname != "127.0.0.1"):
                    raise ValueError("demo-http permits only explicit http://127.0.0.1 mock endpoints")
        # PR-01 integration is read-only. Outbound messaging remains disabled.
        if self.mode == 'demo-http':
            for name in ('CRM_API_URL', 'DIRECTORY_API_URL', 'EWS_API_URL'):
                if os.getenv(name):
                    url = urlparse(os.environ[name])
                    if url.scheme != 'http' or url.hostname != '127.0.0.1' or url.username or url.password or url.query or url.fragment:
                        raise ValueError(f'{name} must be an explicit loopback mock URL')
        if os.getenv("MESSAGING_MODE", "mock").lower() != "mock":
            raise ValueError("PR-01 does not enable outbound HTTP messaging")
