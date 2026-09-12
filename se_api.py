import os
import re
import sys
import time
import gzip
import random
import asyncio
import hashlib
import zlib
import threading
import statistics
from collections import defaultdict, deque, OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, quote, urlencode

import orjson

from curl_cffi.requests import Session as _SyncSession
from curl_cffi.requests import AsyncSession as _AsyncSession

from folder_manager import FolderManager, _atomic_write


# ============================================================================
#  CONSTANTS
# ============================================================================

SE_PRIMARY_ENDPOINT = "https://api.stackexchange.com/2.3"
SE_ENDPOINTS = (
    "https://api.stackexchange.com/2.3",
    "https://api.stackexchange.com/2.2",
    "https://stackexchange.com/2.3",
)

SE_USER_AGENTS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36 OPR/95.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Mobile/15E148 Safari/604.1",
)

SE_IMPERSONATES = (
    "chrome136", "chrome131", "safari184", "firefox135",
    "chrome136", "chrome131", "chrome142",
)

SE_FILTERS = {
    "withbody": "withbody",
    "withcomments": "!9_bDDxJY5",
    "default": "default",
    "no_filter": "none",
}

SE_BASE_TIMEOUT = 15.0
SE_MAX_RETRIES = 4
SE_BACKOFF_BASE = 1.8
SE_BACKOFF_MAX = 45.0
SE_MIN_JITTER = 0.15
SE_MAX_JITTER = 1.1
SE_PER_REQUEST_FLOOR = 0.25
SE_QUOTA_SAFE_MARGIN = 40

SE_WITHBODY = "withbody"
SE_MAX_ANSWERS = 20
SE_MAX_COMMENTS = 30
SE_MAX_PAGES = 25

SE_QUOTA_FILE = "se_quota.json"
SE_BREAKER_FILE = "se_breaker.json"
SE_STATS_FILE = "se_stats.json"


def _log(msg, *args, level="info"):
    try:
        import logging
        getattr(logging.getLogger("se_api"), level)(msg, *args)
    except Exception:
        pass


# ============================================================================
#  SITE MAPPING — every domain in the SE network
# ============================================================================

SE_HOST_TO_SITE = {
    "stackoverflow.com": "stackoverflow",
    "serverfault.com": "serverfault",
    "superuser.com": "superuser",
    "askubuntu.com": "askubuntu",
    "mathoverflow.net": "mathoverflow",
    "stackapps.com": "stackapps",
    "stackexchange.com": "stackexchange",
    "sstatic.net": "stackoverflow",
    "askdifferent.com": "apple",
    "superuser.com": "superuser",
    "unix.stackexchange.com": "unix",
    "askubuntu.com": "askubuntu",
    "math.stackexchange.com": "math",
    "physics.stackexchange.com": "physics",
    "chemistry.stackexchange.com": "chemistry",
    "biology.stackexchange.com": "biology",
    "english.stackexchange.com": "english",
    "ell.stackexchange.com": "ell",
    "stats.stackexchange.com": "stats",
    "dba.stackexchange.com": "dba",
    "security.stackexchange.com": "security",
    "crypto.stackexchange.com": "crypto",
    "softwareengineering.stackexchange.com": "softwareengineering",
    "codereview.stackexchange.com": "codereview",
    "datascience.stackexchange.com": "datascience",
    "ai.stackexchange.com": "ai",
    "gis.stackexchange.com": "gis",
    "apple.stackexchange.com": "apple",
    "android.stackexchange.com": "android",
    "gamedev.stackexchange.com": "gamedev",
    "webapps.stackexchange.com": "webapps",
    "webmasters.stackexchange.com": "webmasters",
    "raspberrypi.stackexchange.com": "raspberrypi",
    "arduino.stackexchange.com": "arduino",
    "electronics.stackexchange.com": "electronics",
    "robotics.stackexchange.com": "robotics",
    "blender.stackexchange.com": "blender",
    "gaming.stackexchange.com": "gaming",
    "puzzling.stackexchange.com": "puzzling",
    "worldbuilding.stackexchange.com": "worldbuilding",
    "scifi.stackexchange.com": "scifi",
    "literature.stackexchange.com": "literature",
    "history.stackexchange.com": "history",
    "philosophy.stackexchange.com": "philosophy",
    "psychology.stackexchange.com": "psychology",
    "skeptics.stackexchange.com": "skeptics",
    "law.stackexchange.com": "law",
    "money.stackexchange.com": "money",
    "travel.stackexchange.com": "travel",
    "cooking.stackexchange.com": "cooking",
    "diy.stackexchange.com": "diy",
    "gardening.stackexchange.com": "gardening",
    "parenting.stackexchange.com": "parenting",
    "pets.stackexchange.com": "pets",
    "outdoors.stackexchange.com": "outdoors",
    "fitness.stackexchange.com": "fitness",
    "health.stackexchange.com": "health",
    "medicalsciences.stackexchange.com": "medicalsciences",
    "academia.stackexchange.com": "academia",
    "workplace.stackexchange.com": "workplace",
    "interpersonal.stackexchange.com": "interpersonal",
    "writers.stackexchange.com": "writers",
    "music.stackexchange.com": "music",
    "movies.stackexchange.com": "movies",
    "anime.stackexchange.com": "anime",
    "crafts.stackexchange.com": "crafts",
    "photo.stackexchange.com": "photo",
    "graphicdesign.stackexchange.com": "graphicdesign",
    "ux.stackexchange.com": "ux",
    "sharepoint.stackexchange.com": "sharepoint",
    "salesforce.stackexchange.com": "salesforce",
    "magento.stackexchange.com": "magento",
    "wordpress.stackexchange.com": "wordpress",
    "drupal.stackexchange.com": "drupal",
    "joomla.stackexchange.com": "joomla",
    "expressionengine.stackexchange.com": "expressionengine",
    "craftcms.stackexchange.com": "craftcms",
    "ethereum.stackexchange.com": "ethereum",
    "bitcoin.stackexchange.com": "bitcoin",
    "stellar.stackexchange.com": "stellar",
    "eosio.stackexchange.com": "eosio",
    "tezos.stackexchange.com": "tezos",
    "cardano.stackexchange.com": "cardano",
    "solana.stackexchange.com": "solana",
    "substrate.stackexchange.com": "substrate",
    "iota.stackexchange.com": "iota",
    "monero.stackexchange.com": "monero",
    "es.stackoverflow.com": "es.stackoverflow",
    "pt.stackoverflow.com": "pt.stackoverflow",
    "ru.stackoverflow.com": "ru.stackoverflow",
    "ja.stackoverflow.com": "ja.stackoverflow",
    "ko.stackoverflow.com": "ko.stackoverflow",
    "fr.stackoverflow.com": "fr.stackoverflow",
    "de.stackoverflow.com": "de.stackoverflow",
    "it.stackoverflow.com": "it.stackoverflow",
    "pl.stackoverflow.com": "pl.stackoverflow",
    "tr.stackoverflow.com": "tr.stackoverflow",
    "vi.stackoverflow.com": "vi.stackoverflow",
    "th.stackoverflow.com": "th.stackoverflow",
    "id.stackoverflow.com": "id.stackoverflow",
    "bn.stackoverflow.com": "bn.stackoverflow",
    "uk.stackoverflow.com": "uk.stackoverflow",
    "gr.stackoverflow.com": "gr.stackoverflow",
    "ro.stackoverflow.com": "ro.stackoverflow",
    "nl.stackoverflow.com": "nl.stackoverflow",
    "cs.stackoverflow.com": "cs.stackoverflow",
    "hu.stackoverflow.com": "hu.stackoverflow",
    "fi.stackoverflow.com": "fi.stackoverflow",
    "sv.stackoverflow.com": "sv.stackoverflow",
    "da.stackoverflow.com": "da.stackoverflow",
    "no.stackoverflow.com": "no.stackoverflow",
    "he.stackoverflow.com": "he.stackoverflow",
    "ar.stackoverflow.com": "ar.stackoverflow",
    "fa.stackoverflow.com": "fa.stackoverflow",
    "hi.stackoverflow.com": "hi.stackoverflow",
    "sqa.stackexchange.com": "sqa",
    "pm.stackexchange.com": "pm",
    "iot.stackexchange.com": "iot",
    "devops.stackexchange.com": "devops",
    "serverfault.com": "serverfault",
    "superuser.com": "superuser",
    "mathoverflow.net": "mathoverflow",
    "stackapps.com": "stackapps",
    "askubuntu.com": "askubuntu",
    "startups.stackexchange.com": "startups",
    "beer.stackexchange.com": "beer",
    "coffee.stackexchange.com": "coffee",
    "wine.stackexchange.com": "wine",
    "bricks.stackexchange.com": "bricks",
    "diy.stackexchange.com": "diy",
    "mechanics.stackexchange.com": "mechanics",
    "bicycles.stackexchange.com": "bicycles",
    "motorcycles.stackexchange.com": "motorcycles",
    "woodworking.stackexchange.com": "woodworking",
    "homebrew.stackexchange.com": "homebrew",
    "vegetarianism.stackexchange.com": "vegetarianism",
    "veganism.stackexchange.com": "vegetarianism",
    "hermeneutics.stackexchange.com": "hermeneutics",
    "christianity.stackexchange.com": "christianity",
    "islam.stackexchange.com": "islam",
    "judaism.stackexchange.com": "judaism",
    "buddhism.stackexchange.com": "buddhism",
    "hinduism.stackexchange.com": "hinduism",
    "atheism.stackexchange.com": "atheism",
    "mormonism.stackexchange.com": "mormonism",
    "russian.stackexchange.com": "russian",
    "german.stackexchange.com": "german",
    "french.stackexchange.com": "french",
    "spanish.stackexchange.com": "spanish",
    "italian.stackexchange.com": "italian",
    "japanese.stackexchange.com": "japanese",
    "chinese.stackexchange.com": "chinese",
    "korean.stackexchange.com": "korean",
    "latin.stackexchange.com": "latin",
    "greek.stackexchange.com": "greek",
    "arabic.stackexchange.com": "arabic",
    "esperanto.stackexchange.com": "esperanto",
    "portuguese.stackexchange.com": "portuguese",
    "signlanguage.stackexchange.com": "signlanguage",
    "linguistics.stackexchange.com": "linguistics",
    "ell.stackexchange.com": "ell",
    "english.stackexchange.com": "english",
    "ukrainian.stackexchange.com": "ukrainian",
    "hinduism.stackexchange.com": "hinduism",
    "buddhism.stackexchange.com": "buddhism",
}

SE_SUBDOMAIN_TO_SITE = SE_HOST_TO_SITE


# ============================================================================
#  UTILITIES
# ============================================================================

def _host_of(url):
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def _bare_host(url_or_host):
    h = _host_of(url_or_host)
    if h.startswith("www."):
        return h[4:]
    return h


def se_site_for_url(url):
    """Map URL to Stack Exchange API site parameter."""
    bare = _bare_host(url)
    if not bare:
        return None
    if bare in SE_HOST_TO_SITE:
        return SE_HOST_TO_SITE[bare]
    if bare.endswith(".stackexchange.com"):
        sub = bare[:-len(".stackexchange.com")]
        if sub in SE_SUBDOMAIN_TO_SITE:
            return SE_SUBDOMAIN_TO_SITE[sub]
        return sub
    if bare.endswith(".stackoverflow.com"):
        sub = bare[:-len(".stackoverflow.com")]
        return f"{sub}.stackoverflow" if sub else "stackoverflow"
    if bare.endswith(".superuser.com") or bare.endswith(".serverfault.com"):
        return bare.split(".")[0]
    return None


def se_parse_question_id(url):
    """Extract numeric question ID from URL."""
    try:
        path = urlparse(url).path
    except Exception:
        return None
    segs = [s for s in path.split("/") if s]
    for i, s in enumerate(segs):
        if s in ("questions", "q") and i + 1 < len(segs):
            try:
                return int(segs[i + 1])
            except ValueError:
                continue
    return None


def se_parse_answer_id(url):
    try:
        p = urlparse(url)
        frag = p.fragment
        if frag:
            m = re.search(r"answer-(\d+)", frag)
            if m:
                return int(m.group(1))
        path = p.path
        m = re.search(r"/(\d+)#(\d+)", path)
        if m:
            return int(m.group(2))
    except Exception:
        pass
    return None


def se_parse_tag(url):
    try:
        path = urlparse(url).path
    except Exception:
        return None
    segs = [s for s in path.split("/") if s]
    for i, s in enumerate(segs):
        if s == "questions" and i + 2 < len(segs):
            if segs[i + 1] == "tagged":
                return segs[i + 2]
        if s == "tags" and i + 1 < len(segs):
            return segs[i + 1]
    return None


def se_parse_user_id(url):
    try:
        path = urlparse(url).path
        segs = [s for s in path.split("/") if s]
        for i, s in enumerate(segs):
            if s in ("users", "u") and i + 1 < len(segs):
                try:
                    return int(segs[i + 1])
                except ValueError:
                    continue
    except Exception:
        pass
    return None


# ============================================================================
#  ANTI-DETECTION STATE
# ============================================================================

class _Rotator:
    """Thread-safe round-robin rotator with weights."""

    def __init__(self, items, weights=None):
        self.items = list(items)
        self.weights = list(weights) if weights else [1.0] * len(items)
        self._lock = threading.Lock()
        self._weights = list(self.weights)
        self._last_idx = -1
        self._recent = deque(maxlen=max(4, len(items)))

    def next(self):
        with self._lock:
            total = sum(self._weights)
            if total <= 0:
                self._weights = list(self.weights)
                total = sum(self._weights)
            r = random.uniform(0, total)
            upto = 0.0
            for i, w in enumerate(self._weights):
                upto += w
                if upto >= r:
                    self._last_idx = i
                    self._recent.append(i)
                    return self.items[i]
            return random.choice(self.items)

    def penalize(self, item):
        with self._lock:
            try:
                i = self.items.index(item)
            except ValueError:
                return
            self._weights[i] = max(0.05, self._weights[i] * 0.5)

    def reward(self, item):
        with self._lock:
            try:
                i = self.items.index(item)
            except ValueError:
                return
            self._weights[i] = min(3.0, self._weights[i] * 1.1)


_UA_ROTATOR = _Rotator(SE_USER_AGENTS)
_IMPERSONATE_ROTATOR = _Rotator(SE_IMPERSONATES)
_ENDPOINT_ROTATOR = _Rotator(SE_ENDPOINTS)


# ============================================================================
#  QUOTA TRACKER — persistent, keyless friendly
# ============================================================================

class QuotaTracker:
    def __init__(self, path=None):
        self.path = Path(path or (FolderManager.CACHE / SE_QUOTA_FILE))
        self.data = {}
        self._lock = threading.Lock()
        self._load()

    def _day_key(self):
        return time.strftime("%Y-%m-%d", time.gmtime())

    def _load(self):
        try:
            if self.path.exists():
                with open(self.path, "rb") as f:
                    self.data = orjson.loads(f.read())
        except Exception:
            self.data = {}

    def _save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write(self.path, orjson.dumps(self.data))
        except Exception:
            pass

    def used_today(self):
        d = self.data.get("day")
        if d != self._day_key():
            return 0
        return self.data.get("count", 0)

    def remaining(self, cap=300):
        return max(0, cap - self.used_today())

    def record(self, n=1):
        with self._lock:
            day = self._day_key()
            if self.data.get("day") != day:
                self.data = {"day": day, "count": 0}
            self.data["count"] = self.data.get("count", 0) + n
            if self.data["count"] % 10 == 0:
                self._save()

    def update_from_response(self, quota_remaining, quota_max):
        with self._lock:
            self.data["quota_remaining"] = quota_remaining
            self.data["quota_max"] = quota_max
            self.data["last_update"] = time.time()
            self._save()

    def is_exhausted(self, cap=300):
        if self.data.get("quota_remaining") is not None:
            return self.data["quota_remaining"] < SE_QUOTA_SAFE_MARGIN
        return self.used_today() >= (cap - SE_QUOTA_SAFE_MARGIN)


# ============================================================================
#  BREAKER — per-endpoint circuit breaker
# ============================================================================

class Breaker:
    def __init__(self, path=None):
        self.path = Path(path or (FolderManager.CACHE / SE_BREAKER_FILE))
        self.state = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        try:
            if self.path.exists():
                with open(self.path, "rb") as f:
                    self.state = orjson.loads(f.read())
        except Exception:
            self.state = {}

    def _save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write(self.path, orjson.dumps(self.state))
        except Exception:
            pass

    def is_open(self, endpoint):
        entry = self.state.get(endpoint)
        if not entry:
            return False
        if entry.get("open_until", 0) > time.time():
            return True
        return False

    def record_failure(self, endpoint):
        with self._lock:
            entry = self.state.setdefault(endpoint, {"failures": 0, "open_until": 0})
            entry["failures"] = entry.get("failures", 0) + 1
            if entry["failures"] >= 5:
                entry["open_until"] = time.time() + 60
                entry["failures"] = 0
                _log("breaker opened for %s", endpoint, level="warning")
            self._save()

    def record_success(self, endpoint):
        with self._lock:
            if endpoint in self.state:
                self.state[endpoint]["failures"] = 0
                self.state[endpoint]["open_until"] = 0


# ============================================================================
#  STATS
# ============================================================================

class Stats:
    def __init__(self, path=None):
        self.path = Path(path or (FolderManager.CACHE / SE_STATS_FILE))
        self.data = {
            "total_requests": 0,
            "total_success": 0,
            "total_failure": 0,
            "total_429": 0,
            "total_backoff_honored": 0,
            "total_retries": 0,
            "endpoints": defaultdict(int),
            "uas": defaultdict(int),
            "impersonates": defaultdict(int),
            "latency_ms": [],
        }
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        try:
            if self.path.exists():
                with open(self.path, "rb") as f:
                    self.data.update(orjson.loads(f.read()))
        except Exception:
            pass

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = dict(self.data)
            payload["latency_ms"] = payload.get("latency_ms", [])[-500:]
            if isinstance(payload.get("endpoints"), dict):
                payload["endpoints"] = dict(payload["endpoints"])
            if isinstance(payload.get("uas"), dict):
                payload["uas"] = dict(payload["uas"])
            if isinstance(payload.get("impersonates"), dict):
                payload["impersonates"] = dict(payload["impersonates"])
            _atomic_write(self.path, orjson.dumps(payload, default=str))
        except Exception:
            pass

    def tick(self, endpoint=None, ua=None, impersonate=None, latency_ms=None,
             ok=True, status=200):
        with self._lock:
            self.data["total_requests"] += 1
            if ok:
                self.data["total_success"] += 1
            else:
                self.data["total_failure"] += 1
            if status == 429:
                self.data["total_429"] += 1
            if endpoint:
                self.data["endpoints"][endpoint] = (
                    self.data["endpoints"].get(endpoint, 0) + 1
                )
            if ua:
                self.data["uas"][ua[:32]] = self.data["uas"].get(ua[:32], 0) + 1
            if impersonate:
                self.data["impersonates"][impersonate] = (
                    self.data["impersonates"].get(impersonate, 0) + 1
                )
            if latency_ms:
                self.data["latency_ms"].append(latency_ms)
                if len(self.data["latency_ms"]) > 500:
                    self.data["latency_ms"] = self.data["latency_ms"][-500:]

    def summary(self):
        with self._lock:
            lat = self.data.get("latency_ms", [])
            return {
                "total": self.data["total_requests"],
                "success": self.data["total_success"],
                "failure": self.data["total_failure"],
                "429": self.data["total_429"],
                "backoff_honored": self.data["total_backoff_honored"],
                "retries": self.data["total_retries"],
                "median_latency_ms": round(statistics.median(lat), 1) if lat else 0,
                "endpoints": dict(self.data["endpoints"]),
                "impersonates": dict(self.data["impersonates"]),
            }


_QUOTA = QuotaTracker()
_BREAKER = Breaker()
_STATS = Stats()


# ============================================================================
#  JITTER + BACKOFF
# ============================================================================

def _jitter_delay():
    return random.uniform(SE_MIN_JITTER, SE_MAX_JITTER)


def _backoff_delay(attempt, base=SE_BACKOFF_BASE, cap=SE_BACKOFF_MAX):
    raw = min(base ** attempt, cap)
    return random.uniform(0, raw)


def _sleep_sync(seconds):
    try:
        time.sleep(seconds)
    except Exception:
        pass


async def _sleep_async(seconds):
    try:
        await asyncio.sleep(seconds)
    except Exception:
        pass


# ============================================================================
#  HEADER BUILDER
# ============================================================================

def _build_headers(accept_gzip=True):
    ua = _UA_ROTATOR.next()
    headers = OrderedDict()
    headers["User-Agent"] = ua
    headers["Accept"] = "application/json"
    if accept_gzip:
        headers["Accept-Encoding"] = random.choice([
            "gzip, deflate",
            "gzip",
            "gzip, deflate, br",
        ])
    else:
        headers["Accept-Encoding"] = "identity"
    headers["Accept-Language"] = random.choice([
        "en-US,en;q=0.9",
        "en-GB,en;q=0.9",
        "en-CA,en;q=0.9",
        "en-US,en;q=0.8",
    ])
    headers["Cache-Control"] = random.choice([
        "no-cache", "max-age=0", "no-store",
    ])
    headers["Connection"] = "keep-alive"
    headers["DNT"] = "1"
    return ua, headers


def _decode_body(body):
    if not body:
        return None
    if body[:2] == b"\x1f\x8b":
        try:
            body = gzip.decompress(body)
        except Exception:
            pass
    try:
        return orjson.loads(body)
    except Exception:
        pass
    try:
        body = zlib.decompress(body)
        return orjson.loads(body)
    except Exception:
        return None


def _pick_endpoint():
    for _ in range(len(SE_ENDPOINTS)):
        ep = _ENDPOINT_ROTATOR.next()
        if not _BREAKER.is_open(ep):
            return ep
    return SE_PRIMARY_ENDPOINT


# ============================================================================
#  ASYNC CORE FETCHER
# ============================================================================

async def _se_get_async(session, path, params, timeout=None, retries=None):
    """Core fetcher with exponential backoff + full jitter + breaker + retry."""
    retries = retries if retries is not None else SE_MAX_RETRIES
    timeout = timeout or SE_BASE_TIMEOUT
    endpoint = _pick_endpoint()
    url = f"{endpoint}{path}"
    last_err = None

    if _QUOTA.is_exhausted():
        return None, "quota_exhausted"

    for attempt in range(retries):
        if _BREAKER.is_open(endpoint):
            endpoint = _pick_endpoint()
            url = f"{endpoint}{path}"
        ua, headers = _build_headers()
        impersonate = _IMPERSONATE_ROTATOR.next()
        t0 = time.monotonic()
        try:
            await _sleep_async(_jitter_delay())
            r = await session.get(
                url, params=params, headers=headers,
                timeout=timeout, allow_redirects=True,
            )
            latency_ms = (time.monotonic() - t0) * 1000.0
            status = r.status_code
            _STATS.tick(endpoint=endpoint, ua=ua,
                         impersonate=impersonate,
                         latency_ms=latency_ms, ok=status == 200,
                         status=status)
            _QUOTA.record()

            if status == 429:
                retry_after = r.headers.get("retry-after")
                delay = None
                if retry_after:
                    try:
                        delay = float(retry_after)
                    except Exception:
                        delay = None
                if delay is None:
                    delay = _backoff_delay(attempt + 1, cap=60.0)
                _STATS.data["total_retries"] += 1
                await _sleep_async(delay)
                last_err = f"429 after {delay:.1f}s"
                continue

            if status == 403:
                _UA_ROTATOR.penalize(ua)
                _BREAKER.record_failure(endpoint)
                delay = _backoff_delay(attempt + 1)
                await _sleep_async(delay)
                last_err = "403"
                continue

            if status >= 500:
                _BREAKER.record_failure(endpoint)
                delay = _backoff_delay(attempt + 1)
                await _sleep_async(delay)
                last_err = f"status {status}"
                continue

            if status != 200:
                return None, f"status {status}"

            _BREAKER.record_success(endpoint)
            _UA_ROTATOR.reward(ua)
            _ENDPOINT_ROTATOR.reward(endpoint)

            data = _decode_body(r.content or b"")
            if data is None:
                last_err = "decode_failed"
                continue

            if isinstance(data, dict):
                qr = data.get("quota_remaining")
                qm = data.get("quota_max")
                if qr is not None:
                    _QUOTA.update_from_response(qr, qm)
                backoff = data.get("backoff")
                if backoff:
                    try:
                        b = float(backoff)
                    except Exception:
                        b = 0
                    if b > 0:
                        _STATS.data["total_backoff_honored"] += 1
                        _sleep_sync(b + random.uniform(0.5, 2.0))

            return data, None
        except asyncio.TimeoutError:
            _STATS.tick(endpoint=endpoint, ua=ua, impersonate=impersonate,
                         ok=False, status=0)
            last_err = "timeout"
            _BREAKER.record_failure(endpoint)
            await _sleep_async(_backoff_delay(attempt + 1))
        except Exception as e:
            _STATS.tick(endpoint=endpoint, ua=ua, impersonate=impersonate,
                         ok=False, status=0)
            last_err = repr(e)[:160]
            _BREAKER.record_failure(endpoint)
            await _sleep_async(_backoff_delay(attempt + 1))

    return None, last_err or "unknown"


# ============================================================================
#  SYNC CORE FETCHER
# ============================================================================

def _se_get_sync(session, path, params, timeout=None, retries=None):
    retries = retries if retries is not None else SE_MAX_RETRIES
    timeout = timeout or SE_BASE_TIMEOUT
    endpoint = _pick_endpoint()
    url = f"{endpoint}{path}"
    last_err = None

    if _QUOTA.is_exhausted():
        return None, "quota_exhausted"

    for attempt in range(retries):
        if _BREAKER.is_open(endpoint):
            endpoint = _pick_endpoint()
            url = f"{endpoint}{path}"
        ua, headers = _build_headers()
        t0 = time.monotonic()
        try:
            _sleep_sync(_jitter_delay())
            r = session.get(
                url, params=params, headers=headers, timeout=timeout,
            )
            latency_ms = (time.monotonic() - t0) * 1000.0
            status = r.status_code
            _STATS.tick(endpoint=endpoint, ua=ua,
                         latency_ms=latency_ms, ok=status == 200,
                         status=status)
            _QUOTA.record()

            if status == 429:
                retry_after = r.headers.get("retry-after")
                try:
                    delay = float(retry_after) if retry_after else None
                except Exception:
                    delay = None
                if delay is None:
                    delay = _backoff_delay(attempt + 1, cap=60.0)
                _STATS.data["total_retries"] += 1
                _sleep_sync(delay)
                last_err = f"429 after {delay:.1f}s"
                continue

            if status == 403:
                _UA_ROTATOR.penalize(ua)
                _BREAKER.record_failure(endpoint)
                _sleep_sync(_backoff_delay(attempt + 1))
                last_err = "403"
                continue

            if status >= 500:
                _BREAKER.record_failure(endpoint)
                _sleep_sync(_backoff_delay(attempt + 1))
                last_err = f"status {status}"
                continue

            if status != 200:
                return None, f"status {status}"

            _BREAKER.record_success(endpoint)
            _UA_ROTATOR.reward(ua)
            _ENDPOINT_ROTATOR.reward(endpoint)

            data = _decode_body(r.content or b"")
            if data is None:
                last_err = "decode_failed"
                continue

            if isinstance(data, dict):
                qr = data.get("quota_remaining")
                qm = data.get("quota_max")
                if qr is not None:
                    _QUOTA.update_from_response(qr, qm)
                backoff = data.get("backoff")
                if backoff:
                    try:
                        b = float(backoff)
                    except Exception:
                        b = 0
                    if b > 0:
                        _STATS.data["total_backoff_honored"] += 1
                        _sleep_sync(b + random.uniform(0.5, 2.0))

            return data, None
        except Exception as e:
            _STATS.tick(endpoint=endpoint, ua=ua, ok=False, status=0)
            last_err = repr(e)[:160]
            _BREAKER.record_failure(endpoint)
            _sleep_sync(_backoff_delay(attempt + 1))

    return None, last_err or "unknown"


# ============================================================================
#  API METHOD WRAPPERS
# ============================================================================

async def _se_get_question_async(session, site, qid, filter_=SE_WITHBODY):
    params = {
        "site": site,
        "filter": filter_,
        "order": "desc",
        "sort": "votes",
    }
    data, err = await _se_get_async(session, f"/questions/{qid}", params)
    if err or not data:
        return None, err or "no_data"
    items = data.get("items") or []
    if not items:
        return None, "no_items"
    return items[0], None


async def _se_get_answers_async(session, site, qid, filter_=SE_WITHBODY,
                                  max_answers=None, sort="votes"):
    max_answers = max_answers or SE_MAX_ANSWERS
    params = {
        "site": site,
        "filter": filter_,
        "order": "desc",
        "sort": sort,
        "pagesize": min(max_answers, 100),
    }
    data, err = await _se_get_async(
        session, f"/questions/{qid}/answers", params,
    )
    if err or not data:
        return [], err or "no_data"
    return data.get("items") or [], None


async def _se_get_comments_async(session, site, qid, filter_="withbody"):
    params = {
        "site": site,
        "filter": filter_,
        "order": "desc",
        "sort": "votes",
        "pagesize": SE_MAX_COMMENTS,
    }
    data, err = await _se_get_async(
        session, f"/questions/{qid}/comments", params,
    )
    if err or not data:
        return [], err or "no_data"
    return data.get("items") or [], None


async def _se_get_related_async(session, site, qid):
    data, err = await _se_get_async(
        session, f"/questions/{qid}/related", {"site": site},
    )
    if err or not data:
        return [], err
    return data.get("items") or [], None


async def _se_search_async(session, site, query, tagged=None, max_results=30):
    params = {
        "site": site,
        "filter": SE_WITHBODY,
        "order": "desc",
        "sort": "relevance",
        "pagesize": min(max_results, 100),
    }
    if tagged:
        params["tagged"] = tagged
    if query:
        params["q"] = query
    data, err = await _se_get_async(session, "/search/advanced", params)
    if err or not data:
        return [], err
    return data.get("items") or [], None


async def _se_tag_async(session, site, tag, max_results=30, sort="votes"):
    params = {
        "site": site,
        "filter": SE_WITHBODY,
        "order": "desc",
        "sort": sort,
        "tagged": tag,
        "pagesize": min(max_results, 100),
    }
    data, err = await _se_get_async(session, "/questions", params)
    if err or not data:
        return [], err
    return data.get("items") or [], None


def _se_get_question_sync(session, site, qid, filter_=SE_WITHBODY):
    params = {
        "site": site, "filter": filter_,
        "order": "desc", "sort": "votes",
    }
    data, err = _se_get_sync(session, f"/questions/{qid}", params)
    if err or not data:
        return None, err or "no_data"
    items = data.get("items") or []
    if not items:
        return None, "no_items"
    return items[0], None


def _se_get_answers_sync(session, site, qid, filter_=SE_WITHBODY,
                          max_answers=None):
    max_answers = max_answers or SE_MAX_ANSWERS
    params = {
        "site": site, "filter": filter_,
        "order": "desc", "sort": "votes",
        "pagesize": min(max_answers, 100),
    }
    data, err = _se_get_sync(session, f"/questions/{qid}/answers", params)
    if err or not data:
        return [], err or "no_data"
    return data.get("items") or [], None


def _se_get_comments_sync(session, site, qid):
    params = {
        "site": site, "filter": "withbody",
        "order": "desc", "sort": "votes",
        "pagesize": SE_MAX_COMMENTS,
    }
    data, err = _se_get_sync(session, f"/questions/{qid}/comments", params)
    if err or not data:
        return [], err or "no_data"
    return data.get("items") or [], None


def _se_get_related_sync(session, site, qid):
    data, err = _se_get_sync(session, f"/questions/{qid}/related", {"site": site})
    if err or not data:
        return [], err
    return data.get("items") or [], None


def _se_tag_sync(session, site, tag, max_results=30, sort="votes"):
    params = {
        "site": site, "filter": SE_WITHBODY,
        "order": "desc", "sort": sort,
        "tagged": tag,
        "pagesize": min(max_results, 100),
    }
    data, err = _se_get_sync(session, "/questions", params)
    if err or not data:
        return [], err
    return data.get("items") or [], None


# ============================================================================
#  PUBLIC ASYNC ENTRY POINTS
# ============================================================================

async def se_fetch_question(site, question_id, session):
    return await _se_get_question_async(session, site, question_id)


async def se_fetch_answers(site, question_id, session, max_answers=SE_MAX_ANSWERS):
    return await _se_get_answers_async(session, site, question_id,
                                         max_answers=max_answers)


async def se_fetch_comments(site, question_id, session):
    return await _se_get_comments_async(session, site, question_id)


async def se_fetch_related(site, question_id, session):
    return await _se_get_related_async(session, site, question_id)


async def se_fetch_search(site, query, session, max_results=30):
    return await _se_search_async(session, site, query,
                                    max_results=max_results)


async def se_fetch_tag(site, tag, session, max_results=30):
    return await _se_tag_async(session, site, tag, max_results=max_results)


# ============================================================================
#  SYNC ENTRY POINTS
# ============================================================================

def se_fetch_question_sync(session, site, question_id):
    return _se_get_question_sync(session, site, question_id)


def se_fetch_answers_sync(session, site, question_id, max_answers=SE_MAX_ANSWERS):
    return _se_get_answers_sync(session, site, question_id,
                                  max_answers=max_answers)


def se_fetch_comments_sync(session, site, question_id):
    return _se_get_comments_sync(session, site, question_id)


def se_fetch_related_sync(session, site, question_id):
    return _se_get_related_sync(session, site, question_id)


def se_fetch_tag_sync(session, site, tag, max_results=30):
    return _se_tag_sync(session, site, tag, max_results=max_results)


# ============================================================================
#  HTML SANITIZER
# ============================================================================

def _strip_html(html):
    if not html:
        return ""
    try:
        from selectolax.lexbor import LexborHTMLParser
        tree = LexborHTMLParser(html)
        for sel in ("script", "style"):
            for n in tree.css(sel):
                try:
                    n.decompose()
                except Exception:
                    pass
        text = tree.text(strip=True) or ""
        return re.sub(r"[ \t]+", " ", text).strip()
    except Exception:
        return re.sub(r"<[^>]+>", " ", html).strip()


# ============================================================================
#  RECORD BUILDER
# ============================================================================

def _content_hash(text):
    return hashlib.blake2b(
        str(text).encode("utf-8", "ignore"), digest_size=16
    ).hexdigest()


def _basic_record(url, site, title, sections, meta, source):
    full = "\n\n".join(s.get("text", "") for s in sections if s.get("text"))
    wc = len(full.split())
    return {
        "id": _content_hash(full),
        "url": url,
        "canonical_url": meta.get("link") or url,
        "domain": _host_of(url),
        "tld": "com" if ".com" in _host_of(url) else "net",
        "title": title,
        "language": "en",
        "language_source": source,
        "published_date": None,
        "updated_date": None,
        "crawled_at": time.time(),
        "content_hash": _content_hash(full),
        "simhash": 0,
        "source_signature": source,
        "idempotency_key": _content_hash(f"{source}::{url}::{meta.get('question_id','')}"),
        "extractor_version": "se-api-2.0",
        "config_hash": "",
        "license": "CC BY-SA 4.0",
        "quality": {},
        "word_count": wc,
        "token_count": int(wc * 1.35),
        "char_count": len(full),
        "sentence_count": full.count("."),
        "reading_time_seconds": round(wc / 200 * 60, 1),
        "flesch_reading_ease": -1.0,
        "flesch_kincaid_grade": -1.0,
        "gunning_fog": -1.0,
        "smog_index": -1.0,
        "automated_readability_index": -1.0,
        "coleman_liau_index": -1.0,
        "dale_chall_score": -1.0,
        "text_standard": "",
        "difficulty": 0,
        "topics": [{"term": t, "score": 1.0} for t in (meta.get("tags") or [])],
        "entities": [],
        "keywords": [],
        "summary": "",
        "sections": sections,
        "chunks": [],
        "links": [],
        "metadata": {"source_type": source, **meta},
        "provenance": {
            "service": source,
            "site": site,
            "endpoint": _pick_endpoint(),
            "quota_remaining": _QUOTA.data.get("quota_remaining"),
        },
        "content": {
            "site_navigation": {"primary": [], "help": [], "actions": []},
            "announcement": None,
            "table_of_contents": [
                {"text": s.get("heading", ""), "anchor": f"#{i}"}
                for i, s in enumerate(sections)
            ],
            "article": {
                "heading": title,
                "tabs": [],
                "notice": "",
                "lead_image": None,
                "intro": (sections[0]["text"][:2000]
                          if sections and sections[0].get("text") else ""),
                "sections": sections,
                "references": [],
                "related_media": None,
                "categories": [{"text": t, "url": None}
                                for t in (meta.get("tags") or [])],
                "published_date": None,
                "updated_date": None,
                "timezone": "UTC",
            },
            "metadata": {"source_type": source},
            "footer_links": [],
        },
        "schema_version": "4.0.0",
        "kind": source,
    }


def se_item_to_record(item, site, url, answers=None, comments=None,
                       related=None):
    """Convert SE question item to full nexus record."""
    title = item.get("title") or ""
    body_html = item.get("body") or ""
    body_text = _strip_html(body_html)
    qid = item.get("question_id") or item.get("id")
    owner = item.get("owner") or {}
    tags = item.get("tags") or []
    link = item.get("link") or url
    created = item.get("creation_date")
    last_activity = item.get("last_activity_date")

    sections = []
    if body_text:
        sections.append({"heading": "Question", "text": body_text[:50000]})

    accepted_id = item.get("accepted_answer_id")
    ordered_answers = []
    if answers:
        accepted = [a for a in answers if a.get("is_accepted")]
        others = [a for a in answers if not a.get("is_accepted")]
        others.sort(key=lambda a: a.get("score", 0), reverse=True)
        ordered_answers = accepted + others
        for i, a in enumerate(ordered_answers[:SE_MAX_ANSWERS]):
            a_body = _strip_html(a.get("body") or "")
            if not a_body:
                continue
            is_accepted = a.get("is_accepted", False)
            heading = ("Accepted Answer" if is_accepted
                        else f"Answer {i+1} (score {a.get('score',0)})")
            sections.append({"heading": heading, "text": a_body[:50000]})

    if comments:
        body_parts = []
        for c in comments[:SE_MAX_COMMENTS]:
            c_body = _strip_html(c.get("body") or "")
            if c_body:
                score = c.get("score", 0)
                body_parts.append(f"[{score}] {c_body}")
        if body_parts:
            sections.append({"heading": "Comments",
                              "text": "\n\n".join(body_parts)[:20000]})

    meta = {
        "source_type": "stack_exchange_api",
        "site": site,
        "question_id": qid,
        "score": item.get("score", 0),
        "view_count": item.get("view_count", 0),
        "answer_count": item.get("answer_count", 0),
        "is_answered": item.get("is_answered", False),
        "accepted_answer_id": accepted_id,
        "tags": tags,
        "owner": {
            "display_name": owner.get("display_name"),
            "reputation": owner.get("reputation"),
            "user_id": owner.get("user_id"),
        },
        "created": created,
        "last_activity": last_activity,
        "link": link,
        "related_question_ids": [r.get("question_id")
                                  for r in (related or [])][:20],
    }

    return _basic_record(url, site, title, sections, meta,
                          "se_api")


# ============================================================================
#  URL-LEVEL ASYNC FETCH (for api_router)
# ============================================================================

async def se_fetch_url(url, impersonate=None):
    site = se_site_for_url(url)
    if not site:
        return None, "not_se_host"
    qid = se_parse_question_id(url)
    if qid is None:
        tag = se_parse_tag(url)
        if tag:
            async with _AsyncSession(
                impersonate=impersonate or _IMPERSONATE_ROTATOR.next(),
                max_clients=2, default_headers=False,
            ) as session:
                items, err = await _se_tag_async(session, site, tag)
                if err or not items:
                    return None, err or "no_items"
                return se_item_to_record(items[0], site, url), None
        return None, "no_question_id"

    async with _AsyncSession(
        impersonate=impersonate or _IMPERSONATE_ROTATOR.next(),
        max_clients=2, default_headers=False,
    ) as session:
        item, err = await _se_get_question_async(session, site, qid)
        if err or not item:
            return None, err or "no_question"
        answers, _ = await _se_get_answers_async(session, site, qid)
        comments, _ = await _se_get_comments_async(session, site, qid)
        related, _ = await _se_get_related_async(session, site, qid)
        return se_item_to_record(item, site, url, answers, comments, related), None


def se_fetch_url_sync(url, impersonate=None):
    try:
        return asyncio.run(se_fetch_url(url, impersonate=impersonate))
    except Exception as e:
        return None, repr(e)


# ============================================================================
#  DIAGNOSTICS
# ============================================================================

def se_stats():
    return _STATS.summary()


def se_quota_status():
    return {
        "used_today": _QUOTA.used_today(),
        "quota_remaining": _QUOTA.data.get("quota_remaining"),
        "quota_max": _QUOTA.data.get("quota_max"),
        "exhausted": _QUOTA.is_exhausted(),
    }


def se_save():
    _STATS.save()
    _QUOTA._save()
    _BREAKER._save()