"""Cliente HTTP simples entre serviços (Trading → Settlement → simulador T2S), com timeout e erros claros."""

import requests


class ServiceUnavailable(Exception):
    pass


class ServiceClient:
    def __init__(self, base_url, name, timeout=5):
        self.base_url = base_url.rstrip("/")
        self.name = name
        self.timeout = timeout

    def request(self, method, path, json=None, timeout=None):
        """Devolve (código HTTP, corpo JSON). Lança ServiceUnavailable se o serviço não responder."""
        try:
            r = requests.request(method, self.base_url + path, json=json, timeout=timeout or self.timeout)
        except requests.RequestException as exc:
            raise ServiceUnavailable(f"{self.name} indisponível em {self.base_url}: {exc.__class__.__name__}") from exc
        try:
            body = r.json()
        except ValueError:
            body = {"raw": r.text}
        return r.status_code, body
