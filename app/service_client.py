"""Simple HTTP client between services (Trading → Settlement → T2S simulator), with timeouts and clear errors."""

import requests


class ServiceUnavailable(Exception):
    pass


class ServiceClient:
    def __init__(self, base_url, name, timeout=5):
        self.base_url = base_url.rstrip("/")
        self.name = name
        self.timeout = timeout

    def request(self, method, path, json=None, timeout=None):
        """Returns (HTTP status, JSON body). Raises ServiceUnavailable if the service does not respond."""
        try:
            r = requests.request(method, self.base_url + path, json=json, timeout=timeout or self.timeout)
        except requests.RequestException as exc:
            raise ServiceUnavailable(f"{self.name} unavailable at {self.base_url}: {exc.__class__.__name__}") from exc
        try:
            body = r.json()
        except ValueError:
            body = {"raw": r.text}
        return r.status_code, body
