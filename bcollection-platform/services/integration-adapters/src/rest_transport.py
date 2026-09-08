"""Shared REST boundary. Explicit idempotent POST; no fallback or automatic retry."""
import json
import os
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler
from uuid import uuid4


class AdapterError(ConnectionError):
    def __init__(self, code, *, status=None, retryable=False):
        # Never expose URLs, credentials, response bodies or customer identifiers.
        self.code, self.status, self.retryable = code, status, retryable
        super().__init__(code)


def validate_base_url(value, synthetic=False):
    url = urlparse(value)
    if (url.scheme not in {"http", "https"} or not url.hostname
            or url.username or url.password or url.query or url.fragment):
        raise ValueError("Explicit HTTP(S) base URL without credentials/query required")
    if synthetic and (url.scheme != "http" or url.hostname != "127.0.0.1"):
        raise ValueError("demo-http permits only explicit http://127.0.0.1 mock endpoints")
    return value.rstrip("/")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class RestTransport:
    def __init__(self, base_url, api_key="", timeout=5):
        self.synthetic = os.getenv("BCOLLECTION_MODE") == "demo-http"
        self.base_url = validate_base_url(base_url, self.synthetic)
        # Do not forward inherited production API keys to a local synthetic server.
        self.api_key, self.timeout = "" if self.synthetic else api_key, timeout
        handlers = [NoRedirect()]
        if self.synthetic:
            handlers.append(ProxyHandler({}))  # Never route demo traffic through a proxy.
        self.opener = build_opener(*handlers)

    def get(self, path):
        return self._request(path)

    def post(self, path, payload, idempotency_key):
        if not idempotency_key:
            raise ValueError('Idempotency key required')
        return self._request(path, payload, idempotency_key)

    def _request(self, path, body=None, idempotency_key=None):
        if path.startswith(("/", "http:" , "https:")) or ".." in path.split("/"):
            raise ValueError("Relative resource path required")
        headers = {"Accept": "application/json", "X-Client-Id": "BCOLLECTION_PLATFORM",
                   "X-Request-Id": str(uuid4())}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        data = None
        if body is not None:
            data = json.dumps(body, sort_keys=True).encode()
            headers.update({'Content-Type': 'application/json', 'Idempotency-Key': idempotency_key})
        try:
            with self.opener.open(Request(f"{self.base_url}/{path}", headers=headers, data=data), timeout=self.timeout) as response:
                if self.synthetic and response.headers.get("X-Data-Origin") != "SYNTHETIC":
                    raise AdapterError("UNTRUSTED_DEMO_SOURCE")
                raw = response.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise AdapterError("RESPONSE_TOO_LARGE")
                try:
                    payload = json.loads(raw)
                except (ValueError, UnicodeError) as exc:
                    raise AdapterError("INVALID_JSON") from exc
                if not isinstance(payload, dict):
                    raise AdapterError("INVALID_CONTRACT")
                return payload
        except HTTPError as exc:
            status = exc.code
            exc.close()
            raise AdapterError("NOT_FOUND" if status == 404 else "HTTP_ERROR", status=status,
                               retryable=status in {429, 502, 503, 504}) from None
        except (URLError, TimeoutError, socket.timeout) as exc:
            raise AdapterError("SOURCE_UNAVAILABLE", retryable=True) from None


def required_list(payload, field):
    value = payload.get(field)
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise AdapterError("INVALID_CONTRACT")
    return value
