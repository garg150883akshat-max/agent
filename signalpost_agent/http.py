from __future__ import annotations
import hashlib, json, os, threading, time
from pathlib import Path
from typing import Any
import requests

UA = "SignalpostResearchAgent/1.0 (+Builderr challenge; source-backed public research)"

class Budget:
    def __init__(self, limit: int = 2000):
        self.limit = limit
        self.used = 0
        self._lock = threading.Lock()
    def take(self) -> bool:
        with self._lock:
            if self.used >= self.limit:
                return False
            self.used += 1
            return True

class HttpClient:
    def __init__(self, cache_dir: str = "data/cache", budget: Budget | None = None):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.8,no;q=0.7"})
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.budget = budget or Budget()
        self.timeout = (5, 15)

    @staticmethod
    def key(url: str, headers: dict[str, str] | None = None) -> str:
        raw = url + "\n" + json.dumps(headers or {}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, url: str, *, headers: dict[str, str] | None = None,
            allow_redirects: bool = True, use_cache: bool = True, binary: bool = False) -> requests.Response:
        path = self.cache_dir / f"{self.key(url, headers)}.bin"
        meta = self.cache_dir / f"{self.key(url, headers)}.json"
        if use_cache and path.exists() and meta.exists():
            data = path.read_bytes()
            m = json.loads(meta.read_text())
            r = requests.Response(); r.status_code = m["status"]; r.url = m["url"]; r.headers.update(m.get("headers", {})); r._content = data; return r
        if not self.budget.take():
            raise RuntimeError("request budget exhausted")
        r = self.session.get(url, headers=headers, timeout=self.timeout, allow_redirects=allow_redirects)
        if use_cache and r.status_code < 500:
            path.write_bytes(r.content)
            meta.write_text(json.dumps({"status": r.status_code, "url": r.url,
                                        "headers": {k: v for k, v in r.headers.items()
                                                     if k.lower() in {"content-type", "etag", "last-modified"}}}))
        return r

    def json(self, url: str, **kwargs: Any) -> tuple[Any, requests.Response]:
        r = self.get(url, **kwargs)
        return r.json(), r
