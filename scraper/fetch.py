"""Polite HTTP fetching: one shared client, robots.txt, a delay per host."""
from __future__ import annotations

import time
import urllib.robotparser
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx


@dataclass
class FetchResult:
    url: str
    ok: bool
    status_code: int | None
    html: str
    error: str | None = None


class Fetcher:
    def __init__(self, user_agent: str, timeout: float = 30, delay_per_host: float = 3):
        self.user_agent = user_agent
        self.delay = delay_per_host
        self.client = httpx.Client(
            headers={"User-Agent": user_agent, "Accept-Language": "nl,fr,en;q=0.8"},
            timeout=timeout,
            follow_redirects=True,
        )
        self._last_hit: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    def _allowed(self, url: str) -> bool:
        host = urlparse(url).scheme + "://" + urlparse(url).netloc
        if host not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self.client.get(host + "/robots.txt")
                if r.status_code == 200:
                    rp.parse(r.text.splitlines())
                    self._robots[host] = rp
                else:
                    self._robots[host] = None  # no robots.txt: allowed
            except httpx.HTTPError:
                self._robots[host] = None
        rp = self._robots[host]
        return True if rp is None else rp.can_fetch(self.user_agent, url)

    def _wait(self, url: str) -> None:
        host = urlparse(url).netloc
        last = self._last_hit.get(host)
        if last is not None:
            gap = time.monotonic() - last
            if gap < self.delay:
                time.sleep(self.delay - gap)
        self._last_hit[host] = time.monotonic()

    def get(self, url: str) -> FetchResult:
        if not self._allowed(url):
            return FetchResult(url, False, None, "", "blocked by robots.txt")
        self._wait(url)
        try:
            r = self.client.get(url)
        except httpx.HTTPError as e:
            return FetchResult(url, False, None, "", f"{type(e).__name__}: {e}")
        if r.status_code >= 400:
            return FetchResult(url, False, r.status_code, "", f"HTTP {r.status_code}")
        return FetchResult(url, True, r.status_code, r.text)

    def close(self) -> None:
        self.client.close()
