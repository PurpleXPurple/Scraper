import os
import sys
import re
import time
import json
import math
import asyncio
import hashlib
import sqlite3
import platform
import threading
import statistics
import subprocess
from collections import defaultdict, Counter
from dataclasses import dataclass, field, asdict
from pathlib import Path
from urllib.parse import urlparse, urljoin, quote, urlunparse
from typing import Optional, Callable, Any

import orjson
from selectolax.lexbor import LexborHTMLParser
from curl_cffi.requests import AsyncSession as _AsyncSession

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

from folder_manager import FolderManager, _atomic_write
from config import (
    API_ROUTER_ENABLED, API_ROUTER_TIMEOUT, API_ROUTER_MAX_ITEMS,
    MOS_BUDGET_FILE, LOG_LEVEL,
)


# ============================================================================
#  LOGGING
# ============================================================================

import logging

_LOG = logging.getLogger("api_router")
_LOG.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))


def _log(msg, *args, level=logging.DEBUG):
    try:
        _LOG.log(level, msg, *args)
    except Exception:
        pass


# ============================================================================
#  HARDWARE PROFILER — one-shot, cached
# ============================================================================

class Hardware:
    _profile = None
    _lock = threading.Lock()

    @classmethod
    def profile(cls):
        if cls._profile is not None:
            return cls._profile
        with cls._lock:
            if cls._profile is not None:
                return cls._profile
            cls._profile = cls._build()
            return cls._profile

    @classmethod
    def _build(cls):
        cores_physical = os.cpu_count() or 4
        cores_logical = cores_physical
        ram_gb = 4.0
        disk_gb = 10.0
        is_ssd = True
        is_windows = os.name == "nt"
        is_mac = sys.platform == "darwin"
        is_linux = sys.platform.startswith("linux")

        if _PSUTIL:
            try:
                cores_physical = psutil.cpu_count(logical=False) or cores_physical
                cores_logical = psutil.cpu_count(logical=True) or cores_physical
            except Exception:
                pass
            try:
                vm = psutil.virtual_memory()
                ram_gb = vm.total / (1024 ** 3)
            except Exception:
                pass
            try:
                du = psutil.disk_usage(str(FolderManager.ROOT))
                disk_gb = du.free / (1024 ** 3)
            except Exception:
                pass
        else:
            try:
                ram_bytes = os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
                ram_gb = ram_bytes / (1024 ** 3)
            except Exception:
                pass
            try:
                stat = os.statvfs(str(FolderManager.ROOT))
                disk_gb = stat.f_bavail * stat.f_frsize / (1024 ** 3)
            except Exception:
                pass

        if is_windows:
            try:
                import shutil as _sh
                du = _sh.disk_usage(str(FolderManager.ROOT))
                disk_gb = du.free / (1024 ** 3)
            except Exception:
                pass

        tier = cls._tier(cores_physical, ram_gb, disk_gb)
        return {
            "cores_physical": cores_physical,
            "cores_logical": cores_logical,
            "ram_gb": round(ram_gb, 2),
            "disk_gb": round(disk_gb, 2),
            "platform": sys.platform,
            "is_windows": is_windows,
            "is_mac": is_mac,
            "is_linux": is_linux,
            "tier": tier,
        }

    @staticmethod
    def _tier(cores, ram_gb, disk_gb):
        if cores >= 16 and ram_gb >= 32 and disk_gb >= 100:
            return "workstation"
        if cores >= 8 and ram_gb >= 16 and disk_gb >= 50:
            return "laptop"
        if cores >= 4 and ram_gb >= 8 and disk_gb >= 20:
            return "small"
        return "minimal"


# ============================================================================
#  ADAPTIVE TUNER — real-time adjustment based on observed throughput
# ============================================================================

class AdaptiveTuner:
    TIERS = {
        "workstation": {
            "concurrency": 32,
            "tier_timeout": 12.0,
            "per_probe_timeout": 8.0,
            "js_bundle_size_mb": 20,
            "js_max_bundles": 12,
            "source_map_size_mb": 30,
            "probe_paths_batch": 24,
            "cache_memory_mb": 256,
            "osint_enabled": True,
            "ct_lookups_per_hour": 100,
            "wayback_lookups_per_hour": 200,
        },
        "laptop": {
            "concurrency": 16,
            "tier_timeout": 15.0,
            "per_probe_timeout": 10.0,
            "js_bundle_size_mb": 10,
            "js_max_bundles": 8,
            "source_map_size_mb": 15,
            "probe_paths_batch": 16,
            "cache_memory_mb": 128,
            "osint_enabled": True,
            "ct_lookups_per_hour": 40,
            "wayback_lookups_per_hour": 80,
        },
        "small": {
            "concurrency": 8,
            "tier_timeout": 20.0,
            "per_probe_timeout": 12.0,
            "js_bundle_size_mb": 5,
            "js_max_bundles": 4,
            "source_map_size_mb": 8,
            "probe_paths_batch": 10,
            "cache_memory_mb": 64,
            "osint_enabled": True,
            "ct_lookups_per_hour": 15,
            "wayback_lookups_per_hour": 30,
        },
        "minimal": {
            "concurrency": 4,
            "tier_timeout": 25.0,
            "per_probe_timeout": 15.0,
            "js_bundle_size_mb": 2,
            "js_max_bundles": 2,
            "source_map_size_mb": 3,
            "probe_paths_batch": 6,
            "cache_memory_mb": 32,
            "osint_enabled": False,
            "ct_lookups_per_hour": 0,
            "wayback_lookups_per_hour": 0,
        },
    }

    def __init__(self, tier):
        base = dict(self.TIERS.get(tier, self.TIERS["small"]))
        self.base = base
        self.current = dict(base)
        self.network_latency_ms = None
        self.observed_success = defaultdict(int)
        self.observed_failure = defaultdict(int)
        self.observed_latency = defaultdict(list)
        self._lock = threading.Lock()

    def set_network_latency(self, ms):
        self.network_latency_ms = ms
        if ms > 800:
            self.current["per_probe_timeout"] = min(
                self.base["per_probe_timeout"] * 1.5, 30.0
            )
        elif ms < 100:
            self.current["per_probe_timeout"] = max(
                self.base["per_probe_timeout"] * 0.7, 3.0
            )

    def record(self, detector, ok, latency=0.0):
        with self._lock:
            if ok:
                self.observed_success[detector] += 1
            else:
                self.observed_failure[detector] += 1
            if latency > 0:
                self.observed_latency[detector].append(latency)
                if len(self.observed_latency[detector]) > 100:
                    self.observed_latency[detector] = (
                        self.observed_latency[detector][-100:]
                    )

    def detector_priority(self, detector, base_priority=0.5):
        s = self.observed_success.get(detector, 0)
        f = self.observed_failure.get(detector, 0)
        total = s + f
        if total < 3:
            return base_priority
        success_rate = s / total
        latencies = self.observed_latency.get(detector, [])
        latency_factor = 1.0
        if latencies:
            median_ms = statistics.median(latencies) * 1000
            if median_ms > 3000:
                latency_factor = 0.5
            elif median_ms > 1500:
                latency_factor = 0.8
            elif median_ms < 300:
                latency_factor = 1.2
        return base_priority * success_rate * latency_factor

    def detector_timeout(self, detector):
        latencies = self.observed_latency.get(detector, [])
        if not latencies:
            return self.current["per_probe_timeout"]
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        return max(2.0, min(p95 * 2.0, self.current["per_probe_timeout"] * 2))

    def snapshot(self):
        return {
            "base": dict(self.base),
            "current": dict(self.current),
            "network_latency_ms": self.network_latency_ms,
            "success_rates": {
                d: round(
                    self.observed_success[d] /
                    max(1, self.observed_success[d] + self.observed_failure[d]),
                    3,
                )
                for d in set(self.observed_success) | set(self.observed_failure)
            },
        }


# ============================================================================
#  ADAPTIVE BUDGET — self-limiting external API caller
# ============================================================================

class AdaptiveBudget:
    def __init__(self, path=None):
        self.path = Path(path or (FolderManager.CACHE / "api_router_budget.json"))
        self.data = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        try:
            if self.path.exists():
                with open(self.path, "rb") as f:
                    self.data = json.loads(f.read())
        except Exception:
            self.data = {}

    def _save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write(self.path, json.dumps(self.data).encode("utf-8"))
        except Exception:
            pass

    def _hour_key(self):
        return time.strftime("%Y-%m-%d-%H", time.gmtime())

    def _day_key(self):
        return time.strftime("%Y-%m-%d", time.gmtime())

    def used_hour(self, name):
        entry = self.data.get(name, {})
        if entry.get("hour") != self._hour_key():
            return 0
        return entry.get("hour_count", 0)

    def used_day(self, name):
        entry = self.data.get(name, {})
        if entry.get("day") != self._day_key():
            return 0
        return entry.get("day_count", 0)

    def record(self, name, limit_hour=None, limit_day=None):
        with self._lock:
            entry = self.data.get(name) or {}
            if entry.get("hour") != self._hour_key():
                entry["hour"] = self._hour_key()
                entry["hour_count"] = 0
            if entry.get("day") != self._day_key():
                entry["day"] = self._day_key()
                entry["day_count"] = 0
            entry["hour_count"] = entry.get("hour_count", 0) + 1
            entry["day_count"] = entry.get("day_count", 0) + 1
            self.data[name] = entry
            if entry["hour_count"] % 5 == 0:
                self._save()

    def allowed(self, name, limit_hour=None, limit_day=None):
        if limit_hour is not None and self.used_hour(name) >= limit_hour:
            return False
        if limit_day is not None and self.used_day(name) >= limit_day:
            return False
        return True

    def flush(self):
        with self._lock:
            self._save()


# ============================================================================
#  DISCOVERY CACHE
# ============================================================================

class DiscoveryCache:
    def __init__(self, path=None):
        self.path = Path(path or (FolderManager.DB / "api_router_cache.sqlite"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path), timeout=30, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS detections ("
            "host TEXT, detector TEXT, result TEXT, confidence REAL, ts REAL, "
            "PRIMARY KEY (host, detector))"
        )
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS host_summary ("
            "host TEXT PRIMARY KEY, result TEXT, ts REAL)"
        )
        self.conn.commit()
        self._lock = threading.Lock()
        self._pending = 0

    def get_detector(self, host, detector, ttl=604800):
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT result, confidence, ts FROM detections "
                "WHERE host = ? AND detector = ? LIMIT 1",
                (host, detector),
            )
            row = cur.fetchone()
            if not row:
                return None
            if time.time() - row[2] > ttl:
                return None
            try:
                return json.loads(row[0]), row[1]
            except Exception:
                return None

    def put_detector(self, host, detector, result, confidence):
        try:
            payload = json.dumps(result, default=str)
        except Exception:
            return
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO detections "
                "(host, detector, result, confidence, ts) VALUES (?, ?, ?, ?, ?)",
                (host, detector, payload, confidence, time.time()),
            )
            self._pending += 1
            if self._pending >= 20:
                self.conn.commit()
                self._pending = 0

    def get_host(self, host, ttl=604800):
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT result, ts FROM host_summary WHERE host = ? LIMIT 1",
                (host,),
            )
            row = cur.fetchone()
            if not row:
                return None
            if time.time() - row[1] > ttl:
                return None
            try:
                return json.loads(row[0])
            except Exception:
                return None

    def put_host(self, host, result):
        try:
            payload = json.dumps(result, default=str)
        except Exception:
            return
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO host_summary (host, result, ts) VALUES (?, ?, ?)",
                (host, payload, time.time()),
            )
            self.conn.commit()

    def flush(self):
        with self._lock:
            try:
                self.conn.commit()
            except Exception:
                pass

    def close(self):
        self.flush()
        try:
            self.conn.close()
        except Exception:
            pass


# ============================================================================
#  RESULT SCHEMA
# ============================================================================

@dataclass
class ApiDiscoveryResult:
    url: str
    host: str
    api_type: str
    endpoint: str
    spec_url: Optional[str] = None
    spec_format: str = "json"
    detector: str = ""
    confidence: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


# ============================================================================
#  HOST / URL HELPERS
# ============================================================================

def _bare_host(url_or_host):
    s = str(url_or_host).strip().lower()
    if "://" in s:
        try:
            return urlparse(s).netloc
        except Exception:
            return s
    return s


def _host_no_www(host):
    if host.startswith("www."):
        return host[4:]
    return host


def _root_url(url_or_host):
    if "://" in str(url_or_host):
        try:
            p = urlparse(str(url_or_host))
            return f"{p.scheme}://{p.netloc}"
        except Exception:
            return str(url_or_host)
    return f"https://{url_or_host}"


def _url_join_safe(base, path):
    try:
        return urljoin(base.rstrip("/") + "/", path.lstrip("/"))
    except Exception:
        return base.rstrip("/") + "/" + path.lstrip("/")


def _content_hash(text):
    return hashlib.blake2b(str(text).encode("utf-8", "ignore"), digest_size=16).hexdigest()


def _looks_like_openapi(obj):
    if not isinstance(obj, dict):
        return False
    if "openapi" in obj or "swagger" in obj:
        if "paths" in obj or "info" in obj:
            return True
    return False


def _looks_like_graphql_introspection(obj):
    if not isinstance(obj, dict):
        return False
    if "data" in obj and isinstance(obj["data"], dict):
        d = obj["data"]
        return "__schema" in d or "__type" in d
    return False


# ============================================================================
#  FETCH HELPERS — adaptive timeouts
# ============================================================================

class Fetcher:
    def __init__(self, tuner):
        self.tuner = tuner
        self._session = None
        self._session_lock = threading.Lock()

    def _get_session(self):
        if self._session is None:
            with self._session_lock:
                if self._session is None:
                    self._session = _AsyncSession(
                        impersonate="chrome136", max_clients=8,
                        default_headers=False,
                    )
        return self._session

    async def fetch(self, url, method="GET", headers=None, body=None,
                     timeout=None, max_bytes=None, allow_redirects=True):
        if not self.tuner:
            timeout = timeout or 10.0
        else:
            timeout = timeout or self.tuner.current["per_probe_timeout"]
        try:
            session = self._get_session()
            req_headers = {"User-Agent": "Mozilla/5.0 (compatible; api-router/2.0)"}
            if headers:
                req_headers.update(headers)
            if method == "POST":
                r = await session.post(
                    url, headers=req_headers,
                    data=body if isinstance(body, (bytes, str)) else None,
                    json=body if isinstance(body, (dict, list)) else None,
                    timeout=timeout, allow_redirects=allow_redirects,
                )
            elif method == "HEAD":
                r = await session.head(
                    url, headers=req_headers, timeout=timeout,
                    allow_redirects=allow_redirects,
                )
            elif method == "OPTIONS":
                r = await session.options(
                    url, headers=req_headers, timeout=timeout,
                    allow_redirects=allow_redirects,
                )
            else:
                r = await session.get(
                    url, headers=req_headers, timeout=timeout,
                    allow_redirects=allow_redirects,
                )
            content = r.content or b""
            if max_bytes and len(content) > max_bytes:
                content = content[:max_bytes]
            return {
                "url": str(r.url) if hasattr(r, "url") else url,
                "status": r.status_code,
                "headers": dict(r.headers) if r.headers else {},
                "body": content,
                "content_type": (r.headers.get("content-type", "") if r.headers else "").lower(),
                "elapsed": 0.0,
            }
        except asyncio.TimeoutError:
            return {"status": 0, "error": "timeout", "url": url}
        except Exception as e:
            return {"status": 0, "error": repr(e)[:200], "url": url}

    async def close(self):
        try:
            if self._session is not None:
                await self._session.close()
        except Exception:
            pass
        self._session = None


# ============================================================================
#  TIER 1 — DIRECT HANDLER REGISTRY
# ============================================================================

class DirectHandlers:
    _registry = {}

    @classmethod
    def register(cls, pattern, handler):
        cls._registry[pattern] = handler

    @classmethod
    def lookup(cls, url):
        host = _bare_host(url)
        bare = _host_no_www(host)
        for pattern, handler in cls._registry.items():
            if pattern in bare:
                return handler
        return None


async def _handler_stackexchange(session, url):
    try:
        from se_api import se_fetch_url
        rec, err = await se_fetch_url(url)
        if err or rec is None:
            return None
        return ApiDiscoveryResult(
            url=url, host=_bare_host(url),
            api_type="se_api",
            endpoint="https://api.stackexchange.com/2.3",
            detector="direct_stackexchange",
            confidence=1.0,
            metadata={"record": rec},
        )
    except Exception:
        return None


async def _handler_wrapper(name, async_fn):
    async def _wrapper(session, url):
        try:
            rec = await async_fn(url)
            if rec is None:
                return None
            return ApiDiscoveryResult(
                url=url, host=_bare_host(url),
                api_type="direct_handler",
                endpoint="",
                detector=f"direct_{name}",
                confidence=1.0,
                metadata={"record": rec},
            )
        except Exception:
            return None
    return _wrapper


def _register_direct():
    DirectHandlers.register("stackexchange", _handler_stackexchange)
    DirectHandlers.register("stackoverflow", _handler_stackexchange)
    DirectHandlers.register("superuser", _handler_stackexchange)
    DirectHandlers.register("serverfault", _handler_stackexchange)
    DirectHandlers.register("askubuntu", _handler_stackexchange)
    DirectHandlers.register("mathoverflow", _handler_stackexchange)


_register_direct()


# ============================================================================
#  TIER 2 — RFC / WELL-KNOWN
# ============================================================================

async def _m01_wellknown_api_catalog(ctx):
    url = _url_join_safe(ctx["root"], "/.well-known/api-catalog")
    r = await ctx["fetcher"].fetch(
        url,
        headers={"Accept": "application/linkset+json, application/json"},
    )
    if r.get("status") != 200:
        return None
    try:
        data = orjson.loads(r["body"])
    except Exception:
        return None
    linkset = data.get("linkset") or []
    for entry in linkset:
        for link in entry.get("item", []) or []:
            rel = link.get("rel", "")
            if rel in ("service-desc", "service-doc"):
                href = link.get("href")
                if href:
                    return ApiDiscoveryResult(
                        url=ctx["url"], host=ctx["host"],
                        api_type="openapi",
                        endpoint=href,
                        spec_url=href,
                        detector="m01_wellknown_api_catalog",
                        confidence=0.98,
                        metadata={"linkset": linkset},
                    )
    return None


async def _m02_wellknown_openapi(ctx):
    for path in ("/.well-known/openapi.json",
                  "/.well-known/openapi.yaml",
                  "/.well-known/openapi"):
        r = await ctx["fetcher"].fetch(_url_join_safe(ctx["root"], path))
        if r.get("status") != 200:
            continue
        try:
            data = orjson.loads(r["body"])
        except Exception:
            continue
        if _looks_like_openapi(data):
            return ApiDiscoveryResult(
                url=ctx["url"], host=ctx["host"],
                api_type="openapi",
                endpoint=r["url"],
                spec_url=r["url"],
                spec_format="json",
                detector="m02_wellknown_openapi",
                confidence=0.95,
                metadata={"title": (data.get("info") or {}).get("title"),
                          "version": (data.get("info") or {}).get("version")},
            )
    return None


async def _m03_oidc(ctx):
    url = _url_join_safe(ctx["root"], "/.well-known/openid-configuration")
    r = await ctx["fetcher"].fetch(url)
    if r.get("status") != 200:
        return None
    try:
        data = orjson.loads(r["body"])
    except Exception:
        return None
    if "issuer" in data and "authorization_endpoint" in data:
        return ApiDiscoveryResult(
            url=ctx["url"], host=ctx["host"],
            api_type="oidc",
            endpoint=data["issuer"],
            detector="m03_oidc",
            confidence=0.90,
            metadata={
                "authorization_endpoint": data.get("authorization_endpoint"),
                "token_endpoint": data.get("token_endpoint"),
                "jwks_uri": data.get("jwks_uri"),
                "userinfo_endpoint": data.get("userinfo_endpoint"),
            },
        )
    return None


async def _m04_oauth_server(ctx):
    url = _url_join_safe(ctx["root"], "/.well-known/oauth-authorization-server")
    r = await ctx["fetcher"].fetch(url)
    if r.get("status") != 200:
        return None
    try:
        data = orjson.loads(r["body"])
    except Exception:
        return None
    if "issuer" in data and "token_endpoint" in data:
        return ApiDiscoveryResult(
            url=ctx["url"], host=ctx["host"],
            api_type="oauth",
            endpoint=data["issuer"],
            detector="m04_oauth_server",
            confidence=0.85,
            metadata=data,
        )
    return None


async def _m05_security_txt(ctx):
    url = _url_join_safe(ctx["root"], "/.well-known/security.txt")
    r = await ctx["fetcher"].fetch(url)
    if r.get("status") != 200:
        return None
    text = r["body"].decode("utf-8", "ignore")
    contacts = re.findall(r"Contact:\s*(\S+)", text)
    if not contacts:
        return None
    return ApiDiscoveryResult(
        url=ctx["url"], host=ctx["host"],
        api_type="security_contact",
        endpoint="",
        detector="m05_security_txt",
        confidence=0.30,
        metadata={"contacts": contacts[:5]},
    )


async def _m06_wellknown_mcp(ctx):
    url = _url_join_safe(ctx["root"], "/.well-known/mcp")
    r = await ctx["fetcher"].fetch(url)
    if r.get("status") != 200:
        return None
    try:
        data = orjson.loads(r["body"])
    except Exception:
        return None
    if "mcpServers" in data or "servers" in data:
        return ApiDiscoveryResult(
            url=ctx["url"], host=ctx["host"],
            api_type="mcp",
            endpoint=r["url"],
            detector="m06_wellknown_mcp",
            confidence=0.85,
            metadata=data,
        )
    return None


# ============================================================================
#  TIER 3 — HTML CONTENT
# ============================================================================

async def _m07_link_rel(ctx):
    r = await ctx["fetcher"].fetch(ctx["url"], max_bytes=2 * 1024 * 1024)
    if r.get("status") != 200:
        return None
    try:
        tree = LexborHTMLParser(r["body"].decode("utf-8", "ignore"))
    except Exception:
        return None
    for link in tree.css("link[rel]"):
        rel = (link.attributes.get("rel") or "").lower()
        if rel in ("service-desc", "service-doc", "api-catalog"):
            href = link.attributes.get("href")
            if href:
                return ApiDiscoveryResult(
                    url=ctx["url"], host=ctx["host"],
                    api_type="openapi",
                    endpoint=href,
                    spec_url=href,
                    detector="m07_link_rel",
                    confidence=0.92,
                    metadata={"rel": rel},
                )
    return None


async def _m08_jsonld(ctx):
    r = await ctx["fetcher"].fetch(ctx["url"], max_bytes=2 * 1024 * 1024)
    if r.get("status") != 200:
        return None
    try:
        tree = LexborHTMLParser(r["body"].decode("utf-8", "ignore"))
    except Exception:
        return None
    for script in tree.css('script[type="application/ld+json"]'):
        try:
            raw = script.text(strip=False) or ""
            data = orjson.loads(raw)
        except Exception:
            continue
        candidates = [data] if isinstance(data, dict) else data if isinstance(data, list) else []
        for item in candidates:
            if not isinstance(item, dict):
                continue
            t = item.get("@type")
            if t in ("WebAPI", "APIReference", "EntryPoint"):
                url = item.get("url") or item.get("documentation")
                if url:
                    return ApiDiscoveryResult(
                        url=ctx["url"], host=ctx["host"],
                        api_type="openapi",
                        endpoint=url,
                        spec_url=url,
                        detector="m08_jsonld",
                        confidence=0.85,
                        metadata={"ld_type": t},
                    )
    return None


async def _m09_spa_config(ctx):
    r = await ctx["fetcher"].fetch(ctx["url"], max_bytes=3 * 1024 * 1024)
    if r.get("status") != 200:
        return None
    text = r["body"].decode("utf-8", "ignore")
    markers = (
        "__NEXT_DATA__", "__NUXT__", "window.__INITIAL_STATE__",
        "window.__DATA__", "window.__APP_STATE__", "__APOLLO_STATE__",
        "__REDUX_STATE__", "window.__PRELOADED_STATE__",
    )
    if not any(m in text for m in markers):
        return None
    api_patterns = [
        r'"(api_?url|apiUrl|API_URL)"\s*:\s*"([^"]+)"',
        r'"(api_base|apiBase|API_BASE)"\s*:\s*"([^"]+)"',
        r'"(baseURL|baseUrl|BASE_URL)"\s*:\s*"([^"]+)"',
        r'"(GRAPHQL_ENDPOINT|graphqlEndpoint)"\s*:\s*"([^"]+)"',
        r'"(API_HOST|apiHost)"\s*:\s*"([^"]+)"',
    ]
    found = {}
    for pat in api_patterns:
        for m in re.finditer(pat, text):
            key, val = m.group(1), m.group(2)
            if val.startswith(("http://", "https://", "/")):
                found[key] = val
    if not found:
        return None
    primary = next(iter(found.values()))
    return ApiDiscoveryResult(
        url=ctx["url"], host=ctx["host"],
        api_type="rest",
        endpoint=primary,
        detector="m09_spa_config",
        confidence=0.80,
        metadata={"spa_configs": found,
                  "markers": [m for m in markers if m in text]},
    )


async def _m10_meta_tags(ctx):
    r = await ctx["fetcher"].fetch(ctx["url"], max_bytes=1 * 1024 * 1024)
    if r.get("status") != 200:
        return None
    try:
        tree = LexborHTMLParser(r["body"].decode("utf-8", "ignore"))
    except Exception:
        return None
    found = {}
    for meta in tree.css("meta"):
        name = (meta.attributes.get("name") or "").lower()
        content = meta.attributes.get("content")
        if not content:
            continue
        if name in ("api-base", "api-url", "api-host", "csrf-token", "generator"):
            found[name] = content
    if not found:
        return None
    endpoint = found.get("api-base") or found.get("api-url") or found.get("api-host")
    if not endpoint:
        return None
    return ApiDiscoveryResult(
        url=ctx["url"], host=ctx["host"],
        api_type="rest",
        endpoint=endpoint,
        detector="m10_meta_tags",
        confidence=0.70,
        metadata=found,
    )


# ============================================================================
#  TIER 4 — PROTOCOL PROBING
# ============================================================================

async def _m11_options(ctx):
    r = await ctx["fetcher"].fetch(ctx["url"], method="OPTIONS")
    if r.get("status") not in (200, 204):
        return None
    allow = r["headers"].get("allow", "") or r["headers"].get("Allow", "")
    if not allow:
        return None
    methods = [m.strip().upper() for m in allow.split(",")]
    api_methods = {"GET", "POST", "PUT", "DELETE", "PATCH"}
    if len(set(methods) & api_methods) < 3:
        return None
    body = r.get("body", b"")
    schema_body = None
    if body and body[:1] in (b"{", b"["):
        try:
            schema_body = orjson.loads(body)
        except Exception:
            pass
    confidence = 0.95 if schema_body else 0.7
    return ApiDiscoveryResult(
        url=ctx["url"], host=ctx["host"],
        api_type="rest",
        endpoint=ctx["url"],
        detector="m11_options",
        confidence=confidence,
        metadata={"allow": methods, "schema": schema_body},
    )


async def _m12_head_content_type(ctx):
    r = await ctx["fetcher"].fetch(ctx["url"], method="HEAD")
    if r.get("status") != 200:
        return None
    ct = r["content_type"]
    api_types = (
        "application/json",
        "application/vnd.api+json",
        "application/hal+json",
        "application/openapi+json",
        "application/problem+json",
        "application/graphql+json",
    )
    if not any(t in ct for t in api_types):
        return None
    return ApiDiscoveryResult(
        url=ctx["url"], host=ctx["host"],
        api_type="rest",
        endpoint=ctx["url"],
        detector="m12_head_content_type",
        confidence=0.85,
        metadata={"content_type": ct},
    )


OPENAPI_PATHS = (
    "/openapi.json", "/openapi.yaml",
    "/swagger.json", "/swagger.yaml",
    "/api-docs", "/api-docs.json",
    "/v1/openapi.json", "/v2/openapi.json", "/v3/openapi.json",
    "/docs/openapi.json", "/api/openapi.json", "/api/swagger.json",
    "/swagger/v1/swagger.json", "/swagger/v2/swagger.json",
    "/api/v1/openapi.json", "/api/v2/openapi.json", "/api/v3/openapi.json",
)


async def _m13_openapi_paths(ctx):
    paths = list(OPENAPI_PATHS)
    batch = ctx["tuner"].current["probe_paths_batch"]
    sem = asyncio.Semaphore(ctx["tuner"].current["concurrency"])
    root = ctx["root"]
    fetcher = ctx["fetcher"]

    async def _probe(path):
        async with sem:
            r = await fetcher.fetch(_url_join_safe(root, path))
            if r.get("status") != 200:
                return None
            ct = r["content_type"]
            body = r.get("body", b"")
            if not body:
                return None
            if "json" in ct or body[:1] in (b"{", b"["):
                try:
                    data = orjson.loads(body)
                except Exception:
                    return None
                if _looks_like_openapi(data):
                    return (path, r["url"], data, "json")
            elif "yaml" in ct or body[:20].lstrip().startswith(b"openapi"):
                try:
                    text = body.decode("utf-8", "ignore")
                    if "openapi:" in text or "swagger:" in text:
                        return (path, r["url"], {}, "yaml")
                except Exception:
                    pass
            return None

    results = await asyncio.gather(
        *[_probe(p) for p in paths[:batch]],
        return_exceptions=True,
    )
    for res in results:
        if isinstance(res, tuple):
            path, url, data, fmt = res
            return ApiDiscoveryResult(
                url=ctx["url"], host=ctx["host"],
                api_type="openapi",
                endpoint=url,
                spec_url=url,
                spec_format=fmt,
                detector="m13_openapi_paths",
                confidence=0.95,
                metadata={"found_at": path,
                          "title": (data.get("info") or {}).get("title") if data else None},
            )
    return None


SWAGGER_UI_PATHS = (
    "/swagger-ui.html", "/swagger-ui/index.html", "/swagger/",
    "/api/docs", "/api/docs/", "/redoc", "/redoc.html", "/docs",
    "/swagger/index.html", "/api/swagger-ui.html",
)


async def _m14_swagger_ui(ctx):
    sem = asyncio.Semaphore(ctx["tuner"].current["concurrency"])
    fetcher = ctx["fetcher"]
    root = ctx["root"]

    spec_regex = re.compile(
        r'(?:url|spec-url|specUrl|configUrl)\s*[:=]\s*["\']([^"\']+)["\']'
    )

    async def _probe(path):
        async with sem:
            r = await fetcher.fetch(_url_join_safe(root, path), max_bytes=512 * 1024)
            if r.get("status") != 200:
                return None
            ct = r["content_type"]
            if "html" not in ct and "json" not in ct:
                return None
            text = r["body"].decode("utf-8", "ignore")
            if "SwaggerUI" not in text and "swagger-ui" not in text and "redoc" not in text.lower():
                return None
            for m in spec_regex.finditer(text):
                spec_url = m.group(1)
                if spec_url.endswith((".json", ".yaml", ".yml")) or "/openapi" in spec_url.lower() or "/swagger" in spec_url.lower():
                    absolute = _url_join_safe(root, spec_url)
                    return (path, absolute)
            return None

    results = await asyncio.gather(
        *[_probe(p) for p in SWAGGER_UI_PATHS],
        return_exceptions=True,
    )
    for res in results:
        if isinstance(res, tuple):
            path, spec_url = res
            return ApiDiscoveryResult(
                url=ctx["url"], host=ctx["host"],
                api_type="openapi",
                endpoint=spec_url,
                spec_url=spec_url,
                detector="m14_swagger_ui",
                confidence=0.92,
                metadata={"ui_path": path},
            )
    return None


GRAPHQL_PATHS = (
    "/graphql", "/graphiql", "/api/graphql", "/v1/graphql",
    "/v2/graphql", "/query", "/api/query", "/gql",
)


async def _m15_graphql(ctx):
    sem = asyncio.Semaphore(ctx["tuner"].current["concurrency"])
    fetcher = ctx["fetcher"]
    root = ctx["root"]
    introspection = {"query": "{__schema{queryType{name} mutationType{name}}}"}

    async def _probe(path):
        async with sem:
            url = _url_join_safe(root, path)
            r = await fetcher.fetch(
                url, method="POST",
                headers={"Content-Type": "application/json",
                         "Accept": "application/json"},
                body=json.dumps(introspection),
                timeout=ctx["tuner"].current["per_probe_timeout"],
            )
            status = r.get("status", 0)
            if status not in (200, 400):
                return None
            body = r.get("body", b"")
            if not body:
                return None
            try:
                data = orjson.loads(body)
            except Exception:
                return None
            if _looks_like_graphql_introspection(data):
                return (path, url, data)
            if isinstance(data, dict) and "errors" in data:
                for err in data["errors"]:
                    msg = err.get("message", "") if isinstance(err, dict) else ""
                    if "introspection" in msg.lower() or "graphql" in msg.lower():
                        return (path, url, None)
            return None

    results = await asyncio.gather(
        *[_probe(p) for p in GRAPHQL_PATHS],
        return_exceptions=True,
    )
    for res in results:
        if isinstance(res, tuple):
            path, url, schema = res
            return ApiDiscoveryResult(
                url=ctx["url"], host=ctx["host"],
                api_type="graphql",
                endpoint=url,
                spec_format="graphql_sdl",
                detector="m15_graphql",
                confidence=0.95 if schema else 0.80,
                metadata={"path": path,
                          "introspection_available": schema is not None,
                          "schema": schema},
            )
    return None


SOAP_PATHS = (
    "?wsdl", "/service?wsdl", "/services", "/ws", "/soap", "/wadl",
    "/services?wsdl", "/api?wsdl",
)


async def _m16_soap_wadl(ctx):
    sem = asyncio.Semaphore(ctx["tuner"].current["concurrency"])
    fetcher = ctx["fetcher"]
    root = ctx["root"]

    async def _probe(path):
        async with sem:
            url = _url_join_safe(root, path)
            r = await fetcher.fetch(url, max_bytes=1024 * 1024)
            if r.get("status") != 200:
                return None
            ct = r["content_type"]
            body = r.get("body", b"")
            if not body:
                return None
            if "xml" in ct or "wsdl" in ct or "wadl" in ct:
                text = body.decode("utf-8", "ignore")
                if "<definitions" in text or "wsdl:" in text:
                    ops = re.findall(r'<wsdl:operation\s+name="([^"]+)"', text)
                    return (path, url, "wsdl", ops)
                if "<application" in text and "wadl" in text.lower():
                    methods = re.findall(r'<method\s+id="([^"]+)"', text)
                    return (path, url, "wadl", methods)
            return None

    results = await asyncio.gather(
        *[_probe(p) for p in SOAP_PATHS],
        return_exceptions=True,
    )
    for res in results:
        if isinstance(res, tuple):
            path, url, kind, ops = res
            return ApiDiscoveryResult(
                url=ctx["url"], host=ctx["host"],
                api_type="soap" if kind == "wsdl" else "wadl",
                endpoint=url,
                spec_url=url,
                spec_format="xml",
                detector="m16_soap_wadl",
                confidence=0.90,
                metadata={"found_at": path, "kind": kind, "operations": ops[:50]},
            )
    return None


# ============================================================================
#  TIER 5 — JAVASCRIPT ANALYSIS
# ============================================================================

_ENDPOINT_PATTERNS = [
    re.compile(r"""["'`](/api/[^"'`\s<>)]+)"""),
    re.compile(r"""["'`](/v[1-9]/[^"'`\s<>)]+)"""),
    re.compile(r"""fetch\s*\(\s*["'`](https?://[^"'`]+)["'`]"""),
    re.compile(r"""axios\.(?:get|post|put|delete|patch)\s*\(\s*["'`]([^"'`]+)["'`]"""),
    re.compile(r"""\.open\s*\(\s*["'`](?:GET|POST|PUT|DELETE|PATCH)["'`]\s*,\s*["'`]([^"'`]+)["'`]"""),
    re.compile(r"""(https?://api\.[a-z0-9\-]+\.[a-z]{2,}(?:/[^\s"'`<>)]*)?)"""),
    re.compile(r"""["'`](/graphql[^"'`\s<>)]*)"""),
    re.compile(r"""["'`](/rest/[^"'`\s<>)]+)"""),
]


async def _get_js_urls(ctx, html_text):
    try:
        tree = LexborHTMLParser(html_text)
    except Exception:
        return []
    urls = []
    for script in tree.css("script[src]"):
        src = script.attributes.get("src") or ""
        if not src:
            continue
        if src.startswith(("data:", "blob:")):
            continue
        absolute = _url_join_safe(ctx["root"], src)
        if absolute.endswith((".js", ".mjs", ".jsx")) or "bundle" in absolute:
            urls.append(absolute)
    return urls


async def _m17_js_bundle_regex(ctx):
    html_r = await ctx["fetcher"].fetch(ctx["url"], max_bytes=3 * 1024 * 1024)
    if html_r.get("status") != 200:
        return None
    html_text = html_r["body"].decode("utf-8", "ignore")
    js_urls = await _get_js_urls(ctx, html_text)
    if not js_urls:
        return None
    max_bundles = ctx["tuner"].current["js_max_bundles"]
    max_bytes = ctx["tuner"].current["js_bundle_size_mb"] * 1024 * 1024
    sem = asyncio.Semaphore(ctx["tuner"].current["concurrency"])
    fetcher = ctx["fetcher"]

    found = set()

    async def _fetch_js(js_url):
        async with sem:
            r = await fetcher.fetch(js_url, max_bytes=max_bytes)
            if r.get("status") != 200:
                return
            text = r["body"].decode("utf-8", "ignore")
            for pat in _ENDPOINT_PATTERNS:
                for m in pat.finditer(text):
                    g = m.group(1) if m.groups() else m.group(0)
                    if not g:
                        continue
                    if g.startswith(("/", "http://", "https://")):
                        found.add(g)

    await asyncio.gather(*[_fetch_js(u) for u in js_urls[:max_bundles]],
                          return_exceptions=True)
    if not found:
        return None
    absolute = [
        _url_join_safe(ctx["root"], f) if f.startswith("/") else f
        for f in found
    ]
    api_like = [u for u in absolute
                 if "/api/" in u or "/v1/" in u or "/v2/" in u or
                 "/v3/" in u or "/graphql" in u or "/rest/" in u or
                 "api." in urlparse(u).netloc]
    if not api_like:
        return None
    api_like = list(dict.fromkeys(api_like))[:20]
    return ApiDiscoveryResult(
        url=ctx["url"], host=ctx["host"],
        api_type="rest",
        endpoint=api_like[0],
        detector="m17_js_bundle_regex",
        confidence=0.75,
        metadata={"candidates": api_like},
    )


async def _m18_source_maps(ctx):
    html_r = await ctx["fetcher"].fetch(ctx["url"], max_bytes=3 * 1024 * 1024)
    if html_r.get("status") != 200:
        return None
    html_text = html_r["body"].decode("utf-8", "ignore")
    js_urls = await _get_js_urls(ctx, html_text)
    if not js_urls:
        return None
    max_bundles = max(1, ctx["tuner"].current["js_max_bundles"] // 2)
    max_bytes = ctx["tuner"].current["source_map_size_mb"] * 1024 * 1024
    sem = asyncio.Semaphore(ctx["tuner"].current["concurrency"])
    fetcher = ctx["fetcher"]

    found = set()

    async def _try_map(js_url):
        async with sem:
            r = await fetcher.fetch(js_url, max_bytes=200 * 1024)
            if r.get("status") != 200:
                return
            tail = r["body"][-1000:].decode("utf-8", "ignore")
            m = re.search(r"//#\s*sourceMappingURL=(\S+)", tail)
            if not m:
                return
            map_url = _url_join_safe(js_url, m.group(1))
            mr = await fetcher.fetch(map_url, max_bytes=max_bytes)
            if mr.get("status") != 200:
                return
            try:
                data = orjson.loads(mr["body"])
            except Exception:
                return
            sources_content = data.get("sourcesContent") or []
            for source in sources_content:
                if not isinstance(source, str):
                    continue
                for pat in _ENDPOINT_PATTERNS:
                    for mm in pat.finditer(source):
                        g = mm.group(1) if mm.groups() else mm.group(0)
                        if g and g.startswith(("/", "http://", "https://")):
                            found.add(g)

    await asyncio.gather(*[_try_map(u) for u in js_urls[:max_bundles]],
                          return_exceptions=True)
    if not found:
        return None
    api_like = [u for u in found
                 if "/api/" in u or "/v1/" in u or "/graphql" in u]
    if not api_like:
        return None
    absolute = [_url_join_safe(ctx["root"], f) if f.startswith("/") else f
                for f in api_like]
    return ApiDiscoveryResult(
        url=ctx["url"], host=ctx["host"],
        api_type="rest",
        endpoint=absolute[0],
        detector="m18_source_maps",
        confidence=0.85,
        metadata={"candidates": list(dict.fromkeys(absolute))[:20],
                  "from": "source_maps"},
    )


async def _m19_websocket(ctx):
    html_r = await ctx["fetcher"].fetch(ctx["url"], max_bytes=2 * 1024 * 1024)
    if html_r.get("status") != 200:
        return None
    text = html_r["body"].decode("utf-8", "ignore")
    ws_urls = set()
    for m in re.finditer(r"""["'`](wss?://[^"'`\s]+)["'`]""", text):
        ws_urls.add(m.group(1))
    for m in re.finditer(r"""new\s+WebSocket\s*\(\s*["'`]([^"'`]+)["'`]""", text):
        ws_urls.add(m.group(1))
    for m in re.finditer(r"""io\s*\(\s*["'`]([^"'`]+)["'`]""", text):
        ws_urls.add(m.group(1))
    if not ws_urls:
        return None
    return ApiDiscoveryResult(
        url=ctx["url"], host=ctx["host"],
        api_type="websocket",
        endpoint=list(ws_urls)[0],
        detector="m19_websocket",
        confidence=0.65,
        metadata={"ws_urls": list(ws_urls)[:10]},
    )


FRAMEWORK_PROBES = {
    "nextjs": ("/api", "/api/health", "/api/status"),
    "nuxt": ("/_nuxt", "/_api", "/api"),
    "django_drf": ("/api/", "/api/v1/", "/api/schema/", "/api/docs/"),
    "rails_api": ("/api/v1", "/api/v2", "/rails/info"),
    "strapi": ("/api", "/api/health", "/admin/init", "/api/__schema"),
    "laravel": ("/api/v1", "/api/v2", "/api/user"),
    "spring_boot": ("/actuator", "/actuator/health", "/v3/api-docs", "/v2/api-docs"),
    "fastapi": ("/docs", "/redoc", "/openapi.json", "/api/v1"),
    "flask_restx": ("/api", "/swagger.json"),
    "graphql_yoga": ("/graphql", "/graphiql"),
    "express": ("/api", "/api/v1"),
    "aspnet_core": ("/swagger", "/api"),
    "phoenix": ("/api", "/api/v1"),
    "wordpress": ("/wp-json", "/wp-json/wp/v2", "/wp-json/wp/v2/posts"),
    "ghost": ("/ghost/api/v3/admin", "/ghost/api/v4/admin", "/ghost/api/content"),
}


async def _m20_framework_fingerprint(ctx):
    r = await ctx["fetcher"].fetch(ctx["url"], max_bytes=3 * 1024 * 1024)
    if r.get("status") != 200:
        return None
    text = r["body"].decode("utf-8", "ignore")
    headers = r.get("headers", {})
    fingerprints = {
        "nextjs": ("__NEXT_DATA__" in text) or ("/_next/" in text),
        "nuxt": ("__NUXT__" in text) or ("/_nuxt/" in text),
        "django_drf": "csrfmiddlewaretoken" in text and "/static/admin/" in text,
        "rails_api": ("csrf-token" in text and "rails" in text.lower()),
        "strapi": ("strapi" in text.lower()),
        "laravel": ("laravel_session" in str(headers).lower()
                    or "XSRF-TOKEN" in headers),
        "spring_boot": ("X-Application-Context" in headers
                        or "Whitelabel Error Page" in text),
        "fastapi": ("fastapi" in text.lower() or "/docs" in text and "swagger" in text.lower()),
        "wordpress": ("/wp-content/" in text or "/wp-json/" in text
                       or "wp-includes" in text),
        "ghost": ("ghost/api" in text.lower() or "content-api" in text.lower()),
        "express": ("X-Powered-By" in headers
                     and "Express" in headers.get("X-Powered-By", "")),
        "aspnet_core": ("ASP.NET" in headers.get("Server", "")
                         or "X-AspNet-Version" in headers),
        "phoenix": ("X-Powered-By" in headers
                     and "phoenix" in str(headers).lower()),
        "graphql_yoga": ("graphql-yoga" in text.lower()),
        "flask_restx": ("flask-restx" in text.lower()
                         or "flask-restplus" in text.lower()),
    }
    matched = [k for k, v in fingerprints.items() if v]
    if not matched:
        return None
    fetcher = ctx["fetcher"]
    root = ctx["root"]
    for fw in matched:
        for path in FRAMEWORK_PROBES.get(fw, ()):
            probe = await fetcher.fetch(_url_join_safe(root, path),
                                          method="HEAD",
                                          timeout=3.0)
            if probe.get("status") in (200, 401, 403):
                return ApiDiscoveryResult(
                    url=ctx["url"], host=ctx["host"],
                    api_type="rest",
                    endpoint=_url_join_safe(root, path),
                    detector="m20_framework_fingerprint",
                    confidence=0.80,
                    metadata={"framework": fw, "all_matches": matched,
                              "probe_path": path},
                )
    return None


# ============================================================================
#  TIER 6 — EXTERNAL OSINT
# ============================================================================

async def _m21_ct_logs(ctx):
    if not ctx["tuner"].current["osint_enabled"]:
        return None
    budget = ctx["budget"]
    name = "crt_sh"
    limit = ctx["tuner"].current["ct_lookups_per_hour"]
    if not budget.allowed(name, limit_hour=limit):
        return None
    domain = _host_no_www(ctx["host"])
    url = f"https://crt.sh/?q=%25.{quote(domain)}&output=json"
    r = await ctx["fetcher"].fetch(url, timeout=10.0, max_bytes=2 * 1024 * 1024)
    budget.record(name, limit_hour=limit)
    if r.get("status") != 200:
        return None
    try:
        data = orjson.loads(r["body"])
    except Exception:
        return None
    names = set()
    for entry in data if isinstance(data, list) else []:
        nv = entry.get("name_value", "") if isinstance(entry, dict) else ""
        for line in nv.split("\n"):
            line = line.strip().lower()
            if line and not line.startswith("*"):
                names.add(line)
    api_hosts = [n for n in names
                  if any(p in n for p in ("api", "rest", "graphql", "gateway",
                                            "svc", "backend", "internal"))]
    if not api_hosts:
        return None
    return ApiDiscoveryResult(
        url=ctx["url"], host=ctx["host"],
        api_type="ct_only",
        endpoint=f"https://{api_hosts[0]}",
        detector="m21_ct_logs",
        confidence=0.60,
        metadata={"api_hosts": api_hosts[:20], "total_names": len(names)},
    )


async def _m22_dns_srv(ctx):
    domain = _host_no_www(ctx["host"])
    queries = [
        (f"_https._tcp.{domain}", "SRV"),
        (f"_http._tcp.{domain}", "SRV"),
        (f"_api._tcp.{domain}", "SRV"),
        (domain, "CNAME"),
    ]
    for name, qtype in queries:
        url = f"https://dns.google/resolve?name={quote(name)}&type={qtype}"
        r = await ctx["fetcher"].fetch(url, timeout=5.0, max_bytes=128 * 1024)
        if r.get("status") != 200:
            continue
        try:
            data = orjson.loads(r["body"])
        except Exception:
            continue
        answers = data.get("Answer", []) if isinstance(data, dict) else []
        for a in answers:
            if a.get("type") == 33 and "data" in a:
                target = a["data"].split()[2].rstrip(".")
                return ApiDiscoveryResult(
                    url=ctx["url"], host=ctx["host"],
                    api_type="srv",
                    endpoint=f"https://{target}",
                    detector="m22_dns_srv",
                    confidence=0.70,
                    metadata={"srv": a["data"], "query": name},
                )
    return None


async def _m23_wayback_cdx(ctx):
    if not ctx["tuner"].current["osint_enabled"]:
        return None
    budget = ctx["budget"]
    name = "wayback_api_router"
    limit = ctx["tuner"].current["wayback_lookups_per_hour"]
    if not budget.allowed(name, limit_hour=limit):
        return None
    domain = _host_no_www(ctx["host"])
    url = (f"https://web.archive.org/cdx/search/cdx?url={quote(domain)}/*"
           f"&output=json&collapse=urlkey&limit=500"
           f"&filter=statuscode:200&filter=mimetype:application/json")
    r = await ctx["fetcher"].fetch(url, timeout=12.0, max_bytes=2 * 1024 * 1024)
    budget.record(name, limit_hour=limit)
    if r.get("status") != 200:
        return None
    try:
        data = orjson.loads(r["body"])
    except Exception:
        return None
    if not isinstance(data, list) or len(data) < 2:
        return None
    header = data[0]
    try:
        url_idx = header.index("original")
    except ValueError:
        url_idx = 2
    urls = set()
    for row in data[1:]:
        if not isinstance(row, list) or len(row) <= url_idx:
            continue
        u = row[url_idx]
        if any(p in u for p in ("/api/", "/v1/", "/v2/", "/v3/",
                                  "/graphql", "/openapi", "/swagger")):
            urls.add(u)
    if not urls:
        return None
    urls = list(urls)[:20]
    return ApiDiscoveryResult(
        url=ctx["url"], host=ctx["host"],
        api_type="rest",
        endpoint=urls[0],
        detector="m23_wayback_cdx",
        confidence=0.65,
        metadata={"historical_urls": urls},
    )


FAVICON_FINGERPRINTS = {
    "grafana": ("/api/health", "/api/dashboards"),
    "kibana": ("/api/status", "/api/saved_objects/_find"),
    "jenkins": ("/api/json", "/crumbIssuer/api/json"),
    "airflow": ("/api/v1/dags", "/api/v1/health"),
    "metabase": ("/api/health", "/api/session"),
    "superset": ("/api/v1/health", "/api/v1/database"),
    "sonarqube": ("/api/server/version", "/api/projects/search"),
    "gitlab": ("/api/v4/projects", "/api/v4/version"),
    "jira": ("/rest/api/2/serverInfo", "/rest/api/3/myself"),
    "confluence": ("/rest/api/content", "/wiki/rest/api/space"),
    "graylog": ("/api/system", "/api/cluster"),
    "prometheus": ("/api/v1/status/config", "/api/v1/targets"),
    "vault": ("/v1/sys/health", "/v1/sys/seal-status"),
    "consul": ("/v1/status/leader", "/v1/catalog/services"),
}


async def _m24_favicon_hash(ctx):
    favicon_url = _url_join_safe(ctx["root"], "/favicon.ico")
    r = await ctx["fetcher"].fetch(favicon_url, max_bytes=200 * 1024, timeout=5.0)
    if r.get("status") != 200 or not r.get("body"):
        return None
    icon_hash = hashlib.md5(r["body"]).hexdigest()
    known = {
        "a19e0dd2b9d8c8e99f574a1a0d7e2b0f": "grafana",
        "f7f5a5a3c8ffa7c8e6e3d5a3d8b6e8b5": "kibana",
    }
    product = known.get(icon_hash)
    if not product:
        return None
    fetcher = ctx["fetcher"]
    for path in FAVICON_FINGERPRINTS.get(product, ()):
        probe = await fetcher.fetch(_url_join_safe(ctx["root"], path),
                                     method="HEAD", timeout=3.0)
        if probe.get("status") in (200, 401, 403):
            return ApiDiscoveryResult(
                url=ctx["url"], host=ctx["host"],
                api_type="rest",
                endpoint=_url_join_safe(ctx["root"], path),
                detector="m24_favicon_hash",
                confidence=0.85,
                metadata={"product": product, "favicon_hash": icon_hash,
                          "probe_path": path},
            )
    return None


_APIS_GURU_CACHE = None
_APIS_GURU_LOCK = threading.Lock()


async def _load_apis_guru(ctx):
    global _APIS_GURU_CACHE
    if _APIS_GURU_CACHE is not None:
        return _APIS_GURU_CACHE
    with _APIS_GURU_LOCK:
        if _APIS_GURU_CACHE is not None:
            return _APIS_GURU_CACHE
        cache_file = FolderManager.CACHE / "apis_guru_list.json"
        data = None
        if cache_file.exists():
            try:
                age = time.time() - cache_file.stat().st_mtime
                if age < 86400:
                    with open(cache_file, "rb") as f:
                        data = json.loads(f.read())
            except Exception:
                pass
        if data is None:
            r = await ctx["fetcher"].fetch(
                "https://api.apis.guru/v2/list.json",
                timeout=20.0, max_bytes=64 * 1024 * 1024,
            )
            if r.get("status") == 200:
                try:
                    data = orjson.loads(r["body"])
                    try:
                        _atomic_write(
                            cache_file,
                            json.dumps(data).encode("utf-8"),
                        )
                    except Exception:
                        pass
                except Exception:
                    data = {}
            else:
                data = {}
        _APIS_GURU_CACHE = data if isinstance(data, dict) else {}
        return _APIS_GURU_CACHE


async def _m25_apis_guru(ctx):
    if not ctx["tuner"].current["osint_enabled"]:
        return None
    directory = await _load_apis_guru(ctx)
    if not directory:
        return None
    domain = _host_no_www(ctx["host"])
    matches = []
    for name, entry in directory.items():
        if domain in name.lower():
            matches.append((name, entry))
        else:
            preferred = entry.get("preferred")
            if preferred:
                info = entry.get("versions", {}).get(preferred, {})
                info_url = info.get("info", {}).get("x-logo", {}).get("url", "")
                if domain in info_url.lower():
                    matches.append((name, entry))
    if not matches:
        return None
    name, entry = matches[0]
    preferred = entry.get("preferred")
    info = entry.get("versions", {}).get(preferred, {})
    spec_url = info.get("swaggerUrl") or info.get("openapiVer")
    return ApiDiscoveryResult(
        url=ctx["url"], host=ctx["host"],
        api_type="openapi",
        endpoint=spec_url or name,
        spec_url=spec_url,
        detector="m25_apis_guru",
        confidence=0.90,
        metadata={"apis_guru_name": name, "preferred_version": preferred},
    )


async def _m26_marketplace(ctx):
    if not ctx["tuner"].current["osint_enabled"]:
        return None
    domain = _host_no_www(ctx["host"])
    r = await ctx["fetcher"].fetch(
        f"https://api.rapidapi.com/search?q={quote(domain)}",
        timeout=8.0, max_bytes=512 * 1024,
    )
    if r.get("status") == 200:
        try:
            data = orjson.loads(r["body"])
        except Exception:
            data = None
        if data:
            return ApiDiscoveryResult(
                url=ctx["url"], host=ctx["host"],
                api_type="marketplace",
                endpoint="https://rapidapi.com/",
                detector="m26_marketplace",
                confidence=0.55,
                metadata={"marketplace": "rapidapi"},
            )
    return None


async def _m27_origin_ip(ctx):
    if not ctx["tuner"].current["osint_enabled"]:
        return None
    host = ctx["host"]
    resolver = f"https://dns.google/resolve?name={quote(host)}&type=A"
    r = await ctx["fetcher"].fetch(resolver, timeout=5.0, max_bytes=128 * 1024)
    if r.get("status") != 200:
        return None
    try:
        data = orjson.loads(r["body"])
    except Exception:
        return None
    answers = data.get("Answer", []) if isinstance(data, dict) else []
    if not answers:
        return None
    ip = answers[0].get("data")
    if not ip:
        return None
    ip_info = await ctx["fetcher"].fetch(
        f"http://ip-api.com/json/{ip}?fields=status,as,org,isp",
        timeout=5.0, max_bytes=32 * 1024,
    )
    if ip_info.get("status") != 200:
        return None
    try:
        info = orjson.loads(ip_info["body"])
    except Exception:
        return None
    asn = info.get("as", "")
    cdn_names = ("Cloudflare", "Fastly", "Akamai", "Amazon", "Google",
                  "Microsoft", "Imperva", "Sucuri", "StackPath")
    is_cdn = any(name.lower() in asn.lower() for name in cdn_names)
    if not is_cdn:
        return None
    return ApiDiscoveryResult(
        url=ctx["url"], host=ctx["host"],
        api_type="cdn_origin",
        endpoint="",
        detector="m27_origin_ip",
        confidence=0.40,
        metadata={"ip": ip, "asn": asn, "org": info.get("org"),
                  "isp": info.get("isp"), "cdn": True},
    )


async def _m28_hsts_preload(ctx):
    url = f"https://hstspreload.org/api/v2/status?domain={quote(_host_no_www(ctx['host']))}"
    r = await ctx["fetcher"].fetch(url, timeout=5.0, max_bytes=64 * 1024)
    if r.get("status") != 200:
        return None
    try:
        data = orjson.loads(r["body"])
    except Exception:
        return None
    if data.get("status") == "preloaded":
        return ApiDiscoveryResult(
            url=ctx["url"], host=ctx["host"],
            api_type="hsts_preload",
            endpoint="",
            detector="m28_hsts_preload",
            confidence=0.30,
            metadata=data,
        )
    return None


async def _m29_rdap(ctx):
    domain = _host_no_www(ctx["host"])
    parts = domain.split(".")
    if len(parts) >= 2:
        apex = ".".join(parts[-2:])
    else:
        apex = domain
    url = f"https://rdap.org/domain/{quote(apex)}"
    r = await ctx["fetcher"].fetch(
        url, timeout=8.0, max_bytes=256 * 1024,
        headers={"Accept": "application/rdap+json"},
    )
    if r.get("status") != 200:
        return None
    try:
        data = orjson.loads(r["body"])
    except Exception:
        return None
    nameservers = []
    for ns in data.get("nameservers", []) if isinstance(data, dict) else []:
        nameservers.append(ns.get("ldhName", "").lower())
    api_ns = [ns for ns in nameservers if "api" in ns or "svc" in ns]
    if not api_ns:
        return None
    return ApiDiscoveryResult(
        url=ctx["url"], host=ctx["host"],
        api_type="rdap",
        endpoint="",
        detector="m29_rdap",
        confidence=0.35,
        metadata={"nameservers": nameservers, "api_ns": api_ns},
    )


async def _m30_http_redirect_chain(ctx):
    r = await ctx["fetcher"].fetch(ctx["url"], method="HEAD", allow_redirects=False)
    if r.get("status") not in (301, 302, 307, 308):
        return None
    loc = r["headers"].get("location", "")
    if not loc:
        return None
    target = _url_join_safe(ctx["url"], loc)
    target_host = _bare_host(target)
    if target_host and target_host != ctx["host"]:
        return ApiDiscoveryResult(
            url=ctx["url"], host=ctx["host"],
            api_type="redirect",
            endpoint=target,
            detector="m30_http_redirect_chain",
            confidence=0.50,
            metadata={"target_host": target_host, "status": r["status"]},
        )
    return None


async def _m31_csp_report(ctx):
    r = await ctx["fetcher"].fetch(ctx["url"], method="HEAD")
    if r.get("status") != 200:
        return None
    csp = r["headers"].get("content-security-policy", "")
    if not csp:
        return None
    uris = re.findall(r"(https?://[^\s;]+)", csp)
    api_uris = [u for u in uris
                 if any(p in u for p in ("api", "graphql", "rest", "svc"))]
    if not api_uris:
        return None
    return ApiDiscoveryResult(
        url=ctx["url"], host=ctx["host"],
        api_type="csp_hint",
        endpoint=api_uris[0],
        detector="m31_csp_report",
        confidence=0.60,
        metadata={"csp_endpoints": api_uris[:10]},
    )


async def _m32_common_subdomain(ctx):
    if not ctx["tuner"].current["osint_enabled"]:
        return None
    domain = _host_no_www(ctx["host"])
    if domain.startswith("www."):
        domain = domain[4:]
    prefixes = ("api", "rest", "graphql", "gateway", "backend", "svc",
                 "developer", "dev", "sandbox", "staging")
    sem = asyncio.Semaphore(ctx["tuner"].current["concurrency"])
    fetcher = ctx["fetcher"]

    async def _probe(prefix):
        async with sem:
            sub = f"{prefix}.{domain}"
            url = f"https://{sub}/"
            r = await fetcher.fetch(url, method="HEAD", timeout=3.0,
                                     allow_redirects=False)
            status = r.get("status", 0)
            if status in (200, 401, 403, 405):
                return sub
            return None

    results = await asyncio.gather(*[_probe(p) for p in prefixes],
                                    return_exceptions=True)
    alive = [r for r in results if isinstance(r, str)]
    if not alive:
        return None
    return ApiDiscoveryResult(
        url=ctx["url"], host=ctx["host"],
        api_type="subdomain",
        endpoint=f"https://{alive[0]}",
        detector="m32_common_subdomain",
        confidence=0.70,
        metadata={"alive_subdomains": alive},
    )


# ============================================================================
#  TIER DEFINITIONS
# ============================================================================

TIER_RFC = {
    "name": "rfc",
    "min_confidence": 0.60,
    "detectors": [
        ("m01_wellknown_api_catalog", _m01_wellknown_api_catalog, 0.95),
        ("m02_wellknown_openapi", _m02_wellknown_openapi, 0.90),
        ("m03_oidc", _m03_oidc, 0.85),
        ("m04_oauth_server", _m04_oauth_server, 0.80),
        ("m05_security_txt", _m05_security_txt, 0.20),
        ("m06_wellknown_mcp", _m06_wellknown_mcp, 0.80),
    ],
}

TIER_HTML = {
    "name": "html",
    "min_confidence": 0.60,
    "detectors": [
        ("m07_link_rel", _m07_link_rel, 0.90),
        ("m08_jsonld", _m08_jsonld, 0.80),
        ("m09_spa_config", _m09_spa_config, 0.75),
        ("m10_meta_tags", _m10_meta_tags, 0.65),
    ],
}

TIER_PROTOCOL = {
    "name": "protocol",
    "min_confidence": 0.65,
    "detectors": [
        ("m11_options", _m11_options, 0.70),
        ("m12_head_content_type", _m12_head_content_type, 0.80),
        ("m13_openapi_paths", _m13_openapi_paths, 0.90),
        ("m14_swagger_ui", _m14_swagger_ui, 0.85),
        ("m15_graphql", _m15_graphql, 0.90),
        ("m16_soap_wadl", _m16_soap_wadl, 0.85),
    ],
}

TIER_JS = {
    "name": "javascript",
    "min_confidence": 0.70,
    "detectors": [
        ("m17_js_bundle_regex", _m17_js_bundle_regex, 0.70),
        ("m18_source_maps", _m18_source_maps, 0.80),
        ("m19_websocket", _m19_websocket, 0.60),
        ("m20_framework_fingerprint", _m20_framework_fingerprint, 0.75),
    ],
}

TIER_OSINT = {
    "name": "osint",
    "min_confidence": 0.55,
    "detectors": [
        ("m21_ct_logs", _m21_ct_logs, 0.55),
        ("m22_dns_srv", _m22_dns_srv, 0.65),
        ("m23_wayback_cdx", _m23_wayback_cdx, 0.60),
        ("m24_favicon_hash", _m24_favicon_hash, 0.80),
        ("m25_apis_guru", _m25_apis_guru, 0.85),
        ("m26_marketplace", _m26_marketplace, 0.50),
        ("m27_origin_ip", _m27_origin_ip, 0.35),
        ("m28_hsts_preload", _m28_hsts_preload, 0.25),
        ("m29_rdap", _m29_rdap, 0.30),
        ("m30_http_redirect_chain", _m30_http_redirect_chain, 0.45),
        ("m31_csp_report", _m31_csp_report, 0.55),
        ("m32_common_subdomain", _m32_common_subdomain, 0.65),
    ],
}

ALL_TIERS = (TIER_RFC, TIER_HTML, TIER_PROTOCOL, TIER_JS, TIER_OSINT)


# ============================================================================
#  ROUTER
# ============================================================================

class ApiRouter:
    def __init__(self, hard_profile=None, tuner=None, cache=None, budget=None):
        self.hard = hard_profile or Hardware.profile()
        self.tuner = tuner or AdaptiveTuner(self.hard["tier"])
        self.cache = cache or DiscoveryCache()
        self.budget = budget or AdaptiveBudget()
        self.fetcher = Fetcher(self.tuner)
        self._latency_probed = False

    async def _probe_network_latency(self):
        if self._latency_probed:
            return
        self._latency_probed = True
        t0 = time.monotonic()
        try:
            r = await self.fetcher.fetch(
                "https://www.google.com/generate_204",
                timeout=5.0, method="HEAD",
            )
            if r.get("status") in (200, 204):
                ms = (time.monotonic() - t0) * 1000
                self.tuner.set_network_latency(ms)
                _log("network latency: %.0f ms", ms)
        except Exception:
            pass

    async def _run_detector(self, ctx, name, fn, base_priority):
        priority = self.tuner.detector_priority(name, base_priority)
        timeout = self.tuner.detector_timeout(name)
        cached = self.cache.get_detector(ctx["host"], name)
        if cached is not None:
            result_dict, conf = cached
            if result_dict is None:
                return None
            return ApiDiscoveryResult(**result_dict)
        t0 = time.monotonic()
        try:
            result = await asyncio.wait_for(fn(ctx), timeout=timeout)
            latency = time.monotonic() - t0
            self.tuner.record(name, result is not None, latency)
            if result is not None:
                self.cache.put_detector(
                    ctx["host"], name, result.to_dict(), result.confidence
                )
            else:
                self.cache.put_detector(ctx["host"], name, None, 0.0)
            return result
        except asyncio.TimeoutError:
            self.tuner.record(name, False, time.monotonic() - t0)
            self.cache.put_detector(ctx["host"], name, None, 0.0)
            return None
        except Exception as e:
            _log("detector %s failed: %r", name, e)
            self.tuner.record(name, False, time.monotonic() - t0)
            return None

    async def discover(self, url):
        host = _bare_host(url)
        cached = self.cache.get_host(host)
        if cached is not None:
            if cached.get("_negative"):
                return None
            try:
                return ApiDiscoveryResult(**cached)
            except Exception:
                pass

        await self._probe_network_latency()

        ctx = {
            "url": url,
            "host": host,
            "root": _root_url(url),
            "fetcher": self.fetcher,
            "tuner": self.tuner,
            "cache": self.cache,
            "budget": self.budget,
        }

        for tier in ALL_TIERS:
            if tier["name"] == "osint" and not self.tuner.current["osint_enabled"]:
                continue
            sem = asyncio.Semaphore(self.tuner.current["concurrency"])
            tier_timeout = self.tuner.current["tier_timeout"]

            async def _run_with_sem(name, fn, priority):
                async with sem:
                    return await self._run_detector(ctx, name, fn, priority)

            tasks = [
                asyncio.create_task(_run_with_sem(name, fn, prio))
                for name, fn, prio in tier["detectors"]
            ]
            try:
                done, pending = await asyncio.wait(
                    tasks, timeout=tier_timeout,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for p in pending:
                    p.cancel()
                best = None
                for t in done:
                    try:
                        r = t.result()
                        if r is None:
                            continue
                        if r.confidence < tier["min_confidence"]:
                            continue
                        if best is None or r.confidence > best.confidence:
                            best = r
                    except Exception:
                        continue
                if best is not None:
                    self.cache.put_host(host, best.to_dict())
                    self.budget.flush()
                    return best
            except Exception as e:
                _log("tier %s failed: %r", tier["name"], e)

        self.cache.put_host(host, {"_negative": True, "ts": time.time()})
        self.budget.flush()
        return None

    async def close(self):
        await self.fetcher.close()
        self.cache.flush()
        self.budget.flush()
        try:
            self.cache.close()
        except Exception:
            pass


# ============================================================================
#  SYNC API
# ============================================================================

_DEFAULT_ROUTER = None
_ROUTER_LOCK = threading.Lock()


def _get_default_router():
    global _DEFAULT_ROUTER
    if _DEFAULT_ROUTER is not None:
        return _DEFAULT_ROUTER
    with _ROUTER_LOCK:
        if _DEFAULT_ROUTER is None:
            _DEFAULT_ROUTER = ApiRouter()
        return _DEFAULT_ROUTER


def has_route(url):
    if not API_ROUTER_ENABLED:
        return False
    try:
        handler = DirectHandlers.lookup(url)
        if handler is not None:
            return True
    except Exception:
        pass
    return True


def route_sync(url):
    if not API_ROUTER_ENABLED:
        return None
    direct = DirectHandlers.lookup(url)
    if direct is not None:
        try:
            loop = asyncio.new_event_loop()
            try:
                session = _AsyncSession(impersonate="chrome136", max_clients=2)
                try:
                    result = loop.run_until_complete(direct(session, url))
                finally:
                    loop.run_until_complete(session.close())
            finally:
                loop.close()
            if result and isinstance(result.metadata, dict):
                record = result.metadata.get("record")
                if record is not None:
                    return record
        except Exception as e:
            _log("direct handler failed: %r", e)
    try:
        router = _get_default_router()
        result = asyncio.run(router.discover(url))
        if result is None:
            return None
        if isinstance(result.metadata, dict):
            record = result.metadata.get("record")
            if record is not None:
                return record
        return result.to_dict()
    except Exception as e:
        _log("route_sync failed: %r", e)
        return None


async def route_async(url):
    if not API_ROUTER_ENABLED:
        return None
    router = _get_default_router()
    result = await router.discover(url)
    if result is None:
        return None
    return result


# ============================================================================
#  CLI
# ============================================================================

def _cli():
    import argparse
    p = argparse.ArgumentParser(prog="api_router",
                                 description="32-method adaptive API discovery")
    p.add_argument("--probe", type=str, help="URL to probe")
    p.add_argument("--show-hardware", action="store_true")
    p.add_argument("--show-diagnostics", action="store_true")
    p.add_argument("--show-cache", action="store_true")
    args = p.parse_args()

    if args.show_hardware:
        profile = Hardware.profile()
        print(json.dumps(profile, indent=2))
        tuner = AdaptiveTuner(profile["tier"])
        print(json.dumps(tuner.snapshot(), indent=2))
        return

    if args.show_diagnostics:
        from folder_manager import FolderManager
        print(FolderManager.diagnose()["summary"])
        return

    if args.show_cache:
        cache = DiscoveryCache()
        cur = cache.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM detections")
        n_det = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM host_summary")
        n_host = cur.fetchone()[0]
        print(f"detections cached: {n_det}")
        print(f"hosts cached:      {n_host}")
        cache.close()
        return

    if args.probe:
        result = asyncio.run(route_async(args.probe))
        if result is None:
            print("no API discovered")
            return
        if hasattr(result, "to_dict"):
            print(json.dumps(result.to_dict(), indent=2, default=str))
        else:
            print(json.dumps(result, indent=2, default=str))
        return

    p.print_help()


if __name__ == "__main__":
    _cli()