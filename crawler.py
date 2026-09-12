import os
import re
import gc
import sys
import time
import json
import mmap
import math
import random
import signal
import sqlite3
import hashlib
import shutil
import struct
import heapq
import logging
import tempfile
import subprocess
import threading
import multiprocessing as mp
from logging.handlers import RotatingFileHandler
from pathlib import Path
from collections import defaultdict, OrderedDict, deque, Counter
from dataclasses import dataclass, asdict, field
from urllib.parse import urlparse, urldefrag, urljoin, parse_qs, quote

import orjson
import psutil
from courlan import clean_url, normalize_url, is_navigation_page
from tld import get_tld
from selectolax.lexbor import LexborHTMLParser

from folder_manager import FolderManager, ErrorClassifier, FolderError
from config import (
    MAX_WORKERS, MAX_WORKERS_FAST_MULT, MAX_RSS_MB,
    WORKER_RECYCLE_AFTER_URLS, WORKER_RECYCLE_AFTER_SECONDS,
    SAME_DOMAIN_CONCURRENCY,
    DOMAIN_TOKEN_BUCKET_RATE, DOMAIN_TOKEN_BUCKET_BURST,
    DOMAIN_TOKEN_BUCKET_MIN_RATE, DOMAIN_TOKEN_BUCKET_MAX_RATE,
    DOMAIN_BACKOFF_BASE, DOMAIN_BACKOFF_MAX, DOMAIN_FAILURE_THRESHOLD,
    DOMAIN_COOLDOWN_SECONDS, DOMAIN_RATE_ADAPTIVE, DOMAIN_RATE_PERSIST,
    DOMAIN_RATE_FILE, DOMAIN_RATE_429_FACTOR, DOMAIN_RATE_2XX_FACTOR,
    DOMAIN_RATE_2XX_WINDOW,
    MAX_DEPTH, MAX_LINKS_PER_PAGE, MAX_QUEUE_SIZE,
    CHECKPOINT_EVERY, COMPACT_THRESHOLD, IDLE_TIMEOUT,
    CACHE_CLEAR_INTERVAL, GC_INTERVAL,
    TASK_QUEUE_MAX, RESULT_QUEUE_MAX, LINK_QUEUE_MAX,
    CROSS_DOMAIN_ALLOWLIST, CROSS_DOMAIN_DENYLIST, CROSS_DOMAIN_MAX_HOPS,
    FOLLOW_EXTERNAL, RESPECT_ROBOTS, ROBOTS_CACHE_TTL,
    BLOCKED_RETRY_MIN, BLOCKED_RETRY_MAX, BLOCKED_BACKOFF_MULTIPLIER,
    MAX_BLOCKED_RETRIES, BLOCKED_CHECK_INTERVAL,
    BLOCKED_FINGERPRINT_ROTATE, BLOCKED_PROXY_ROTATE,
    BLOOM_BITS, BLOOM_HASHES, SIMHASH_BITS, SIMHASH_BANDS,
    SIMHASH_HAMMING, MINHASH_PERMS, MINHASH_JACCARD,
    SEMANTIC_DEDUP_ENABLED, SEMANTIC_DEDUP_THRESHOLD,
    CHUNK_DEDUP_ENABLED, CHUNK_DEDUP_HAMMING, CHUNK_DEDUP_PREFER_LONGER,
    STATE_FILE, QUEUE_FILE, DONE_FILE, ERRORS_FILE, BLOCKED_FILE,
    DEDUP_DB, BLOOM_FILE, RESUME_JOURNAL, PID_FILE, LOG_FILE,
    OUTPUT_PATH, CACHE_DIR,
    AGENT_INDEX_DIR, AGENT_MANIFEST, AGENT_SHARDS_DIR,
    AGENT_QUARANTINE_DIR, AGENT_SCHEMA_VERSION,
    AGENT_MANIFEST_WRITE_INTERVAL, AGENT_MANIFEST_INCLUDE_COUNTS,
    AGENT_MANIFEST_INCLUDE_SHARDS, AGENT_MANIFEST_INCLUDE_CONFIG_HASH,
    AGENT_MANIFEST_INCLUDE_SCHEMA_VERSION, AGENT_MANIFEST_INCLUDE_CATEGORY_COUNTS,
    AGENT_SHARD_ENABLED, AGENT_SHARD_SIZE_RECORDS, AGENT_SHARD_SIZE_BYTES,
    AGENT_SHARD_NAMING,
    AGENT_QUARANTINE_ENABLED, AGENT_QUARANTINE_LOW_QUALITY,
    AGENT_QUARANTINE_EMPTY_CONTENT,
    QUARANTINE_CATEGORIES, JS_REQUIRED_MARKERS,
    LOG_LEVEL, LOG_FORMAT, LOG_ROTATE_BYTES, LOG_BACKUP_COUNT,
    LOG_TO_FILE, LOG_TO_CONSOLE,
    TELEMETRY_ENABLED, TELEMETRY_INTERVAL,
    TELEMETRY_INCLUDE_CATEGORY_COUNTS,
    CACHE_TTL_SECONDS,
    IS_WIN, IS_LINUX, CONFIG_VERSION, CONFIG_GENERATION,
    STRICT_CONFIG_ENFORCEMENT, FORCE_RESUME_OVERRIDE_FLAG,
    API_ROUTER_ENABLED,
)

_PRIORITY_SAME = 0
_PRIORITY_CROSS = 1
_SENTINEL = None
_LOG = logging.getLogger("crawler")
_LOG_CONFIGURED = False

FRONTIER_DRAIN_PER_TICK = 400
FRONTIER_HIGH_WATER = 0.9
FRONTIER_PRIORITY_DECAY_INTERVAL = 200
BOOTSTRAP_CACHE_TTL = 86400
YIELD_WINDOW = 500
ADAPTIVE_CONCURRENCY_INTERVAL = 60


# ============================================================================
#  LOGGING
# ============================================================================

def _setup_logging():
    global _LOG_CONFIGURED
    if _LOG_CONFIGURED:
        return
    _LOG.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    fmt = logging.Formatter(LOG_FORMAT)
    if LOG_TO_CONSOLE:
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        _LOG.addHandler(ch)
    if LOG_TO_FILE:
        try:
            Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
            fh = RotatingFileHandler(
                LOG_FILE, maxBytes=LOG_ROTATE_BYTES,
                backupCount=LOG_BACKUP_COUNT, encoding="utf-8",
            )
            fh.setFormatter(fmt)
            _LOG.addHandler(fh)
        except Exception:
            pass
    _LOG_CONFIGURED = True


def _log(msg, *args, level=logging.INFO):
    try:
        _LOG.log(level, msg, *args)
    except Exception:
        pass


# ============================================================================
#  BLOOM FILTER
# ============================================================================

class BloomFilter:
    __slots__ = ("bits", "nbits", "nhash", "count")

    def __init__(self, nbits=BLOOM_BITS, nhash=BLOOM_HASHES):
        self.nbits = nbits
        self.nhash = nhash
        self.bits = bytearray(nbits >> 3)
        self.count = 0

    def _hashes(self, data):
        h1 = int.from_bytes(hashlib.blake2b(data, digest_size=8).digest(), "big")
        h2 = int.from_bytes(
            hashlib.blake2b(data, digest_size=8, person=b"b2").digest(), "big"
        )
        for i in range(self.nhash):
            yield (h1 + i * h2) % self.nbits

    def add(self, key):
        data = key.encode("utf-8", "ignore")
        for pos in self._hashes(data):
            self.bits[pos >> 3] |= 1 << (pos & 7)
        self.count += 1

    def __contains__(self, key):
        data = key.encode("utf-8", "ignore")
        for pos in self._hashes(data):
            if not (self.bits[pos >> 3] & (1 << (pos & 7))):
                return False
        return True

    def save(self, path):
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(struct.pack("<QQ", self.nbits, self.nhash))
            f.write(self.bits)
        os.replace(tmp, path)

    @classmethod
    def load(cls, path):
        if not os.path.exists(path):
            return cls()
        try:
            with open(path, "rb") as f:
                nbits, nhash = struct.unpack("<QQ", f.read(16))
                bits = bytearray(f.read())
            bf = cls(nbits, nhash)
            bf.bits = bits
            return bf
        except Exception:
            return cls()


# ============================================================================
#  SIMHASH / MINHASH
# ============================================================================

def _simhash64(tokens):
    if not tokens:
        return 0
    v = [0] * 64
    for tok in tokens:
        h = int.from_bytes(
            hashlib.blake2b(tok.encode("utf-8", "ignore"), digest_size=8).digest(),
            "big",
        )
        for i in range(64):
            v[i] += 1 if (h >> i) & 1 else -1
    out = 0
    for i in range(64):
        if v[i] > 0:
            out |= 1 << i
    return out


def _simhash_bands(h):
    band_bits = SIMHASH_BITS // SIMHASH_BANDS
    mask = (1 << band_bits) - 1
    for b in range(SIMHASH_BANDS):
        yield b, (h >> (b * band_bits)) & mask


def _hamming(a, b):
    return (a ^ b).bit_count()


_MINHASH_SEEDS = [
    int.from_bytes(hashlib.blake2b(str(i).encode(), digest_size=8).digest(), "big")
    for i in range(MINHASH_PERMS)
]


def _minhash_signature(tokens):
    if not tokens:
        return None
    sig = []
    for seed in _MINHASH_SEEDS:
        m = min(
            seed ^ int.from_bytes(
                hashlib.blake2b(t.encode("utf-8", "ignore"), digest_size=8).digest(),
                "big",
            )
            for t in tokens
        )
        sig.append(m)
    return sig


def _minhash_jaccard(a, b):
    if not a or not b:
        return 0.0
    return sum(1 for x, y in zip(a, b) if x == y) / len(a)


# ============================================================================
#  DEDUP STORE
# ============================================================================

class DedupStore:
    def __init__(self, path=DEDUP_DB):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.bloom = BloomFilter.load(BLOOM_FILE)
        self.conn = sqlite3.connect(path, timeout=60, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA temp_store=MEMORY")
        self.conn.execute("PRAGMA mmap_size=268435456")
        self._pending = 0
        self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS urls "
            "(h TEXT PRIMARY KEY, url TEXT NOT NULL, tld TEXT, ts REAL)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS content "
            "(h TEXT PRIMARY KEY, simhash INTEGER NOT NULL, title_h TEXT, ts REAL)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS simhash_bands "
            "(band INTEGER NOT NULL, value INTEGER NOT NULL, "
            "content_h TEXT NOT NULL, PRIMARY KEY (band, value, content_h))"
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bands ON simhash_bands(band, value)")
        cur.execute(
            "CREATE TABLE IF NOT EXISTS minhash "
            "(content_h TEXT PRIMARY KEY, sig BLOB NOT NULL)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS idempotency "
            "(key TEXT PRIMARY KEY, url TEXT, ts REAL)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS api_routes "
            "(host TEXT PRIMARY KEY, has_route INT, api_type TEXT, ts REAL)"
        )
        self.conn.commit()

    def url_hash(self, url):
        return hashlib.blake2b(url.encode("utf-8", "ignore"), digest_size=16).hexdigest()

    def canonical(self, url):
        try:
            c = clean_url(url)
            if not c:
                return None
            n = normalize_url(c)
            return n or c
        except Exception:
            return None

    def seen_url(self, url):
        canon = self.canonical(url)
        if not canon:
            return True
        h = self.url_hash(canon)
        if h in self.bloom:
            return True
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM urls WHERE h = ? LIMIT 1", (h,))
        return cur.fetchone() is not None

    def mark_url(self, url):
        canon = self.canonical(url)
        if not canon:
            return
        h = self.url_hash(canon)
        self.bloom.add(h)
        try:
            tld = get_tld(canon, fix_protocol=True, fail_silently=True) or ""
        except Exception:
            tld = ""
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO urls(h, url, tld, ts) VALUES (?, ?, ?, ?)",
            (h, canon, tld, time.time()),
        )
        self._pending += 1
        if self._pending >= 500:
            self.conn.commit()
            self._pending = 0

    def remember_api_route(self, host, has_route, api_type=""):
        try:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO api_routes(host, has_route, api_type, ts) "
                "VALUES (?, ?, ?, ?)",
                (host, 1 if has_route else 0, api_type, time.time()),
            )
        except Exception:
            pass

    def lookup_api_route(self, host, ttl=604800):
        try:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT has_route, api_type, ts FROM api_routes WHERE host = ? LIMIT 1",
                (host,),
            )
            row = cur.fetchone()
            if not row:
                return None
            if time.time() - row[2] > ttl:
                return None
            return {"has_route": bool(row[0]), "api_type": row[1]}
        except Exception:
            return None

    def commit(self):
        try:
            self.conn.commit()
        except Exception:
            pass
        self._pending = 0

    def close(self):
        try:
            self.commit()
            self.bloom.save(BLOOM_FILE)
            self.conn.close()
        except Exception:
            pass


# ============================================================================
#  CRAWL STATE
# ============================================================================

@dataclass
class CrawlState:
    generation: int = 0
    started_at: float = 0.0
    last_checkpoint: float = 0.0
    enqueued: int = 0
    completed: int = 0
    failed: int = 0
    dup: int = 0
    blocked: int = 0
    blocked_retried: int = 0
    blocked_gave_up: int = 0
    queue_dropped: int = 0
    depth_reached: int = 0
    quarantined: int = 0
    traps_detected: int = 0
    circuit_opened: int = 0
    api_routed: int = 0
    api_discovered: int = 0
    bootstrap_discovered: int = 0
    worker_scale_events: int = 0
    seeds_hash: str = ""
    config_version: str = CONFIG_VERSION
    config_generation: int = CONFIG_GENERATION
    version: int = 1


def _atomic_write(path, data):
    tmp = path + ".tmp"
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _read_state():
    if not os.path.exists(STATE_FILE):
        return CrawlState()
    try:
        with open(STATE_FILE, "rb") as f:
            obj = orjson.loads(f.read())
            return CrawlState(
                **{k: obj.get(k) for k in CrawlState.__dataclass_fields__ if k in obj}
            )
    except Exception:
        return CrawlState()


def _save_state(state):
    _atomic_write(STATE_FILE, orjson.dumps(asdict(state)))


# ============================================================================
#  MERCATOR FRONTIER — with priority decay
# ============================================================================

class MercatorFrontier:
    FRONT_BANDS = 8

    def __init__(self, cap=MAX_QUEUE_SIZE):
        self.cap = cap
        self.front = [deque() for _ in range(self.FRONT_BANDS)]
        self.seen_local = set()
        self._counter = 0
        self._total = 0
        self._last_decay = time.monotonic()

    def _band_for(self, priority, depth, score=0.0):
        if score > 0.7:
            base = 0
        elif score > 0.4:
            base = 2
        elif priority == _PRIORITY_SAME:
            base = 3
        else:
            base = 5
        return min(self.FRONT_BANDS - 1, base + min(depth, 3))

    def push(self, url, depth, priority, score=0.0):
        if url in self.seen_local:
            return False
        if self._total >= self.cap:
            return False
        self.seen_local.add(url)
        self._counter += 1
        entry = [depth, priority, self._counter, url, score, time.monotonic()]
        band = self._band_for(priority, depth, score)
        self.front[band].append(entry)
        self._total += 1
        return True

    def pop(self):
        for band in range(self.FRONT_BANDS):
            q = self.front[band]
            if not q:
                continue
            entry = q.popleft()
            self._total -= 1
            return entry[3], entry[0], entry[1], entry[4]
        return None

    def decay(self, threshold_seconds=600.0):
        """Age-based boost: items in frontier for > threshold get one band up."""
        now = time.monotonic()
        if now - self._last_decay < FRONTIER_PRIORITY_DECAY_INTERVAL:
            return 0
        self._last_decay = now
        boosted = 0
        for band in range(self.FRONT_BANDS - 1, 0, -1):
            q = self.front[band]
            if not q:
                continue
            keep = deque()
            for entry in q:
                age = now - entry[5]
                if age > threshold_seconds:
                    self.front[band - 1].append(entry)
                    boosted += 1
                else:
                    keep.append(entry)
            self.front[band] = keep
        return boosted

    def __len__(self):
        return self._total

    def snapshot(self):
        out = []
        for band, q in enumerate(self.front):
            for entry in q:
                out.append((entry[1], entry[0], entry[2], entry[3]))
        return out


# ============================================================================
#  HOST HEALTH SCOREBOARD — replaces static circuit breaker
# ============================================================================

class HostHealth:
    """Score-based health tracking. 1.0 = perfect, 0.0 = dead.
    Health decays on failure, recovers on success. Different thresholds trigger
    different actions:
      >= 0.7 : full speed
      >= 0.4 : reduced rate
      >= 0.2 : one probe per minute
      <  0.2 : skip entirely (open circuit)
    """
    __slots__ = ("score", "last_update", "consecutive_failures",
                 "consecutive_successes", "total_success", "total_failure")

    def __init__(self):
        self.score = 1.0
        self.last_update = time.time()
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.total_success = 0
        self.total_failure = 0

    def record_success(self):
        self.consecutive_failures = 0
        self.consecutive_successes += 1
        self.total_success += 1
        bump = 0.05 * min(self.consecutive_successes, 4)
        self.score = min(1.0, self.score + bump)
        self.last_update = time.time()

    def record_failure(self, weight=1.0):
        self.consecutive_successes = 0
        self.consecutive_failures += 1
        self.total_failure += 1
        drop = 0.15 * weight * min(self.consecutive_failures, 3)
        self.score = max(0.0, self.score - drop)
        self.last_update = time.time()

    def is_usable(self):
        return self.score >= 0.2

    def rate_factor(self):
        if self.score >= 0.7:
            return 1.0
        if self.score >= 0.4:
            return 0.5
        if self.score >= 0.2:
            return 0.15
        return 0.0


class HealthRegistry:
    def __init__(self):
        self._scores = {}
        self._lock = threading.Lock()

    def get(self, host):
        with self._lock:
            h = self._scores.get(host)
            if h is None:
                h = HostHealth()
                self._scores[host] = h
            return h

    def snapshot(self):
        with self._lock:
            return {h: round(v.score, 3) for h, v in self._scores.items()}


# ============================================================================
#  DOMAIN TRACKER — adaptive rate, health-aware
# ============================================================================

class DomainTracker:
    def __init__(self):
        self.rate = {}
        self.tokens = {}
        self.last_refill = {}
        self._load_persisted_rates()

    def _load_persisted_rates(self):
        if not DOMAIN_RATE_PERSIST or not os.path.exists(DOMAIN_RATE_FILE):
            return
        try:
            with open(DOMAIN_RATE_FILE, "rb") as f:
                data = orjson.loads(f.read())
            for host, r in data.items():
                self.rate[host] = float(r)
        except Exception:
            pass

    def persist_rates(self):
        if not DOMAIN_RATE_PERSIST:
            return
        try:
            Path(DOMAIN_RATE_FILE).parent.mkdir(parents=True, exist_ok=True)
            _atomic_write(DOMAIN_RATE_FILE, orjson.dumps(self.rate))
        except Exception:
            pass

    def _get_rate(self, domain):
        if domain not in self.rate:
            self.rate[domain] = DOMAIN_TOKEN_BUCKET_RATE
            self.tokens[domain] = float(DOMAIN_TOKEN_BUCKET_BURST)
            self.last_refill[domain] = time.monotonic()
        return self.rate[domain]

    def _refill(self, domain, health_factor=1.0):
        now = time.monotonic()
        elapsed = now - self.last_refill.get(domain, now)
        self.last_refill[domain] = now
        burst = DOMAIN_TOKEN_BUCKET_BURST
        rate = self._get_rate(domain) * health_factor
        self.tokens[domain] = min(burst, self.tokens.get(domain, burst) + elapsed * rate)

    def try_acquire(self, domain, health_factor=1.0):
        self._refill(domain, health_factor)
        if self.tokens.get(domain, 0.0) >= 1.0:
            self.tokens[domain] -= 1.0
            return True
        return False

    def record_success(self, domain):
        if not DOMAIN_RATE_ADAPTIVE:
            return
        current = self._get_rate(domain)
        new_rate = min(DOMAIN_TOKEN_BUCKET_MAX_RATE, current * DOMAIN_RATE_2XX_FACTOR)
        self.rate[domain] = new_rate

    def record_429(self, domain):
        if not DOMAIN_RATE_ADAPTIVE:
            return
        current = self._get_rate(domain)
        new_rate = max(DOMAIN_TOKEN_BUCKET_MIN_RATE, current * DOMAIN_RATE_429_FACTOR)
        self.rate[domain] = new_rate


# ============================================================================
#  DEAD LETTER QUEUE
# ============================================================================

class DeadLetterQueue:
    def __init__(self, path=None):
        self.path = path or str(FolderManager.CACHE / "dead_letter.jsonl")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._fh = None
        self._size = 0

    def _open(self):
        if self._fh is None:
            self._fh = open(self.path, "ab")
        return self._fh

    def add(self, url, error, attempts):
        try:
            f = self._open()
            f.write(orjson.dumps({
                "url": url, "error": str(error)[:500],
                "attempts": attempts, "ts": time.time(),
            }))
            f.write(b"\n")
            f.flush()
            self._size += 1
        except Exception:
            pass

    def __len__(self):
        return self._size

    def close(self):
        if self._fh:
            try:
                self._fh.close()
            except Exception:
                pass


# ============================================================================
#  TRAP DETECTOR
# ============================================================================

_SESSION_ID_RE = re.compile(
    r"(?:^|[?&])(session_?id|sid|phpsessid|jsessionid|aspsessionid)=[^&#]+",
    re.IGNORECASE,
)
_HEX_TOKEN_RE = re.compile(r"(?:^|[?&])[a-z]+=[a-f0-9]{32,}", re.IGNORECASE)
_CALENDAR_RE = re.compile(r"/(\d{4})/(\d{1,2})/(\d{1,2})")


def _detect_trap(url):
    try:
        u = urlparse(url)
    except Exception:
        return True, "invalid_url"
    segs = [s for s in u.path.split("/") if s]
    if len(segs) >= 3:
        for length in range(1, max(1, len(segs) // 3) + 1):
            pattern = segs[:length]
            reps = 0
            for i in range(0, len(segs) - length + 1, length):
                if segs[i:i + length] == pattern:
                    reps += 1
            if reps >= 4:
                return True, f"repeating_pattern:{'/'.join(pattern)}"
    m = _CALENDAR_RE.search(u.path)
    if m:
        try:
            if int(m.group(1)) > time.gmtime().tm_year + 2:
                return True, "calendar_trap"
        except Exception:
            pass
    if u.query:
        if _SESSION_ID_RE.search(u.query):
            return True, "session_id_in_query"
        if _HEX_TOKEN_RE.search(u.query):
            return True, "hex_token_in_query"
        if len(parse_qs(u.query)) > 30:
            return True, "query_param_explosion"
    if len(url) > 2000:
        return True, "url_too_long"
    if u.path.count("..") > 0:
        return True, "path_traversal"
    return False, ""


# ============================================================================
#  CHANGE DETECTOR
# ============================================================================

class ChangeDetector:
    def __init__(self):
        self.etag = {}
        self.last_modified = {}
        self.change_rate = defaultdict(lambda: 0.1)

    def observe(self, url, headers):
        try:
            host = urlparse(url).netloc
            cur_etag = headers.get("etag")
            cur_lm = headers.get("last-modified")
            changed = False
            prev_etag = self.etag.get(url)
            prev_lm = self.last_modified.get(url)
            if cur_etag and prev_etag and cur_etag != prev_etag:
                changed = True
            elif cur_lm and prev_lm and cur_lm != prev_lm:
                changed = True
            if cur_etag:
                self.etag[url] = cur_etag
            if cur_lm:
                self.last_modified[url] = cur_lm
            if changed:
                alpha = 0.1
                self.change_rate[host] = (1 - alpha) * self.change_rate[host] + alpha
            return changed
        except Exception:
            return False

    def priority_boost(self, url):
        try:
            return min(self.change_rate.get(urlparse(url).netloc, 0.1), 1.0)
        except Exception:
            return 0.0


# ============================================================================
#  YIELD TRACKER — new
# ============================================================================

class YieldTracker:
    """Per-domain and per-path-pattern yield. Yield = useful_records / fetched."""

    def __init__(self):
        self.domain_window = defaultdict(lambda: deque(maxlen=YIELD_WINDOW))
        self.path_window = defaultdict(lambda: deque(maxlen=YIELD_WINDOW))
        self._lock = threading.Lock()

    def record(self, url, useful, blocked=False):
        try:
            p = urlparse(url)
            host = p.netloc
            path_parts = [s for s in p.path.split("/") if s]
            key = "/".join(path_parts[:2]) if path_parts else "/"
        except Exception:
            return
        with self._lock:
            value = 1.0 if useful else (0.0 if not blocked else -0.5)
            self.domain_window[host].append(value)
            self.path_window[(host, key)].append(value)

    def domain_yield(self, host):
        with self._lock:
            window = self.domain_window.get(host)
            if not window:
                return 0.5
            return sum(window) / len(window)

    def path_yield(self, url):
        try:
            p = urlparse(url)
            host = p.netloc
            path_parts = [s for s in p.path.split("/") if s]
            key = "/".join(path_parts[:2]) if path_parts else "/"
        except Exception:
            return 0.5
        with self._lock:
            window = self.path_window.get((host, key))
            if not window:
                return 0.5
            return sum(window) / len(window)


# ============================================================================
#  DOMAIN BOOTSTRAP — new
# ============================================================================

class DomainBootstrap:
    """When a new domain is seen, run discovery once. Produces seed URLs
    from sitemap.xml, robots.txt Sitemap: directives, RSS/Atom feeds, and
    common-path probes. Results are cached per host for BOOTSTRAP_CACHE_TTL."""

    SITEMAP_PATHS = (
        "/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml",
        "/sitemap/sitemap.xml",
    )
    FEED_HINTS = ("rss", "atom", "feed", "json")

    def __init__(self, cache_dir=None):
        self.cache = Path(cache_dir or (FolderManager.CACHE / "bootstrap"))
        self.cache.mkdir(parents=True, exist_ok=True)
        self._mem = {}

    def _cache_path(self, host):
        h = hashlib.blake2b(host.encode(), digest_size=16).hexdigest()
        return self.cache / f"{h}.json"

    def _load(self, host):
        if host in self._mem:
            return self._mem[host]
        path = self._cache_path(host)
        if not path.exists():
            return None
        try:
            if time.time() - path.stat().st_mtime > BOOTSTRAP_CACHE_TTL:
                return None
            with open(path, "rb") as f:
                data = orjson.loads(f.read())
            self._mem[host] = data
            return data
        except Exception:
            return None

    def _save(self, host, data):
        self._mem[host] = data
        try:
            _atomic_write(self._cache_path(host), orjson.dumps(data))
        except Exception:
            pass

    def discover_sync(self, host, root_url, session, max_seeds=200):
        """Blocking discovery. Returns list of seed URLs."""
        cached = self._load(host)
        if cached is not None:
            return cached.get("seeds", [])

        seeds = []
        try:
            for path in self.SITEMAP_PATHS:
                try:
                    r = session.get(root_url + path, timeout=10)
                    if r.status_code != 200:
                        continue
                    body = r.content or b""
                    if b"<urlset" in body or b"<sitemapindex" in body:
                        locs = self._parse_sitemap_locs(body)
                        seeds.extend(locs[:max_seeds])
                        if seeds:
                            break
                except Exception:
                    continue

            try:
                r = session.get(root_url + "/robots.txt", timeout=10)
                if r.status_code == 200:
                    text = r.text
                    for line in text.splitlines():
                        if line.lower().startswith("sitemap:"):
                            sm = line.split(":", 1)[1].strip()
                            if sm.startswith(("http://", "https://")):
                                try:
                                    rs = session.get(sm, timeout=10)
                                    if rs.status_code == 200:
                                        locs = self._parse_sitemap_locs(rs.content or b"")
                                        seeds.extend(locs[:max_seeds])
                                except Exception:
                                    pass
            except Exception:
                pass

            try:
                r = session.get(root_url, timeout=10)
                if r.status_code == 200:
                    tree = LexborHTMLParser(r.text or "")
                    for link in tree.css('link[rel="alternate"]'):
                        t = (link.attributes.get("type") or "").lower()
                        if any(h in t for h in self.FEED_HINTS):
                            href = link.attributes.get("href")
                            if href:
                                seeds.append(urljoin(root_url, href))
            except Exception:
                pass

        except Exception:
            pass

        seeds = list(dict.fromkeys(seeds))[:max_seeds]
        self._save(host, {"seeds": seeds, "ts": time.time(),
                           "count": len(seeds)})
        return seeds

    def _parse_sitemap_locs(self, body):
        locs = []
        try:
            text = body.decode("utf-8", "ignore")
        except Exception:
            return locs
        for m in re.finditer(r"<loc>\s*([^<\s]+)\s*</loc>", text):
            u = m.group(1).strip()
            if u.startswith(("http://", "https://")):
                locs.append(u)
        return locs


# ============================================================================
#  ADAPTIVE CONCURRENCY — new
# ============================================================================

class AdaptiveConcurrency:
    """Tracks observed success rate over rolling window. Adjusts worker count
    up when everything is fast, down when errors spike."""

    def __init__(self, initial, min_workers=2, max_workers=None):
        self.current = initial
        self.min_workers = min_workers
        self.max_workers = max_workers or initial * 2
        self.success = 0
        self.failure = 0
        self.window_start = time.monotonic()
        self.scale_events = 0

    def record(self, ok):
        if ok:
            self.success += 1
        else:
            self.failure += 1

    def tick(self):
        """Call every N seconds. Returns new worker count or None."""
        now = time.monotonic()
        elapsed = now - self.window_start
        if elapsed < ADAPTIVE_CONCURRENCY_INTERVAL:
            return None
        total = self.success + self.failure
        if total < 20:
            self.window_start = now
            self.success = 0
            self.failure = 0
            return None

        rate = self.success / total
        before = self.current
        if rate > 0.9 and self.current < self.max_workers:
            self.current = min(self.max_workers, self.current + 1)
        elif rate < 0.6 and self.current > self.min_workers:
            self.current = max(self.min_workers, self.current - 1)

        self.window_start = now
        self.success = 0
        self.failure = 0
        if self.current != before:
            self.scale_events += 1
            return self.current
        return None


# ============================================================================
#  SHARDED WRITER
# ============================================================================

class ShardedWriter:
    def __init__(self, base_dir=AGENT_SHARDS_DIR):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.shard_index = 0
        self.shard_records = 0
        self.shard_bytes = 0
        self.current_path = None
        self.current_file = None
        self.shard_map = {}
        self._open_shard()

    def _shard_name(self, idx):
        return AGENT_SHARD_NAMING.format(index=idx)

    def _open_shard(self):
        if self.current_file:
            try:
                self.current_file.flush()
                self.current_file.close()
            except Exception:
                pass
        self.current_path = self.base_dir / self._shard_name(self.shard_index)
        self.current_file = open(self.current_path, "wb")
        self.shard_records = 0
        self.shard_bytes = 0

    def _rotate(self):
        self.shard_map[str(self.current_path)] = self.shard_records
        self.shard_index += 1
        self._open_shard()

    def write(self, record):
        try:
            line = orjson.dumps(record, option=orjson.OPT_APPEND_NEWLINE)
        except Exception:
            return False
        try:
            self.current_file.write(line)
            self.shard_records += 1
            self.shard_bytes += len(line)
        except Exception:
            return False
        if (self.shard_records >= AGENT_SHARD_SIZE_RECORDS
                or self.shard_bytes >= AGENT_SHARD_SIZE_BYTES):
            self._rotate()
        return True

    def flush(self):
        if self.current_file:
            try:
                self.current_file.flush()
            except Exception:
                pass

    def close(self):
        if self.current_path:
            self.shard_map[str(self.current_path)] = self.shard_records
        if self.current_file:
            try:
                self.current_file.flush()
                self.current_file.close()
            except Exception:
                pass

    def shards(self):
        out = dict(self.shard_map)
        if self.current_path:
            out[str(self.current_path)] = self.shard_records
        return out


# ============================================================================
#  QUARANTINE WRITER
# ============================================================================

class QuarantineWriter:
    def __init__(self, base_dir=AGENT_QUARANTINE_DIR):
        self.base_dir = Path(base_dir)
        if AGENT_QUARANTINE_ENABLED:
            self.base_dir.mkdir(parents=True, exist_ok=True)
        self.files = {}
        self.counts = defaultdict(int)

    def _handle(self, category):
        if category not in self.files:
            path = self.base_dir / f"{category}.ndjson"
            self.files[category] = open(path, "ab")
        return self.files[category]

    def write(self, category, record):
        if not AGENT_QUARANTINE_ENABLED:
            return
        try:
            h = self._handle(category)
            h.write(orjson.dumps(record, option=orjson.OPT_APPEND_NEWLINE))
            h.flush()
            self.counts[category] += 1
        except Exception:
            pass

    def counts_snapshot(self):
        return dict(self.counts)

    def close(self):
        for f in self.files.values():
            try:
                f.close()
            except Exception:
                pass


# ============================================================================
#  MANIFEST
# ============================================================================

def _write_manifest(state, shards, telemetry_snapshot, config_hash,
                     category_counts=None, extra=None):
    manifest = {
        "schema_version": AGENT_SCHEMA_VERSION,
        "config_version": CONFIG_VERSION,
        "config_generation": CONFIG_GENERATION,
        "config_hash": config_hash if AGENT_MANIFEST_INCLUDE_CONFIG_HASH else None,
        "generated_at": time.time(),
        "state": {
            "generation": state.generation,
            "started_at": state.started_at,
            "enqueued": state.enqueued if AGENT_MANIFEST_INCLUDE_COUNTS else None,
            "completed": state.completed if AGENT_MANIFEST_INCLUDE_COUNTS else None,
            "failed": state.failed if AGENT_MANIFEST_INCLUDE_COUNTS else None,
            "dup": state.dup if AGENT_MANIFEST_INCLUDE_COUNTS else None,
            "blocked": state.blocked if AGENT_MANIFEST_INCLUDE_COUNTS else None,
            "quarantined": state.quarantined if AGENT_MANIFEST_INCLUDE_COUNTS else None,
            "traps_detected": state.traps_detected if AGENT_MANIFEST_INCLUDE_COUNTS else None,
            "api_routed": state.api_routed if AGENT_MANIFEST_INCLUDE_COUNTS else None,
            "api_discovered": state.api_discovered if AGENT_MANIFEST_INCLUDE_COUNTS else None,
            "bootstrap_discovered": state.bootstrap_discovered if AGENT_MANIFEST_INCLUDE_COUNTS else None,
            "worker_scale_events": state.worker_scale_events if AGENT_MANIFEST_INCLUDE_COUNTS else None,
        },
        "telemetry": telemetry_snapshot if TELEMETRY_ENABLED else None,
        "shards": shards if AGENT_MANIFEST_INCLUDE_SHARDS else None,
        "categories": category_counts if AGENT_MANIFEST_INCLUDE_CATEGORY_COUNTS else None,
    }
    if extra:
        manifest["extra"] = extra
    try:
        Path(AGENT_INDEX_DIR).mkdir(parents=True, exist_ok=True)
        _atomic_write(AGENT_MANIFEST, orjson.dumps(manifest, option=orjson.OPT_INDENT_2))
    except Exception:
        pass


def _config_hash():
    try:
        import config as c
        h = hashlib.blake2b(digest_size=16)
        for k in sorted(dir(c)):
            if k.isupper() and not k.startswith("_"):
                try:
                    h.update(f"{k}={getattr(c, k)!r}".encode("utf-8", "ignore"))
                except Exception:
                    pass
        return h.hexdigest()
    except Exception:
        return ""


# ============================================================================
#  FILE IO
# ============================================================================

def _load_done_set():
    done = set()
    if not os.path.exists(DONE_FILE):
        return done
    try:
        with open(DONE_FILE, "rb") as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            for line in iter(mm.readline, b""):
                line = line.strip()
                if line:
                    done.add(line.decode("ascii", "ignore"))
            mm.close()
    except Exception:
        pass
    return done


def _append_error(url, reason):
    try:
        with open(ERRORS_FILE, "a", encoding="utf-8") as f:
            f.write(f"{url}\t{reason}\t{time.time()}\n")
    except Exception:
        pass


def _append_blocked(url, depth, priority, retries, retry_ts):
    try:
        with open(BLOCKED_FILE, "a", encoding="utf-8") as f:
            f.write(f"{url}\t{depth}\t{priority}\t{retries}\t{retry_ts}\n")
    except Exception:
        pass


def _rewrite_blocked(entries):
    tmp = BLOCKED_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            for url, depth, priority, retries, retry_ts in entries:
                f.write(f"{url}\t{depth}\t{priority}\t{retries}\t{retry_ts}\n")
        os.replace(tmp, BLOCKED_FILE)
    except Exception:
        pass


def _read_blocked():
    out = []
    if not os.path.exists(BLOCKED_FILE):
        return out
    try:
        with open(BLOCKED_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) < 5:
                    continue
                try:
                    out.append((
                        parts[0], int(parts[1]), int(parts[2]),
                        int(parts[3]), float(parts[4]),
                    ))
                except Exception:
                    continue
    except Exception:
        pass
    return out


def _load_queue_from_disk(frontier, done, dedup):
    if not os.path.exists(QUEUE_FILE):
        return 0
    loaded = 0
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if len(frontier) >= frontier.cap:
                    break
                line = line.rstrip("\n")
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) < 2:
                    continue
                url = parts[0]
                try:
                    depth = int(parts[1])
                except Exception:
                    depth = 0
                priority = _PRIORITY_SAME
                if len(parts) >= 3:
                    try:
                        priority = int(parts[2])
                    except Exception:
                        priority = _PRIORITY_SAME
                if dedup.url_hash(url) in done:
                    continue
                if dedup.seen_url(url):
                    continue
                if frontier.push(url, depth, priority):
                    loaded += 1
    except Exception:
        pass
    return loaded


def _persist_queue(frontier):
    tmp = QUEUE_FILE + ".tmp"
    try:
        entries = sorted(frontier.snapshot())[: frontier.cap]
        with open(tmp, "w", encoding="utf-8") as f:
            for priority, depth, _, url in entries:
                f.write(f"{url}\t{depth}\t{priority}\n")
        os.replace(tmp, QUEUE_FILE)
    except Exception:
        pass


def _replay_journal(dedup, frontier):
    if not os.path.exists(RESUME_JOURNAL):
        return 0
    replayed = 0
    try:
        with open(RESUME_JOURNAL, "rb") as f:
            for line in f:
                if len(frontier) >= frontier.cap:
                    break
                try:
                    obj = orjson.loads(line)
                except Exception:
                    continue
                url = obj.get("url")
                depth = int(obj.get("depth", 0))
                if not url or dedup.seen_url(url):
                    continue
                if frontier.push(url, depth + 1, _PRIORITY_SAME):
                    replayed += 1
    except Exception:
        pass
    return replayed


def _append_resume_journal(url, depth):
    try:
        with open(RESUME_JOURNAL, "ab") as f:
            f.write(orjson.dumps({"url": url, "depth": depth, "ts": time.time()}))
            f.write(b"\n")
    except Exception:
        pass


# ============================================================================
#  PROCESS UTILITIES
# ============================================================================

def _pid_rss_mb(pid):
    try:
        return psutil.Process(pid).memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0


def _kill_pid(pid):
    try:
        if IS_WIN:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True, timeout=10,
            )
        else:
            os.kill(pid, signal.SIGKILL)
    except Exception:
        pass


def _clear_os_cache():
    try:
        if IS_WIN:
            subprocess.run(["cmd", "/c", "ipconfig", "/flushdns"],
                            capture_output=True, timeout=10)
        elif IS_LINUX:
            subprocess.run(
                ["sh", "-c", "sync; echo 1 > /proc/sys/vm/drop_caches 2>/dev/null || true"],
                capture_output=True, timeout=10,
            )
    except Exception:
        pass


def _clear_temp():
    try:
        FolderManager.sweep_tmp(max_age_hours=4.0)
    except Exception:
        pass


# ============================================================================
#  LINK FILTERING
# ============================================================================

def _same_tld_plus_one(base_url, candidate):
    try:
        a_host = urlparse(base_url).netloc
        b_host = urlparse(candidate).netloc
        if not a_host or not b_host:
            return False
        a = get_tld(a_host, fix_protocol=True, fail_silently=True)
        b = get_tld(b_host, fix_protocol=True, fail_silently=True)
        return bool(a) and a == b
    except Exception:
        return False


def _domain_denied(url):
    try:
        host = urlparse(url).netloc
    except Exception:
        return True
    for d in CROSS_DOMAIN_DENYLIST:
        if d in host:
            return True
    return False


def _should_follow(base_url, link):
    try:
        p = urlparse(link)
    except Exception:
        return False
    if p.scheme not in ("http", "https") or not p.netloc:
        return False
    if is_navigation_page(link):
        return False
    if _domain_denied(link):
        return False
    base_host = urlparse(base_url).netloc
    if p.netloc == base_host:
        return True
    if CROSS_DOMAIN_ALLOWLIST and any(a in link for a in CROSS_DOMAIN_ALLOWLIST):
        return True
    if not FOLLOW_EXTERNAL:
        return False
    return _same_tld_plus_one(base_url, link)


def _clean_link(base_url, link):
    try:
        absolute = urljoin(base_url, link)
    except Exception:
        return None
    if not absolute.startswith(("http://", "https://")):
        return None
    try:
        c = clean_url(absolute)
        if not c:
            return None
        n = normalize_url(c)
        return n or c
    except Exception:
        return None


def _filter_links(base_url, links):
    out = []
    seen = set()
    for link in links:
        if len(out) >= MAX_LINKS_PER_PAGE:
            break
        if not link:
            continue
        cleaned = _clean_link(base_url, link)
        if not cleaned:
            continue
        if not _should_follow(base_url, cleaned):
            continue
        if _detect_trap(cleaned)[0]:
            continue
        h = hashlib.blake2b(cleaned.encode("utf-8", "ignore"), digest_size=12).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        out.append(cleaned)
    return out


# ============================================================================
#  ROBOTS CACHE
# ============================================================================

_ROBOTS_CACHE = {}
_ROBOTS_LOCK = threading.Lock()


def _robots_allowed(url, session):
    if not RESPECT_ROBOTS:
        return True
    try:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return True
    now = time.time()
    with _ROBOTS_LOCK:
        entry = _ROBOTS_CACHE.get(base)
        if entry and now - entry[0] < ROBOTS_CACHE_TTL:
            return entry[1]
    try:
        r = session.get(f"{base}/robots.txt", timeout=10)
        if r.status_code != 200:
            allowed = True
        else:
            allowed = _parse_robots(r.text, parsed.path or "/")
    except Exception:
        allowed = True
    with _ROBOTS_LOCK:
        _ROBOTS_CACHE[base] = (now, allowed)
    return allowed


def _parse_robots(text, path):
    ua_match = False
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("user-agent:"):
            ua_match = line.split(":", 1)[1].strip() == "*"
        elif ua_match and line.lower().startswith("disallow:"):
            rule = line.split(":", 1)[1].strip()
            if rule and path.startswith(rule):
                return False
    return True


# ============================================================================
#  API ROUTER INTEGRATION
# ============================================================================

def _is_full_record(obj):
    if not isinstance(obj, dict):
        return False
    return ("content" in obj and "url" in obj
            and ("schema_version" in obj or "kind" in obj))


def _try_api_route(url, dedup, state):
    """Try api_router first. Returns full record or None.
    Updates dedup route memory and state counters."""
    if not API_ROUTER_ENABLED:
        return None
    try:
        from api_router import route_sync
    except ImportError:
        return None
    try:
        result = route_sync(url)
    except Exception as e:
        _log("api_route failed for %s: %r", url[:100], e, level=logging.DEBUG)
        return None
    if result is None:
        return None
    if _is_full_record(result):
        state["api_routed"] = state.get("api_routed", 0) + 1
        return result
    return None


# ============================================================================
#  WORKER
# ============================================================================

def _call_scrape(sc_mod, url, session, mos_state):
    result = sc_mod.scrape_url(url, session, mos_state)
    if isinstance(result, tuple):
        if len(result) == 4:
            return result
        if len(result) == 3:
            rec, links, blocked = result
            return rec, links, blocked, False
    return {"url": url, "error": "invalid_result"}, [], False, False


def _worker(worker_id, task_q, result_q, link_q, blocked_q, stop_evt,
            pending, completed_count, dedup_path, opts):
    from spoof import SpoofedSession
    import scraper as sc_mod

    _setup_logging()
    fast = opts.get("fast", False)
    antiblock = opts.get("antiblock", False)

    try:
        dedup = DedupStore(dedup_path)
    except Exception as e:
        _log("worker %d failed to open dedup: %r", worker_id, e,
             level=logging.ERROR)
        return

    dlq = DeadLetterQueue()
    sessions = {}
    tracker = DomainTracker()
    health = HealthRegistry()
    change_detector = ChangeDetector()
    yield_tracker = YieldTracker()
    bootstrap = DomainBootstrap()
    state_shared = {}

    try:
        mos_state = sc_mod.MOSState()
    except Exception:
        mos_state = None

    done_count = 0
    session_start = time.monotonic()

    try:
        while not stop_evt.is_set():
            if done_count >= WORKER_RECYCLE_AFTER_URLS:
                break
            if time.monotonic() - session_start >= WORKER_RECYCLE_AFTER_SECONDS:
                break
            try:
                item = task_q.get(timeout=1.5)
            except Exception:
                continue
            if item is _SENTINEL:
                break

            url, depth, priority, retries = item
            domain = urlparse(url).netloc
            h = health.get(domain)

            if not h.is_usable():
                try:
                    task_q.put(item, timeout=5)
                except Exception:
                    pass
                time.sleep(0.5)
                continue

            if not tracker.try_acquire(domain, health_factor=h.rate_factor()):
                try:
                    task_q.put(item, timeout=5)
                except Exception:
                    pass
                time.sleep(0.1)
                continue

            session = sessions.get(domain)
            if session is None:
                try:
                    session = SpoofedSession(domain, fast=fast)
                    sessions[domain] = session
                except Exception as e:
                    _log("session init failed for %s: %r", domain, e,
                         level=logging.WARNING)
                    with pending.get_lock():
                        pending.value -= 1
                    continue

            blocked = False
            record = None
            raw_links = []
            escalate = False
            used_api = False

            try:
                if not _robots_allowed(url, session):
                    result_q.put({"url": url, "error": "robots_denied"})
                    with pending.get_lock():
                        pending.value -= 1
                    yield_tracker.record(url, False, blocked=True)
                    continue

                # Try api_router first for full records
                api_record = _try_api_route(url, dedup, state_shared)
                if api_record is not None:
                    record = api_record
                    used_api = True
                else:
                    record, raw_links, blocked, escalate = _call_scrape(
                        sc_mod, url, session, mos_state
                    )

            except Exception as e:
                msg = repr(e).lower()
                if antiblock and ("timeout" in msg or "connection" in msg
                                    or "reset" in msg):
                    blocked = True
                else:
                    record = {"url": url, "error": repr(e)}
                    raw_links = []

            if blocked:
                h.record_failure(weight=1.0)
                if isinstance(record, dict):
                    status = record.get("status", 403)
                    if status == 429:
                        tracker.record_429(domain)
                if BLOCKED_FINGERPRINT_ROTATE:
                    try:
                        session.rotate_fingerprint()
                    except Exception:
                        pass
                if BLOCKED_PROXY_ROTATE:
                    try:
                        session.rotate_proxy()
                    except Exception:
                        pass
                blocked_q.put((url, depth, priority, retries + 1))
                with pending.get_lock():
                    pending.value -= 1
                yield_tracker.record(url, False, blocked=True)
                continue

            h.record_success()
            tracker.record_success(domain)

            if escalate and isinstance(record, dict) and not blocked:
                record["quarantine_category"] = "empty_extraction"

            useful = False
            if isinstance(record, dict):
                wc = record.get("word_count", 0) or 0
                if wc >= 30 and not record.get("error"):
                    useful = True
            yield_tracker.record(url, useful, blocked=False)

            # Bootstrap new domain if not yet done
            if record and not record.get("error") and depth == 0:
                try:
                    root_url = f"{urlparse(url).scheme}://{domain}"
                    cached = bootstrap._load(domain)
                    if cached is None:
                        seeds = bootstrap.discover_sync(
                            domain, root_url, session, max_seeds=100
                        )
                        if seeds:
                            state_shared["bootstrap_discovered"] = (
                                state_shared.get("bootstrap_discovered", 0)
                                + len(seeds)
                            )
                            link_q.put((url, depth, seeds))
                except Exception as e:
                    _log("bootstrap failed for %s: %r", domain, e,
                         level=logging.DEBUG)

            links = _filter_links(url, raw_links or [])
            result_q.put(record)
            link_q.put((url, depth, links))
            with completed_count.get_lock():
                completed_count.value += 1
            with pending.get_lock():
                pending.value -= 1
            done_count += 1

            if done_count % GC_INTERVAL == 0:
                gc.collect()

    finally:
        for s in sessions.values():
            try:
                s.close()
            except Exception:
                pass
        if mos_state is not None:
            try:
                mos_state.close()
            except Exception:
                pass
        tracker.persist_rates()
        dlq.close()
        dedup.close()


# ============================================================================
#  WRITER
# ============================================================================

def _writer(result_q, stop_evt, out_path, manifest_q):
    _setup_logging()
    use_shards = AGENT_SHARD_ENABLED
    writer = ShardedWriter(AGENT_SHARDS_DIR) if use_shards else None
    flat = None
    tmp_path = None
    if not use_shards:
        tmp_path = out_path + ".tmp"
        Path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
        flat = open(tmp_path, "wb")

    quarantine = QuarantineWriter()
    written = 0

    def _route(rec):
        nonlocal written
        if not isinstance(rec, dict):
            return
        if "error" in rec:
            return
        words = rec.get("word_count", 0) or 0
        quality = rec.get("quality", {}) or {}
        if AGENT_QUARANTINE_ENABLED:
            if AGENT_QUARANTINE_EMPTY_CONTENT and words == 0:
                quarantine.write("empty", rec)
                return
            if (AGENT_QUARANTINE_LOW_QUALITY
                    and quality.get("flesch_reading_ease", 0.0) < 0
                    and words < 30):
                quarantine.write("low_quality", rec)
                return
            qcat = rec.get("quarantine_category")
            if qcat:
                quarantine.write(qcat, rec)
                return
        if use_shards:
            if writer.write(rec):
                written += 1
        else:
            try:
                flat.write(orjson.dumps(rec, option=orjson.OPT_INDENT_2))
                flat.write(b"\n")
                written += 1
            except Exception:
                pass

    while not stop_evt.is_set() or not result_q.empty():
        try:
            rec = result_q.get(timeout=1)
        except Exception:
            if stop_evt.is_set() and result_q.empty():
                break
            continue
        if rec is _SENTINEL:
            break
        _route(rec)
        if written % 50 == 0:
            if use_shards:
                writer.flush()
            else:
                try:
                    flat.flush()
                except Exception:
                    pass

    if use_shards:
        writer.close()
        try:
            manifest_q.put({
                "shards": writer.shards(),
                "categories": quarantine.counts_snapshot(),
                "written": written,
            })
        except Exception:
            pass
    else:
        try:
            flat.flush()
            flat.close()
            os.replace(tmp_path, out_path)
        except Exception:
            pass
    quarantine.close()


# ============================================================================
#  MONITOR
# ============================================================================

def _monitor(stop_evt, worker_pids, telemetry_q):
    _setup_logging()
    last_cache = time.monotonic()
    last_telemetry = time.monotonic()
    while not stop_evt.is_set():
        time.sleep(5)
        for pid in list(worker_pids):
            if not pid:
                continue
            try:
                if not psutil.pid_exists(pid):
                    continue
            except Exception:
                continue
            mb = _pid_rss_mb(pid)
            if mb > MAX_RSS_MB:
                _log("killing worker pid=%s rss=%.1fMB", pid, mb,
                     level=logging.WARNING)
                _kill_pid(pid)
        if time.monotonic() - last_cache > CACHE_CLEAR_INTERVAL:
            _clear_os_cache()
            _clear_temp()
            gc.collect()
            last_cache = time.monotonic()
        if TELEMETRY_ENABLED and time.monotonic() - last_telemetry >= TELEMETRY_INTERVAL:
            try:
                telemetry_q.put("tick")
            except Exception:
                pass
            last_telemetry = time.monotonic()


# ============================================================================
#  COMPACTOR
# ============================================================================

def _compactor(stop_evt, dedup_path):
    try:
        dedup = DedupStore(dedup_path)
    except Exception:
        return
    while not stop_evt.is_set():
        time.sleep(15)
        try:
            dedup.commit()
            dedup.bloom.save(BLOOM_FILE)
        except Exception:
            pass
    dedup.close()


# ============================================================================
#  TELEMETRY LOOP
# ============================================================================

def _telemetry_loop(stop_evt, telemetry_q, shared):
    _setup_logging()
    while not stop_evt.is_set():
        try:
            telemetry_q.get(timeout=1)
        except Exception:
            continue
        if stop_evt.is_set():
            break
        snap = shared.snapshot()
        _log(
            "telemetry: rate=%.2f/s records=%d blocked=%d dup=%d errors=%d",
            snap["rate_per_sec"], snap["records_total"],
            snap["blocked_total"], snap["dup_total"], snap["error_total"],
        )


# ============================================================================
#  BLOCKED QUEUE PROCESSOR
# ============================================================================

def _process_blocked_file(task_q, pending, state):
    now = time.time()
    entries = _read_blocked()
    if not entries:
        return 0
    keep = []
    requeued = 0
    for url, depth, priority, retries, retry_ts in entries:
        if retry_ts > now:
            keep.append((url, depth, priority, retries, retry_ts))
            continue
        if retries >= MAX_BLOCKED_RETRIES:
            _append_error(url, f"blocked x{retries}")
            state.failed += 1
            state.blocked_gave_up += 1
            continue
        try:
            task_q.put((url, depth, priority, retries), timeout=5)
            with pending.get_lock():
                pending.value += 1
            requeued += 1
            state.blocked += 1
            state.blocked_retried += 1
        except Exception:
            keep.append((
                url, depth, priority, retries,
                now + random.uniform(BLOCKED_RETRY_MIN, BLOCKED_RETRY_MAX),
            ))
    _rewrite_blocked(keep)
    return requeued


# ============================================================================
#  SEEDS HASH
# ============================================================================

def _seeds_hash(seeds):
    return hashlib.blake2b("|".join(sorted(seeds)).encode(), digest_size=12).hexdigest()


# ============================================================================
#  RUN
# ============================================================================

def run(seeds, options):
    _setup_logging()
    FolderManager.bootstrap()

    try:
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass

    try:
        mp.set_start_method("spawn", force=True)
    except Exception:
        pass

    fast = options.get("fast", False)
    infinite = options.get("inf", False)
    antiblock = options.get("antiblock", False)
    queue_cap = options.get("queue_cap", MAX_QUEUE_SIZE)
    max_depth = options.get("max_depth", MAX_DEPTH)
    out_path = options.get("out", OUTPUT_PATH)
    workers_n = options.get(
        "workers", MAX_WORKERS * (MAX_WORKERS_FAST_MULT if fast else 1)
    )

    _log("crawler starting: seeds=%d workers=%d depth=%d queue_cap=%d",
         len(seeds), workers_n, max_depth, queue_cap)

    worker_opts = {"fast": fast, "antiblock": antiblock}

    state = _read_state()
    if (STRICT_CONFIG_ENFORCEMENT
            and state.config_version
            and state.config_version != CONFIG_VERSION):
        _log("config version changed %s -> %s; refusing resume",
             state.config_version, CONFIG_VERSION, level=logging.WARNING)
        if FORCE_RESUME_OVERRIDE_FLAG not in sys.argv:
            _log("pass %s to force resume", FORCE_RESUME_OVERRIDE_FLAG,
                 level=logging.WARNING)
            return
    state.seeds_hash = _seeds_hash(seeds)
    state.config_version = CONFIG_VERSION
    state.config_generation = CONFIG_GENERATION
    if state.started_at == 0:
        state.started_at = time.time()

    try:
        dedup = DedupStore(DEDUP_DB)
    except Exception as e:
        _log("failed to open dedup store: %r", e, level=logging.ERROR)
        return

    done = _load_done_set()
    frontier = MercatorFrontier(cap=queue_cap)

    loaded = _load_queue_from_disk(frontier, done, dedup)
    replayed = _replay_journal(dedup, frontier)
    _log("resume: loaded=%d replayed=%d", loaded, replayed)

    task_q = mp.Queue(maxsize=TASK_QUEUE_MAX)
    result_q = mp.Queue(maxsize=RESULT_QUEUE_MAX)
    link_q = mp.Queue(maxsize=LINK_QUEUE_MAX)
    blocked_q = mp.Queue(maxsize=LINK_QUEUE_MAX)
    manifest_q = mp.Queue(maxsize=4)
    telemetry_q = mp.Queue(maxsize=16)
    stop_evt = mp.Event()
    pending = mp.Value("i", 0)
    completed_count = mp.Value("i", 0)

    change_detector = ChangeDetector()

    def enqueue_new(url, depth, priority, score=0.0):
        try:
            url = urldefrag(url)[0]
        except Exception:
            return False
        if depth > max_depth:
            return False
        if dedup.seen_url(url):
            state.dup += 1
            return False
        if dedup.url_hash(url) in done:
            state.dup += 1
            return False
        trap, reason = _detect_trap(url)
        if trap:
            state.traps_detected += 1
            _log("trap: %s (%s)", url[:120], reason, level=logging.DEBUG)
            return False
        try:
            task_q.put((url, depth, priority, 0), timeout=10)
        except Exception:
            state.queue_dropped += 1
            return False
        dedup.mark_url(url)
        _append_resume_journal(url, depth)
        with pending.get_lock():
            pending.value += 1
        state.enqueued += 1
        if depth > state.depth_reached:
            state.depth_reached = depth
        return True

    bootstrap_n = 0
    while len(frontier) > 0 and bootstrap_n < 10000:
        item = frontier.pop()
        if not item:
            break
        url, depth, priority, score = item
        if enqueue_new(url, depth, priority, score):
            bootstrap_n += 1

    for s in seeds:
        canon = dedup.canonical(s)
        if not canon:
            continue
        enqueue_new(canon, 0, _PRIORITY_SAME, score=0.5)

    _log("bootstrap: task_queue=%d frontier=%d", bootstrap_n, len(frontier))

    workers = []
    for i in range(workers_n):
        p = mp.Process(
            target=_worker,
            args=(i, task_q, result_q, link_q, blocked_q, stop_evt,
                  pending, completed_count, DEDUP_DB, worker_opts),
            daemon=False,
        )
        p.start()
        workers.append(p)

    writer_p = mp.Process(
        target=_writer, args=(result_q, stop_evt, out_path, manifest_q),
        daemon=False,
    )
    writer_p.start()

    monitor_p = mp.Process(
        target=_monitor,
        args=(stop_evt, [w.pid for w in workers], telemetry_q),
        daemon=False,
    )
    monitor_p.start()

    compactor_p = mp.Process(
        target=_compactor, args=(stop_evt, DEDUP_DB), daemon=False,
    )
    compactor_p.start()

    telemetry_p = None
    if TELEMETRY_ENABLED:
        try:
            from scraper import Telemetry
            shared_tele = Telemetry()
            telemetry_p = mp.Process(
                target=_telemetry_loop, args=(stop_evt, telemetry_q, shared_tele),
                daemon=False,
            )
            telemetry_p.start()
        except Exception:
            telemetry_p = None

    idle_since = None
    last_blocked_check = 0.0
    completed_ticks = 0
    last_manifest = time.monotonic()
    cfg_hash = _config_hash()

    try:
        while not stop_evt.is_set():
            drained = False

            while True:
                try:
                    u, d, p, r = blocked_q.get_nowait()
                except Exception:
                    break
                drained = True
                retry_ts = time.time() + random.uniform(
                    BLOCKED_RETRY_MIN, BLOCKED_RETRY_MAX
                )
                _append_blocked(u, d, p, r, retry_ts)

            if time.monotonic() - last_blocked_check >= BLOCKED_CHECK_INTERVAL:
                _process_blocked_file(task_q, pending, state)
                last_blocked_check = time.monotonic()

            while True:
                try:
                    url, depth, links = link_q.get_nowait()
                except Exception:
                    break
                drained = True
                if depth >= max_depth:
                    continue
                base_host = urlparse(url).netloc
                base_tld = None
                try:
                    base_tld = get_tld(base_host, fix_protocol=True,
                                        fail_silently=True)
                except Exception:
                    pass
                for l in links:
                    if len(frontier) >= frontier.cap:
                        state.queue_dropped += 1
                        continue
                    l_host = urlparse(l).netloc
                    if l_host == base_host:
                        priority = _PRIORITY_SAME
                    else:
                        priority = _PRIORITY_CROSS
                        if base_tld:
                            try:
                                l_tld = get_tld(l_host, fix_protocol=True,
                                                fail_silently=True)
                                if l_tld != base_tld:
                                    if depth + 1 > CROSS_DOMAIN_MAX_HOPS:
                                        continue
                            except Exception:
                                pass
                    score = change_detector.priority_boost(l)
                    frontier.push(l, depth + 1, priority, score)

            drained_frontier = 0
            while len(frontier) > 0 and drained_frontier < FRONTIER_DRAIN_PER_TICK:
                item = frontier.pop()
                if not item:
                    break
                furl, fdepth, fpriority, fscore = item
                if enqueue_new(furl, fdepth, fpriority, fscore):
                    drained_frontier += 1
                    drained = True

            with pending.get_lock():
                p = pending.value
            with completed_count.get_lock():
                state.completed = completed_count.value

            try:
                q_empty = task_q.empty()
            except Exception:
                q_empty = True
            try:
                l_empty = link_q.empty()
            except Exception:
                l_empty = True
            try:
                r_empty = result_q.empty()
            except Exception:
                r_empty = True
            frontier_empty = len(frontier) == 0

            if p == 0 and q_empty and l_empty and r_empty and frontier_empty:
                if infinite:
                    idle_since = None
                    time.sleep(1.0)
                    continue
                if idle_since is None:
                    idle_since = time.monotonic()
                elif time.monotonic() - idle_since > IDLE_TIMEOUT:
                    break
            else:
                idle_since = None

            completed_ticks += 1
            if completed_ticks % CHECKPOINT_EVERY == 0:
                try:
                    dedup.commit()
                    _save_state(state)
                    _persist_queue(frontier)
                except Exception:
                    pass

            if completed_ticks % FRONTIER_PRIORITY_DECAY_INTERVAL == 0:
                try:
                    frontier.decay(threshold_seconds=600.0)
                except Exception:
                    pass

            if time.monotonic() - last_manifest >= AGENT_MANIFEST_WRITE_INTERVAL:
                try:
                    _write_manifest(state, {}, None, cfg_hash)
                except Exception:
                    pass
                last_manifest = time.monotonic()

            time.sleep(0.1)
    except KeyboardInterrupt:
        _log("interrupted, shutting down")
    finally:
        with completed_count.get_lock():
            state.completed = completed_count.value
        for _ in range(workers_n + 2):
            try:
                task_q.put_nowait(_SENTINEL)
            except Exception:
                pass
        stop_evt.set()
        deadline = time.monotonic() + 20
        for w in workers:
            w.join(timeout=max(0.1, deadline - time.monotonic()))
        for w in workers:
            if w.is_alive():
                _kill_pid(w.pid)
        writer_p.join(timeout=20)
        if writer_p.is_alive():
            _kill_pid(writer_p.pid)
        monitor_p.join(timeout=5)
        if monitor_p.is_alive():
            _kill_pid(monitor_p.pid)
        compactor_p.join(timeout=10)
        if compactor_p.is_alive():
            _kill_pid(compactor_p.pid)
        if telemetry_p is not None:
            telemetry_p.join(timeout=5)
            if telemetry_p.is_alive():
                _kill_pid(telemetry_p.pid)

        manifest_data = {}
        try:
            while True:
                d = manifest_q.get_nowait()
                manifest_data.update(d)
        except Exception:
            pass

        try:
            dedup.commit()
            dedup.bloom.save(BLOOM_FILE)
            dedup.close()
        except Exception:
            pass
        try:
            state.records_written = manifest_data.get("written", 0)
            _save_state(state)
            _persist_queue(frontier)
            _write_manifest(
                state,
                manifest_data.get("shards", {}),
                None,
                cfg_hash,
                manifest_data.get("categories"),
            )
        except Exception:
            pass
        try:
            os.remove(PID_FILE)
        except Exception:
            pass
        _log("crawler stopped: completed=%d enqueued=%d dup=%d written=%d",
             state.completed, state.enqueued, state.dup,
             state.records_written)
        _clear_temp()
        gc.collect()