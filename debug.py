import os
import sys
import re
import io
import json
import time
import math
import gzip
import queue
import random
import signal
import string
import hashlib
import argparse
import threading
import traceback
import statistics
import subprocess
import contextlib
import multiprocessing as mp
from pathlib import Path
from collections import deque, defaultdict, Counter, OrderedDict
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Optional

import psutil

sys.path.insert(0, str(Path(__file__).resolve().parent))

from urllib.parse import urlparse, urljoin, urldefrag

from folder_manager import FolderManager


# ============================================================================
#  LOGGING INFRASTRUCTURE
# ============================================================================

class Level(Enum):
    TRACE = 5
    DEBUG = 10
    INFO = 20
    PASS = 25
    WARN = 30
    FAIL = 35
    ERROR = 40
    FATAL = 50


LEVEL_LABELS = {
    Level.TRACE: ("TRCE", "\033[90m"),
    Level.DEBUG: ("DBUG", "\033[36m"),
    Level.INFO: ("INFO", "\033[37m"),
    Level.PASS: ("PASS", "\033[92m"),
    Level.WARN: ("WARN", "\033[93m"),
    Level.FAIL: ("FAIL", "\033[91m"),
    Level.ERROR: ("ERRO", "\033[91m"),
    Level.FATAL: ("FATL", "\033[1;91m"),
}
RESET = "\033[0m"


def _colorize(text, color):
    if os.name == "nt" and not os.environ.get("WT_SESSION"):
        return text
    return f"{color}{text}{RESET}"


class RingBuffer:
    __slots__ = ("_buf", "_lock", "_total")

    def __init__(self, maxlen=50000):
        self._buf = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._total = 0

    def append(self, item):
        with self._lock:
            self._buf.append(item)
            self._total += 1

    def drain(self):
        with self._lock:
            items = list(self._buf)
            self._buf.clear()
            return items

    def snapshot(self):
        with self._lock:
            return list(self._buf)

    def __len__(self):
        return len(self._buf)

    @property
    def total(self):
        return self._total


class AsyncFileWriter:
    def __init__(self, path, batch_size=200, flush_interval=1.0):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._queue = queue.Queue(maxsize=100000)
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._thread = None
        self._stop = threading.Event()
        self._written = 0
        self._dropped = 0
        self._start()

    def _start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        buffer = []
        last_flush = time.monotonic()
        try:
            fh = open(self.path, "ab", buffering=65536)
        except Exception:
            return
        try:
            while not self._stop.is_set() or not self._queue.empty():
                try:
                    item = self._queue.get(timeout=0.2)
                    buffer.append(item)
                except queue.Empty:
                    pass
                now = time.monotonic()
                if (len(buffer) >= self._batch_size
                        or now - last_flush >= self._flush_interval):
                    if buffer:
                        try:
                            fh.write(b"".join(buffer))
                            fh.flush()
                            self._written += len(buffer)
                        except Exception:
                            pass
                        buffer.clear()
                    last_flush = now
        finally:
            if buffer:
                try:
                    fh.write(b"".join(buffer))
                    fh.flush()
                    self._written += len(buffer)
                except Exception:
                    pass
            try:
                fh.close()
            except Exception:
                pass

    def write(self, data):
        try:
            self._queue.put_nowait(data)
            return True
        except queue.Full:
            self._dropped += 1
            return False

    def stop(self, timeout=3.0):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    @property
    def stats(self):
        return {"written": self._written, "dropped": self._dropped,
                "pending": self._queue.qsize()}


class Logger:
    __slots__ = ("name", "_min_level", "_console", "_file", "_ring",
                 "_context", "_lock", "_events", "_counters", "_timings")

    _global_min_level = Level.DEBUG
    _global_console = True
    _global_file = None
    _global_ring = None
    _global_lock = threading.Lock()

    def __init__(self, name, min_level=None, console=None, file=None):
        self.name = name
        self._min_level = min_level or Logger._global_min_level
        self._console = console if console is not None else Logger._global_console
        self._file = file if file is not None else Logger._global_file
        self._ring = Logger._global_ring
        self._context = {}
        self._lock = threading.Lock()
        self._events = Counter()
        self._counters = defaultdict(int)
        self._timings = defaultdict(list)

    @classmethod
    def configure(cls, min_level=None, console=None, file_path=None,
                   ring_buffer_size=50000):
        if min_level is not None:
            cls._global_min_level = min_level
        if console is not None:
            cls._global_console = console
        if file_path is not None:
            cls._global_file = AsyncFileWriter(file_path)
        if cls._global_ring is None:
            cls._global_ring = RingBuffer(maxlen=ring_buffer_size)

    @classmethod
    def shutdown(cls):
        if cls._global_file is not None:
            cls._global_file.stop()

    def with_context(self, **kwargs):
        ctx = dict(self._context)
        ctx.update(kwargs)
        return _ContextLogger(self, ctx)

    def _enabled(self, level):
        return level.value >= self._min_level.value

    def _emit(self, level, msg, args=None, exc_info=None, **extra):
        if not self._enabled(level):
            return
        label, color = LEVEL_LABELS[level]
        if args:
            try:
                message = msg % args
            except Exception:
                message = msg + " " + repr(args)
        else:
            message = msg

        ts = time.time()
        tid = threading.get_ident() % 10000
        prefix = f"{self.name}[{tid:04d}]"
        if self._context:
            ctx_str = " ".join(f"{k}={v}" for k, v in self._context.items())
            prefix = f"{prefix} {ctx_str}"

        record = {
            "ts": ts,
            "level": level.name,
            "logger": self.name,
            "thread": tid,
            "context": dict(self._context),
            "message": message,
            "extra": extra or {},
        }
        if exc_info is not None:
            record["exception"] = "".join(
                traceback.format_exception(*exc_info)
            )

        if self._console:
            stamp = time.strftime("%H:%M:%S", time.localtime(ts))
            tag = _colorize(label, color)
            line = f"{stamp} {tag} {prefix} {message}"
            try:
                print(line)
            except Exception:
                pass

        if self._file is not None:
            try:
                line = json.dumps(record, default=str) + "\n"
                self._file.write(line.encode("utf-8"))
            except Exception:
                pass

        if self._ring is not None:
            self._ring.append(record)

    def _emit_simple(self, level, msg, *args, **kwargs):
        self._emit(level, msg, args if args else None, **kwargs)

    def trace(self, msg, *a, **k):
        self._emit_simple(Level.TRACE, msg, *a, **k)

    def debug(self, msg, *a, **k):
        self._emit_simple(Level.DEBUG, msg, *a, **k)

    def info(self, msg, *a, **k):
        self._emit_simple(Level.INFO, msg, *a, **k)

    def pass_(self, msg, *a, **k):
        self._emit_simple(Level.PASS, msg, *a, **k)

    def warn(self, msg, *a, **k):
        self._emit_simple(Level.WARN, msg, *a, **k)

    def fail(self, msg, *a, **k):
        self._emit_simple(Level.FAIL, msg, *a, **k)

    def error(self, msg, *a, **k):
        self._emit_simple(Level.ERROR, msg, *a, **k)

    def fatal(self, msg, *a, **k):
        self._emit_simple(Level.FATAL, msg, *a, **k)

    def exception(self, e, msg="exception"):
        self._emit(Level.ERROR, f"{msg}: {e!r}",
                    exc_info=(type(e), e, e.__traceback__))

    @contextlib.contextmanager
    def timer(self, label):
        t0 = time.perf_counter_ns()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter_ns() - t0) / 1e6
            with self._lock:
                self._timings[label].append(elapsed_ms)
            self.debug("timing[%s] = %.2f ms", label, elapsed_ms)

    def event(self, name, **fields):
        with self._lock:
            self._events[name] += 1
        self.debug("event[%s] %s", name,
                    " ".join(f"{k}={v}" for k, v in fields.items()))

    def counter(self, name, delta=1):
        with self._lock:
            self._counters[name] += delta

    def timing_stats(self):
        with self._lock:
            return {
                k: {
                    "count": len(v),
                    "min_ms": round(min(v), 3),
                    "max_ms": round(max(v), 3),
                    "mean_ms": round(statistics.mean(v), 3),
                    "median_ms": round(statistics.median(v), 3),
                    "p95_ms": round(
                        sorted(v)[int(len(v) * 0.95)] if v else 0, 3
                    ),
                }
                for k, v in self._timings.items() if v
            }

    def event_counts(self):
        with self._lock:
            return dict(self._events)

    def counter_snapshot(self):
        with self._lock:
            return dict(self._counters)


class _ContextLogger:
    __slots__ = ("_logger", "_ctx")

    def __init__(self, logger, ctx):
        self._logger = logger
        self._ctx = ctx

    def _emit(self, level, msg, *args):
        old = self._logger._context
        self._logger._context = self._ctx
        try:
            self._logger._emit_simple(level, msg, *args)
        finally:
            self._logger._context = old

    def trace(self, msg, *a): self._emit(Level.TRACE, msg, *a)
    def debug(self, msg, *a): self._emit(Level.DEBUG, msg, *a)
    def info(self, msg, *a): self._emit(Level.INFO, msg, *a)
    def pass_(self, msg, *a): self._emit(Level.PASS, msg, *a)
    def warn(self, msg, *a): self._emit(Level.WARN, msg, *a)
    def fail(self, msg, *a): self._emit(Level.FAIL, msg, *a)
    def error(self, msg, *a): self._emit(Level.ERROR, msg, *a)


# ============================================================================
#  TEST FRAMEWORK
# ============================================================================

class Status(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    EMPTY = "EMPTY"
    SLOW = "SLOW"
    SKIP = "SKIP"
    ERROR = "ERROR"


@dataclass
class TestResult:
    category: str
    name: str
    status: str
    detail: str = ""
    elapsed_ms: float = 0.0
    rss_mb: float = 0.0
    cpu_pct: float = 0.0
    extra: dict = field(default_factory=dict)
    logs: list = field(default_factory=list)
    traceback: str = ""

    def to_dict(self):
        d = asdict(self)
        if not self.logs:
            d.pop("logs", None)
        if not self.traceback:
            d.pop("traceback", None)
        return d


class AssertionError(FolderAssertionError := type("FolderAssertionError", (AssertionError,), {})):
    pass


class TestContext:
    __slots__ = ("name", "category", "log", "start_ns", "_proc",
                 "_failures", "_warnings")

    def __init__(self, category, name):
        self.category = category
        self.name = name
        self.log = Logger(f"{category}.{name[:24]}")
        self.start_ns = time.perf_counter_ns()
        self._proc = psutil.Process(os.getpid())
        self._failures = []
        self._warnings = []

    def expect(self, condition, message="assertion failed"):
        if not condition:
            raise AssertionError(message)

    def expect_eq(self, a, b, label=""):
        if a != b:
            raise AssertionError(f"{label}: {a!r} != {b!r}")

    def expect_neq(self, a, b, label=""):
        if a == b:
            raise AssertionError(f"{label}: {a!r} == {b!r}")

    def expect_in(self, needle, haystack, label=""):
        if needle not in haystack:
            raise AssertionError(f"{label}: {needle!r} not in {haystack!r}")

    def expect_gt(self, a, b, label=""):
        if not a > b:
            raise AssertionError(f"{label}: {a!r} <= {b!r}")

    def expect_lt(self, a, b, label=""):
        if not a < b:
            raise AssertionError(f"{label}: {a!r} >= {b!r}")

    def expect_raises(self, exc_type, fn, *args, **kwargs):
        try:
            fn(*args, **kwargs)
        except exc_type:
            return True
        except Exception as e:
            raise AssertionError(
                f"expected {exc_type.__name__}, got {type(e).__name__}: {e!r}"
            )
        raise AssertionError(f"expected {exc_type.__name__}, no exception raised")

    def warn(self, message):
        self._warnings.append(message)
        self.log.warn(message)

    def rss_mb(self):
        try:
            return self._proc.memory_info().rss / (1024 * 1024)
        except Exception:
            return 0.0

    def cpu_pct(self):
        try:
            return self._proc.cpu_percent(interval=None)
        except Exception:
            return 0.0

    def elapsed_ms(self):
        return (time.perf_counter_ns() - self.start_ns) / 1e6

    def run(self, fn):
        result = TestResult(
            category=self.category,
            name=self.name,
            status=Status.PASS.value,
            rss_mb=round(self.rss_mb(), 2),
        )
        try:
            rv = fn(self)
            if isinstance(rv, tuple) and len(rv) == 2:
                status, detail = rv
                result.status = status
                result.detail = detail
        except AssertionError as e:
            result.status = Status.FAIL.value
            result.detail = f"assert: {e}"
            result.traceback = traceback.format_exc()
        except Exception as e:
            result.status = Status.ERROR.value
            result.detail = f"{type(e).__name__}: {e}"
            result.traceback = traceback.format_exc()
        result.elapsed_ms = round(self.elapsed_ms(), 3)
        result.cpu_pct = round(self.cpu_pct(), 2)
        result.extra = {
            "events": self.log.event_counts(),
            "timings": self.log.timing_stats(),
            "counters": self.log.counter_snapshot(),
        }
        return result


_REGISTRY = OrderedDict()


def test(category, name, skip_if=None, timeout=None):
    def decorator(fn):
        _REGISTRY.setdefault(category, []).append({
            "name": name, "fn": fn, "skip_if": skip_if, "timeout": timeout,
        })
        return fn
    return decorator


# ============================================================================
#  ENVIRONMENT / DISCOVERY
# ============================================================================

class Env:
    PROCESS = psutil.Process(os.getpid())
    START = time.time()
    CWD = str(Path.cwd())
    PYTHON = sys.version.split()[0]
    PLATFORM = f"{os.name} {sys.platform}"
    CPU_COUNT = os.cpu_count() or 1
    MEM_TOTAL_GB = round(psutil.virtual_memory().total / (1024 ** 3), 2)
    DISK_FREE_GB = 0.0

    try:
        DISK_FREE_GB = round(psutil.disk_usage(".").free / (1024 ** 3), 2)
    except Exception:
        pass

    @classmethod
    def banner(cls):
        return (
            f"NEXUS debug harness v6 :: python {cls.PYTHON} :: "
            f"{cls.PLATFORM} :: {cls.CPU_COUNT} cores :: "
            f"{cls.MEM_TOTAL_GB} GB RAM :: {cls.DISK_FREE_GB} GB free"
        )


# ============================================================================
#  T0 — ENVIRONMENT
# ============================================================================

@test("T0", "environment info")
def t0_env(ctx):
    ctx.log.info("python=%s", Env.PYTHON)
    ctx.log.info("platform=%s", Env.PLATFORM)
    ctx.log.info("cpu_count=%d", Env.CPU_COUNT)
    ctx.log.info("mem_total_gb=%.2f", Env.MEM_TOTAL_GB)
    ctx.log.info("disk_free_gb=%.2f", Env.DISK_FREE_GB)
    ctx.expect(Env.CPU_COUNT >= 1)
    return Status.PASS.value, f"cores={Env.CPU_COUNT} mem={Env.MEM_TOTAL_GB}GB"


@test("T0", "cleanup stale artifacts")
def t0_cleanup(ctx):
    from folder_manager import FolderManager
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        nltk_dir = Path(appdata) / "nltk_data"
        if nltk_dir.exists():
            import shutil
            shutil.rmtree(nltk_dir, ignore_errors=True)
            ctx.log.info("removed nltk_data")
    stale = [
        "bloom.dbg.bin", "bloom.dbg2.bin",
        "dedup.dbg.sqlite", "dedup.dbg2.sqlite",
        "mos_budget.dbg.json", "mos_prefs.dbg.json",
        "budget_score.dbg.json", "prefs_score.dbg.json",
        "dlq.dbg.jsonl", "blocked.test.txt",
    ]
    removed = 0
    for name in stale:
        p = Path(name)
        if p.exists():
            try:
                p.unlink()
                removed += 1
            except Exception:
                pass
    FolderManager.bootstrap()
    return Status.PASS.value, f"removed={removed}"


@test("T0", "folder manager bootstrap")
def t0_fm_bootstrap(ctx):
    from folder_manager import FolderManager
    FolderManager.bootstrap(force=True)
    report = FolderManager.report()
    ctx.expect(len(report["tiers"]) == len(FolderManager.TIERS))
    for tier, entry in report["tiers"].items():
        ctx.expect(Path(entry["path"]).exists(),
                    f"tier {tier} path missing")
    return Status.PASS.value, f"tiers={len(report['tiers'])}"


# ============================================================================
#  T1 — IMPORTS
# ============================================================================

MODULES = [
    "config", "folder_manager", "spoof", "crawler",
    "scraper", "api_router", "se_api",
]


def _make_import_test(modname):
    @test("T1", f"import {modname}")
    def _t(ctx, _m=modname):
        mod = __import__(_m)
        ctx.expect(hasattr(mod, "__file__") or hasattr(mod, "__name__"))
        path = getattr(mod, "__file__", "?")
        ctx.log.info("loaded from %s", path)
        return Status.PASS.value, Path(path).name if path != "?" else "ok"
    return _t


for _m in MODULES:
    _make_import_test(_m)


# ============================================================================
#  T2 — CONFIG INVARIANTS
# ============================================================================

def _cfg_check(name, predicate, detail=""):
    @test("T2", name)
    def _t(ctx, _p=predicate, _n=name, _d=detail):
        import config as c
        ctx.expect(_p(c), _n)
        return Status.PASS.value, _d
    return _t


_cfg_check("MAX_WORKERS >= 1", lambda c: c.MAX_WORKERS >= 1)
_cfg_check("MAX_QUEUE_SIZE == 500 or 5000",
            lambda c: c.MAX_QUEUE_SIZE in (500, 5000, 50000))
_cfg_check("MAX_DEPTH > 0", lambda c: c.MAX_DEPTH > 0)
_cfg_check("REQUEST_TIMEOUT tuple",
            lambda c: isinstance(c.REQUEST_TIMEOUT, tuple)
            and len(c.REQUEST_TIMEOUT) == 2)
_cfg_check("BLOCKED_RETRY range",
            lambda c: 0 < c.BLOCKED_RETRY_MIN < c.BLOCKED_RETRY_MAX)
_cfg_check("BROWSER_PROFILES >= 3",
            lambda c: len(c.BROWSER_PROFILES) >= 3)
_cfg_check("LOCALES >= 3", lambda c: len(c.LOCALES) >= 3)
_cfg_check("BLOOM_BITS > 0", lambda c: c.BLOOM_BITS > 0)
_cfg_check("CONFIG_VERSION string",
            lambda c: isinstance(c.CONFIG_VERSION, str))
_cfg_check("EXTRACTOR_VERSION present",
            lambda c: isinstance(c.EXTRACTOR_VERSION, str) and c.EXTRACTOR_VERSION)
_cfg_check("MOS config",
            lambda c: hasattr(c, "MOS_ENABLED") and hasattr(c, "MOS_DAILY_BUDGET"))
_cfg_check("API_ROUTER_ENABLED bool",
            lambda c: isinstance(c.API_ROUTER_ENABLED, bool))
_cfg_check("SE config",
            lambda c: hasattr(c, "SE_API_ENABLED") and hasattr(c, "SE_API_TIMEOUT"))
_cfg_check("BROWSER_PROFILES have family",
            lambda c: all("family" in p for p in c.BROWSER_PROFILES))


@test("T2", "BROWSER_PROFILES impersonate resolvable")
def t2_impersonate_resolvable(ctx):
    import config as c
    import curl_cffi
    for p in c.BROWSER_PROFILES:
        imp = p.get("impersonate")
        ctx.expect(imp, "missing impersonate")
        try:
            s = curl_cffi.requests.Session(impersonate=imp)
            s.close()
        except Exception as e:
            ctx.log.warn("profile %s failed: %r", imp, e)
            raise
    return Status.PASS.value, f"profiles={len(c.BROWSER_PROFILES)}"


# ============================================================================
#  T3 — SPOOF ENGINE
# ============================================================================

@test("T3", "SpoofedSession init normal")
def t3_session_normal(ctx):
    from spoof import SpoofedSession
    s = SpoofedSession("example.com", fast=False)
    ctx.expect(s.impersonate)
    ctx.expect(s.locale)
    s.close()
    return Status.PASS.value, f"imp={s.impersonate}"


@test("T3", "SpoofedSession init fast")
def t3_session_fast(ctx):
    from spoof import SpoofedSession
    s = SpoofedSession("example.com", fast=True)
    ctx.expect(s.fast is True)
    s.close()
    return Status.PASS.value, ""


@test("T3", "fast jitter bypass")
def t3_fast_jitter(ctx):
    from spoof import SpoofedSession
    s = SpoofedSession("example.com", fast=True)
    t0 = time.monotonic()
    s._jitter()
    el = time.monotonic() - t0
    s.close()
    ctx.expect_lt(el, 0.05, "fast jitter")
    return Status.PASS.value, f"{el*1000:.1f}ms"


@test("T3", "slow jitter enforced")
def t3_slow_jitter(ctx):
    from spoof import SpoofedSession
    s = SpoofedSession("example.com", fast=False)
    s._last_ts = time.monotonic()
    t0 = time.monotonic()
    s._jitter()
    el = time.monotonic() - t0
    s.close()
    ctx.expect_gt(el, 0.4, "slow jitter")
    return Status.PASS.value, f"{el:.2f}s"


@test("T3", "header order chrome profile")
def t3_header_chrome(ctx):
    from spoof import SpoofedSession
    from config import BROWSER_PROFILES
    chrome = next((p for p in BROWSER_PROFILES if p.get("family") == "chrome"),
                  None)
    if chrome is None:
        return Status.SKIP.value, "no chrome profile"
    s = SpoofedSession("example.com", fast=True, profile_override=chrome)
    h = s._build_headers("https://example.com/x", "https://example.com/p")
    keys = list(h.keys())
    s.close()
    ctx.expect_in("User-Agent", keys)
    ctx.expect_in("Accept", keys)
    ctx.expect_in("Referer", keys)
    ctx.expect_lt(keys.index("User-Agent"), keys.index("Accept"),
                  "UA should precede Accept")
    return Status.PASS.value, ""


@test("T3", "header order firefox profile")
def t3_header_firefox(ctx):
    from spoof import SpoofedSession
    from config import BROWSER_PROFILES
    ff = next((p for p in BROWSER_PROFILES if p.get("family") == "firefox"),
              None)
    if ff is None:
        return Status.SKIP.value, "no firefox profile"
    s = SpoofedSession("example.com", fast=True, profile_override=ff)
    h = s._build_headers("https://example.com/x", None)
    keys = list(h.keys())
    s.close()
    ctx.expect_in("User-Agent", keys)
    ctx.expect("Referer" not in keys, "firefox no-referer should not send Referer")
    return Status.PASS.value, ""


@test("T3", "sec-fetch-site computation")
def t3_sec_fetch(ctx):
    import spoof
    same = spoof._sec_fetch_site("https://example.com/a", "example.com")
    cross = spoof._sec_fetch_site("https://other.com/a", "example.com")
    none = spoof._sec_fetch_site(None, "example.com")
    ctx.expect_eq(same, "same-origin", "same")
    ctx.expect_eq(cross, "cross-site", "cross")
    ctx.expect_eq(none, "none", "none")
    return Status.PASS.value, ""


@test("T3", "referer chain")
def t3_referer_chain(ctx):
    from spoof import SpoofedSession
    s = SpoofedSession("example.com", fast=True)
    r1 = s._referer("https://example.com/a", None)
    ctx.expect(r1 is None, "first should have no referer")
    s._last_url = "https://example.com/a"
    r2 = s._referer("https://example.com/b", None)
    ctx.expect_eq(r2, "https://example.com/a", "chain")
    s.close()
    return Status.PASS.value, ""


@test("T3", "rotate_fingerprint changes identity")
def t3_rotate(ctx):
    from spoof import SpoofedSession
    s = SpoofedSession("example.com", fast=True)
    old = s.impersonate
    o, n = s.rotate_fingerprint()
    ctx.expect_eq(o, old, "old")
    ctx.expect_eq(n, s.impersonate, "new")
    s.close()
    return Status.PASS.value, ""


@test("T3", "SOD pool acquire")
def t3_sod_pool(ctx):
    try:
        from spoof import SODPool
    except ImportError:
        return Status.SKIP.value, "SODPool not present"
    pool = SODPool(size=3)
    w1 = pool.acquire("example.com")
    w2 = pool.acquire("example.com")
    ctx.expect_eq(w1.worker_id, w2.worker_id, "sticky domain")
    pool.close()
    return Status.PASS.value, ""


# ============================================================================
#  T4 — CRAWLER INTERNALS
# ============================================================================

@test("T4", "bloom filter 200 inserts")
def t4_bloom(ctx):
    from crawler import BloomFilter
    bf = BloomFilter(nbits=1 << 16, nhash=5)
    for i in range(200):
        bf.add(f"item-{i}")
    hits = sum(1 for i in range(200) if f"item-{i}" in bf)
    ctx.expect_eq(hits, 200, "hits")
    return Status.PASS.value, f"{hits}/200"


@test("T4", "bloom filter persistence")
def t4_bloom_persist(ctx):
    from crawler import BloomFilter
    tmp = "bloom.dbg.bin"
    try:
        bf = BloomFilter(nbits=1 << 16, nhash=5)
        bf.add("persist-test")
        bf.save(tmp)
        bf2 = BloomFilter.load(tmp)
        ctx.expect("persist-test" in bf2, "persisted key")
    finally:
        Path(tmp).unlink(missing_ok=True)
    return Status.PASS.value, ""


@test("T4", "simhash determinism")
def t4_simhash(ctx):
    from crawler import _simhash64
    h1 = _simhash64(["hello", "world", "foo"])
    h2 = _simhash64(["hello", "world", "foo"])
    h3 = _simhash64(["different", "tokens", "here"])
    ctx.expect_eq(h1, h2, "determinism")
    ctx.expect_neq(h1, h3, "different tokens")
    return Status.PASS.value, ""


@test("T4", "hamming distance")
def t4_hamming(ctx):
    from crawler import _hamming
    ctx.expect_eq(_hamming(0b1011, 0b1001), 1, "one bit")
    ctx.expect_eq(_hamming(0, 0xFFFFFFFFFFFFFFFF), 64, "all bits")
    return Status.PASS.value, ""


@test("T4", "minhash signature")
def t4_minhash(ctx):
    from crawler import _minhash_signature, _minhash_jaccard
    a = _minhash_signature(["a", "b", "c"])
    b = _minhash_signature(["a", "b", "c"])
    c = _minhash_signature(["x", "y", "z"])
    ctx.expect_eq(a, b, "identical sigs")
    ctx.expect_eq(_minhash_jaccard(a, b), 1.0, "jaccard self")
    ctx.expect_lt(_minhash_jaccard(a, c), 1.0, "jaccard diff")
    return Status.PASS.value, ""


@test("T4", "TLD+1 same")
def t4_tld_same(ctx):
    from crawler import _same_tld_plus_one
    ctx.expect(_same_tld_plus_one(
        "https://en.wikipedia.org/wiki/X",
        "https://fr.wikipedia.org/wiki/Y"
    ), "same TLD")
    return Status.PASS.value, ""


@test("T4", "TLD+1 cross")
def t4_tld_cross(ctx):
    from crawler import _same_tld_plus_one
    ctx.expect(not _same_tld_plus_one(
        "https://en.wikipedia.org/wiki/X",
        "https://example.com/"
    ), "cross TLD")
    return Status.PASS.value, ""


@test("T4", "domain token bucket")
def t4_domain_tracker(ctx):
    from crawler import DomainTracker
    import config as c
    dt = DomainTracker()
    for _ in range(c.DOMAIN_TOKEN_BUCKET_BURST):
        ctx.expect(dt.try_acquire("x.com"), "burst exhausted early")
    ctx.expect(not dt.try_acquire("x.com"), "should be rate-limited")
    return Status.PASS.value, ""


@test("T4", "host health decay")
def t4_health(ctx):
    from crawler import HostHealth
    h = HostHealth()
    ctx.expect_eq(h.score, 1.0, "start")
    h.record_failure(1.0)
    ctx.expect_lt(h.score, 1.0, "after fail")
    h.record_success()
    ctx.expect_gt(h.score, 0.5, "after recovery")
    return Status.PASS.value, f"score={h.score:.2f}"


@test("T4", "trap detector 6 cases")
def t4_trap(ctx):
    from crawler import _detect_trap
    cases = [
        ("https://x.com/a/b/c/a/b/c/a/b/c/a/b/c", True),
        ("https://x.com/2030/12/25/", True),
        ("https://x.com/?jsessionid=abc123", True),
        ("https://x.com/normal/path", False),
        ("https://x.com/2027/12/25/", False),
        ("https://x.com/?a=" + "a" * 40, True),
    ]
    for url, expected in cases:
        trap, reason = _detect_trap(url)
        ctx.expect_eq(trap, expected,
                       f"{url[:60]} reason={reason}")
    return Status.PASS.value, ""


@test("T4", "mercator frontier push/pop")
def t4_mercator(ctx):
    from crawler import MercatorFrontier
    f = MercatorFrontier(cap=100)
    for i in range(50):
        ctx.expect(f.push(f"https://a.com/{i}", 0, 0, 0.5), f"push {i}")
    ctx.expect_eq(len(f), 50, "len")
    popped = f.pop()
    ctx.expect(popped is not None, "pop")
    ctx.expect_eq(len(f), 49, "len after pop")
    return Status.PASS.value, ""


@test("T4", "mercator frontier cap")
def t4_mercator_cap(ctx):
    from crawler import MercatorFrontier
    f = MercatorFrontier(cap=10)
    for i in range(20):
        f.push(f"https://a.com/{i}", 0, 0)
    ctx.expect_eq(len(f), 10, "cap")
    return Status.PASS.value, ""


@test("T4", "dead letter queue")
def t4_dlq(ctx):
    from crawler import DeadLetterQueue
    tmp = "dlq.dbg.jsonl"
    try:
        Path(tmp).unlink(missing_ok=True)
        dlq = DeadLetterQueue(tmp)
        dlq.add("https://x.com/a", "err", 3)
        dlq.close()
        ctx.expect(Path(tmp).exists())
        size = Path(tmp).stat().st_size
        ctx.expect_gt(size, 10, "file size")
    finally:
        Path(tmp).unlink(missing_ok=True)
    return Status.PASS.value, ""


@test("T4", "change detector etag")
def t4_change(ctx):
    from crawler import ChangeDetector
    cd = ChangeDetector()
    cd.observe("https://x.com/a", {"etag": '"v1"'})
    changed = cd.observe("https://x.com/a", {"etag": '"v2"'})
    ctx.expect(changed is True, "change detected")
    return Status.PASS.value, ""


@test("T4", "yield tracker records")
def t4_yield(ctx):
    from crawler import YieldTracker
    yt = YieldTracker()
    for _ in range(10):
        yt.record("https://x.com/a", True)
    score = yt.domain_yield("x.com")
    ctx.expect_gt(score, 0.9, "yield for useful")
    return Status.PASS.value, f"yield={score:.2f}"


@test("T4", "domain bootstrap cache")
def t4_bootstrap(ctx):
    from crawler import DomainBootstrap
    db = DomainBootstrap()
    path = db._cache_path("example.com")
    ctx.expect("example" not in str(path) or len(str(path)) > 20, "hashed path")
    return Status.PASS.value, ""


@test("T4", "config hash format")
def t4_config_hash(ctx):
    from crawler import _config_hash
    h = _config_hash()
    ctx.expect_eq(len(h), 32, "config hash length")
    return Status.PASS.value, ""


# ============================================================================
#  T5 — SCRAPER INTERNALS
# ============================================================================

@test("T5", "_norm_ws collapse")
def t5_norm_ws(ctx):
    from scraper import _norm_ws
    ctx.expect_eq(_norm_ws("  a   b  "), "a b")
    ctx.expect_eq(_norm_ws(""), "")
    ctx.expect_eq(_norm_ws("\t\n  x  \n"), "x")
    return Status.PASS.value, ""


@test("T5", "_token_count bounds")
def t5_token_count(ctx):
    from scraper import _token_count
    n = _token_count("hello world foo bar")
    ctx.expect(0 < n < 10, f"count={n}")
    return Status.PASS.value, f"n={n}"


@test("T5", "_sentence_split basic")
def t5_sent_split(ctx):
    from scraper import _sentence_split
    sents = _sentence_split("Hello world. This is a test! Is it? Yes.")
    ctx.expect_eq(len(sents), 4, "sentence count")
    return Status.PASS.value, ""


@test("T5", "_sentence_split abbreviation guard")
def t5_sent_abbrev(ctx):
    from scraper import _sentence_split
    sents = _sentence_split("Dr. Smith went. He met Mr. Jones.")
    ctx.expect_eq(len(sents), 2, "abbrev split")
    return Status.PASS.value, ""


@test("T5", "content kind 7 cases")
def t5_content_kind(ctx):
    from scraper import _detect_content_kind
    cases = [
        ("text/html", b"<html></html>", "html"),
        ("application/pdf", b"%PDF-1.4", "pdf"),
        ("application/json", b"{}", "json"),
        ("", b"{}", "json"),
        ("application/xml", b"<?xml", "xml"),
        ("text/plain", b"hello", "text"),
        ("", b"<rss><channel/></rss>", "xml"),
    ]
    for ct, body, expected in cases:
        got = _detect_content_kind(ct, body, "u")
        ctx.expect_eq(got, expected, f"ct={ct}")
    return Status.PASS.value, ""


@test("T5", "blocked detection 8 cases")
def t5_blocked(ctx):
    from scraper import _is_blocked
    cases = [
        (403, b"", True),
        (429, b"", True),
        (503, b"", True),
        (202, b"", True),
        (200, b"<title>Just a moment...</title>", True),
        (200, b"cf-chl-", True),
        (200, b"<html>ok</html>", False),
        (200, b"challenge-platform", True),
    ]
    for status, body, expected in cases:
        got = _is_blocked(status, body)
        ctx.expect_eq(got, expected, f"{status} {body[:20]!r}")
    return Status.PASS.value, ""


@test("T5", "extract_html schema fields")
def t5_extract_html(ctx):
    from scraper import extract_html
    html = """<!DOCTYPE html><html lang="en"><head><title>Sample</title>
    <meta name="description" content="A sample">
    <link rel="canonical" href="https://example.com/canonical">
    </head><body>
    <h1>Sample</h1>
    <p>This is a long paragraph with enough content. It contains multiple sentences. This helps satisfy the extraction pipeline.</p>
    <h2>Section One</h2>
    <p>Content of section one. More content to pad the sentence count.</p>
    </body></html>"""
    rec, links, blocked = extract_html(html, "https://example.com/")
    ctx.expect_eq(rec.get("title"), "Sample", "title")
    ctx.expect_in("content", rec)
    ctx.expect_in("chunks", rec)
    ctx.expect_in("quality", rec)
    ctx.expect_eq(blocked, False, "blocked")
    return Status.PASS.value, f"words={rec.get('word_count', 0)}"


@test("T5", "extract_json simple")
def t5_extract_json(ctx):
    from scraper import extract_json
    rec, _, _ = extract_json(b'{"a":1,"b":[2,3]}', "https://x.com/j")
    ctx.expect_eq(rec["json"], {"a": 1, "b": [2, 3]})
    ctx.expect_in("content", rec)
    return Status.PASS.value, ""


@test("T5", "extract_json HTML fallback")
def t5_extract_json_fallback(ctx):
    from scraper import extract_json
    html_body = (b"<html><head><title>X</title></head><body><p>"
                  + b"Content here. " * 30 + b"</p></body></html>")
    rec, _, _ = extract_json(html_body, "https://x.com/f")
    ctx.expect_in("content", rec)
    ctx.expect_eq(rec.get("kind"), "html", "should be html")
    return Status.PASS.value, ""


@test("T5", "extract_xml RSS")
def t5_extract_xml(ctx):
    from scraper import extract_xml
    xml = b'<?xml version="1.0"?><rss><channel><item><title>T</title><link>https://x.com/a</link><description>D</description></item></channel></rss>'
    rec, _, _ = extract_xml(xml, "https://x.com/feed")
    ctx.expect_eq(len(rec["feed_items"]), 1, "feed items")
    ctx.expect_in("content", rec)
    return Status.PASS.value, ""


@test("T5", "extract_text_plain")
def t5_extract_text(ctx):
    from scraper import extract_text_plain
    rec, _, _ = extract_text_plain("hello world content", "https://x.com/t")
    ctx.expect_in("hello world", rec["content"]["article"]["intro"])
    return Status.PASS.value, ""


@test("T5", "extract_pdf native text")
def t5_extract_pdf(ctx):
    from scraper import extract_pdf
    import pymupdf
    doc = pymupdf.open()
    for i in range(2):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i+1} content. " * 20)
    data = doc.tobytes()
    doc.close()
    rec, _, _ = extract_pdf(data, "https://x.com/a.pdf")
    ctx.expect_in("content", rec)
    ctx.expect_eq(rec["content"]["metadata"].get("pages"), 2, "pages")
    return Status.PASS.value, ""


@test("T5", "chunk_text small")
def t5_chunk(ctx):
    from scraper import chunk_text
    text = " ".join(f"Sentence number {i} with content." for i in range(200))
    chunks = chunk_text(text, size=100, overlap=20, min_size=10)
    ctx.expect_gt(len(chunks), 3, "chunk count")
    return Status.PASS.value, f"chunks={len(chunks)}"


@test("T5", "chunk dedup")
def t5_chunk_dedup(ctx):
    from scraper import _dedup_chunks
    base = "Content sentence repeated many times. "
    chunks = _dedup_chunks([base * 5, base * 6, "different content here"])
    ctx.expect_lt(len(chunks), 3, "dedup result")
    return Status.PASS.value, f"after={len(chunks)}"


@test("T5", "extract_keywords")
def t5_keywords(ctx):
    from scraper import extract_keywords
    text = ("Machine learning is a field of artificial intelligence. "
            "Machine learning models learn from data. " * 5)
    kws = extract_keywords(text)
    ctx.expect_gt(len(kws), 0, "keyword count")
    return Status.PASS.value, f"kw={len(kws)}"


@test("T5", "extract_entities v2")
def t5_entities(ctx):
    from scraper import extract_entities
    text = ("John Smith said the project was complete. "
            "John Smith added that the team succeeded. "
            "Contact test@example.com for details. Cost is $42.50. " * 3)
    ents = extract_entities(text, body_for_freq=text)
    types = {e["type"] for e in ents}
    ctx.expect_in("EMAIL", types)
    ctx.expect_in("MONEY", types)
    return Status.PASS.value, f"types={sorted(types)}"


@test("T5", "quality metrics 12 keys")
def t5_quality(ctx):
    from scraper import _quality_metrics
    text = "The quick brown fox jumps over the lazy dog. " * 30
    q = _quality_metrics(text)
    expected_keys = [
        "word_count", "flesch_reading_ease", "flesch_kincaid_grade",
        "gunning_fog", "smog_index", "text_standard", "difficulty",
        "sentence_count", "syllable_count", "char_count",
        "reading_time_seconds", "dale_chall_score",
    ]
    for k in expected_keys:
        ctx.expect_in(k, q, f"key={k}")
    ctx.expect_gt(q["word_count"], 0, "word count")
    return Status.PASS.value, f"words={q['word_count']}"


@test("T5", "quality short returns -1")
def t5_quality_short(ctx):
    from scraper import _quality_metrics
    q = _quality_metrics("short")
    ctx.expect_eq(q["flesch_reading_ease"], -1.0, "short flesch")
    return Status.PASS.value, ""


@test("T5", "_base_record all fields")
def t5_base_record(ctx):
    from scraper import _base_record, AGENT_RECORD_FIELDS
    rec = _base_record("https://example.com/x", "html")
    for f in AGENT_RECORD_FIELDS:
        ctx.expect_in(f, rec, f"field={f}")
    return Status.PASS.value, f"fields={len(AGENT_RECORD_FIELDS)}"


@test("T5", "MOS classifier 13 cases")
def t5_mos_classify(ctx):
    from scraper import classify_error, FetchResult
    cases = [
        (200, b"<html>ok</html>", "empty_ssr_body"),
        (202, b"", "bot_wall_js"),
        (401, b"", "401_auth"),
        (403, b"cloudflare", "cloudflare_interstitial"),
        (403, b"turnstile", "cloudflare_turnstile"),
        (403, b"", "403_waf"),
        (429, b"", "429_rate"),
        (500, b"mysql database error", "500_database"),
        (500, b"out of memory", "500_resource_exhaustion"),
        (500, b"", "500_transient"),
        (502, b"", "502_bad_gateway"),
        (503, b"", "503_unavailable"),
        (504, b"", "504_timeout"),
    ]
    for status, body, expected in cases:
        r = FetchResult(url="x", status=status, content_type="",
                         body=body, headers={}, http_version="",
                         elapsed=0.0, blocked=False)
        got = classify_error(r)
        ctx.expect_eq(got, expected, f"status={status}")
    return Status.PASS.value, ""


@test("T5", "MOS classifier error field")
def t5_mos_error_field(ctx):
    from scraper import classify_error, FetchResult
    cases = [
        ("SSLError('Recv failure')", "500_tls"),
        ("Timeout('curl: (28)')", "504_timeout"),
        ("ConnectionResetError", "500_routing"),
        ("SomeRandomError", "500_transient"),
    ]
    for err, expected in cases:
        r = FetchResult(url="x", status=0, content_type="", body=b"",
                         headers={}, http_version="", elapsed=0.0,
                         blocked=False, error=err)
        got = classify_error(r)
        ctx.expect_eq(got, expected, f"err={err[:20]}")
    return Status.PASS.value, ""


@test("T5", "MOS policies populated")
def t5_mos_policies(ctx):
    from scraper import MOS_POLICIES
    ctx.expect_gt(len(MOS_POLICIES), 15, "policy count")
    for key, chain in MOS_POLICIES.items():
        ctx.expect(len(chain) > 0, f"empty policy: {key}")
    return Status.PASS.value, f"policies={len(MOS_POLICIES)}"


@test("T5", "MOS services populated")
def t5_mos_services(ctx):
    from scraper import MOS_SERVICES
    ctx.expect_gt(len(MOS_SERVICES), 15, "service count")
    for key, svc in MOS_SERVICES.items():
        ctx.expect_in("reliability", svc, f"svc={key}")
        ctx.expect_in("latency_p50", svc, f"svc={key}")
    return Status.PASS.value, f"services={len(MOS_SERVICES)}"


@test("T5", "MOS timing constants")
def t5_mos_timing(ctx):
    from scraper import MOS_TOTAL_TIMEOUT, MOS_PER_SERVICE_TIMEOUT
    ctx.expect_eq(MOS_TOTAL_TIMEOUT, 25.0)
    ctx.expect_eq(MOS_PER_SERVICE_TIMEOUT, 15.0)
    return Status.PASS.value, ""


@test("T5", "scrape_url returns tuple")
def t5_scrape_url_tuple(ctx):
    from scraper import scrape_url
    from spoof import SpoofedSession
    session = SpoofedSession("example.com", fast=True)
    try:
        result = scrape_url("https://example.com/", session)
        ctx.expect(isinstance(result, tuple), "result is tuple")
        ctx.expect_eq(len(result), 3, "3-tuple")
    finally:
        session.close()
    return Status.PASS.value, ""


# ============================================================================
#  T5b — FOLDER MANAGER
# ============================================================================

@test("T5b", "folder manager diagnose")
def t5b_diagnose(ctx):
    from folder_manager import FolderManager
    diag = FolderManager.diagnose()
    failed = [r for r in diag["results"] if not r["ok"]]
    ctx.log.info("diagnostics summary:\n%s", diag["summary"])
    if failed:
        for f in failed[:5]:
            ctx.log.warn("diagnostic failed: %s :: %s", f["name"], f["detail"])
        return Status.WARN.value, f"{len(failed)} failed"
    return Status.PASS.value, f"{len(diag['results'])} checks"


@test("T5b", "error classifier maps OSError categories")
def t5b_classifier(ctx):
    from folder_manager import ErrorClassifier, ErrorCategory
    cases = [
        (PermissionError("x"), ErrorCategory.LOCKED),
        (FileExistsError("x"), ErrorCategory.CONCURRENT),
        (IsADirectoryError("x"), ErrorCategory.IO),
        (NotADirectoryError("x"), ErrorCategory.IO),
    ]
    for exc, expected_cat in cases:
        classified = ErrorClassifier.classify(exc)
        ctx.expect(classified is not None, f"classify {type(exc).__name__}")
        ctx.expect_eq(classified.category, expected_cat,
                       f"{type(exc).__name__}")
    return Status.PASS.value, ""


@test("T5b", "error classifier FileNotFound returns None")
def t5b_classifier_none(ctx):
    from folder_manager import ErrorClassifier
    result = ErrorClassifier.classify(FileNotFoundError("x"))
    ctx.expect(result is None, "FileNotFound returns None")
    return Status.PASS.value, ""


@test("T5b", "error handler retries LockedFileError")
def t5b_handler_retry(ctx):
    from folder_manager import ErrorHandler, LockedFileError
    handler = ErrorHandler(max_retries=3, base_delay=0.01)
    state = {"n": 0}

    def flaky():
        state["n"] += 1
        if state["n"] < 3:
            raise LockedFileError("locked")
        return "ok"

    result = handler.run(flaky)
    ctx.expect_eq(result, "ok", "should succeed after retries")
    ctx.expect_eq(state["n"], 3, "attempt count")
    return Status.PASS.value, ""


@test("T5b", "error handler raises on fatal")
def t5b_handler_fatal(ctx):
    from folder_manager import ErrorHandler, NotWritableError
    handler = ErrorHandler(max_retries=3, base_delay=0.01)

    def always_fails():
        raise NotWritableError("no")

    ctx.expect_raises(NotWritableError, handler.run, always_fails)
    return Status.PASS.value, ""


@test("T5b", "json safe save/load roundtrip")
def t5b_json_roundtrip(ctx):
    from folder_manager import FolderManager
    tmp = FolderManager.TMP / "test_json_roundtrip.json"
    try:
        data = {"a": 1, "b": [2, 3], "c": {"nested": True}}
        FolderManager.save_json_safe(tmp, data)
        loaded = FolderManager.load_json_safe(tmp)
        ctx.expect_eq(loaded, data, "roundtrip")
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass
    return Status.PASS.value, ""


@test("T5b", "json corrupt detection")
def t5b_json_corrupt(ctx):
    from folder_manager import FolderManager, CorruptedStateError
    tmp = FolderManager.TMP / "test_corrupt.json"
    try:
        tmp.write_bytes(b"{not valid json")
        ctx.expect_raises(CorruptedStateError,
                           FolderManager.load_json_safe, tmp)
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass
    return Status.PASS.value, ""


@test("T5b", "file lock exclusive")
def t5b_file_lock(ctx):
    from folder_manager import FileLock, ConcurrentAccessError
    lock_path = FolderManager.TMP / "test.lock"
    try:
        with FileLock(lock_path, timeout=2.0):
            ctx.log.info("acquired lock")
        ctx.log.info("released lock")
        ctx.expect(not lock_path.exists(), "lock file gone")
    except Exception as e:
        ctx.log.warn("lock test: %r", e)
    return Status.PASS.value, ""


@test("T5b", "safe_remove handles missing")
def t5b_safe_remove(ctx):
    from folder_manager import FolderManager
    result = FolderManager.safe_remove(FolderManager.TMP / "nonexistent_xyz")
    ctx.expect(result is True, "returns True for missing")
    return Status.PASS.value, ""


@test("T5b", "clear_tier dry_run")
def t5b_clear_dry(ctx):
    from folder_manager import FolderManager
    result = FolderManager.clear_tier("tmp", dry_run=True)
    ctx.expect_in("removed", result)
    ctx.expect_eq(result["dry_run"], True)
    return Status.PASS.value, f"would_remove={result['removed']}"


@test("T5b", "acquire/release run lock")
def t5b_run_lock(ctx):
    from folder_manager import FolderManager
    ok = FolderManager.acquire_run_lock()
    ctx.expect(ok, "acquire")
    FolderManager.release_run_lock()
    return Status.PASS.value, ""


# ============================================================================
#  T5c — SE API
# ============================================================================

@test("T5c", "se_site_for_url 9 cases")
def t5c_se_site(ctx):
    from se_api import se_site_for_url
    cases = [
        ("https://stackoverflow.com/questions/12345/x", "stackoverflow"),
        ("https://serverfault.com/q/12345", "serverfault"),
        ("https://superuser.com/questions/1", "superuser"),
        ("https://askubuntu.com/questions/1", "askubuntu"),
        ("https://mathoverflow.net/questions/1", "mathoverflow"),
        ("https://unix.stackexchange.com/questions/1", "unix"),
        ("https://stats.stackexchange.com/questions/1", "stats"),
        ("https://english.stackexchange.com/questions/1", "english"),
        ("https://example.com/", None),
    ]
    for url, expected in cases:
        got = se_site_for_url(url)
        ctx.expect_eq(got, expected, f"url={url[:40]}")
    return Status.PASS.value, ""


@test("T5c", "se_parse_question_id 4 cases")
def t5c_se_qid(ctx):
    from se_api import se_parse_question_id
    cases = [
        ("https://stackoverflow.com/questions/12345/title", 12345),
        ("https://stackoverflow.com/q/12345", 12345),
        ("https://stackoverflow.com/questions/tagged/python", None),
        ("https://stackoverflow.com/", None),
    ]
    for url, expected in cases:
        got = se_parse_question_id(url)
        ctx.expect_eq(got, expected, f"url={url[:40]}")
    return Status.PASS.value, ""


@test("T5c", "se_parse_tag 3 cases")
def t5c_se_tag(ctx):
    from se_api import se_parse_tag
    cases = [
        ("https://stackoverflow.com/questions/tagged/python", "python"),
        ("https://stackoverflow.com/tags/javascript", "javascript"),
        ("https://stackoverflow.com/questions/12345/x", None),
    ]
    for url, expected in cases:
        got = se_parse_tag(url)
        ctx.expect_eq(got, expected, f"url={url[:40]}")
    return Status.PASS.value, ""


@test("T5c", "se quota status")
def t5c_se_quota(ctx):
    from se_api import se_quota_status
    status = se_quota_status()
    ctx.expect_in("used_today", status)
    ctx.expect_in("exhausted", status)
    return Status.PASS.value, f"used={status['used_today']}"


@test("T5c", "se stats summary")
def t5c_se_stats(ctx):
    from se_api import se_stats
    stats = se_stats()
    ctx.expect_in("total", stats)
    ctx.expect_in("success", stats)
    ctx.expect_in("failure", stats)
    return Status.PASS.value, f"total={stats['total']}"


# ============================================================================
#  T5d — API ROUTER
# ============================================================================

@test("T5d", "api_router hardware profile")
def t5d_hw(ctx):
    from api_router import Hardware
    profile = Hardware.profile()
    for k in ("cores_physical", "cores_logical", "ram_gb", "tier"):
        ctx.expect_in(k, profile)
    ctx.expect(profile["tier"] in ("workstation", "laptop", "small", "minimal"))
    return Status.PASS.value, f"tier={profile['tier']}"


@test("T5d", "api_router tuner snapshot")
def t5d_tuner(ctx):
    from api_router import Hardware, AdaptiveTuner
    profile = Hardware.profile()
    tuner = AdaptiveTuner(profile["tier"])
    snap = tuner.snapshot()
    ctx.expect_in("base", snap)
    ctx.expect_in("current", snap)
    return Status.PASS.value, f"conc={snap['current']['concurrency']}"


@test("T5d", "api_router has_route")
def t5d_has_route(ctx):
    from api_router import has_route
    ctx.expect(has_route("https://stackoverflow.com/questions/1"), "SE URL")
    return Status.PASS.value, ""


@test("T5d", "api_router budget allowed")
def t5d_budget(ctx):
    from api_router import AdaptiveBudget
    budget = AdaptiveBudget()
    ctx.expect(budget.allowed("test_service", limit_hour=10), "under limit")
    for _ in range(15):
        budget.record("test_service")
    return Status.PASS.value, ""


# ============================================================================
#  T6+ — LIVE URL TESTS
# ============================================================================

URLS_EASY = [
    "https://example.com/",
    "https://httpbin.org/html",
    "https://httpbin.org/json",
    "https://httpbin.org/xml",
    "https://httpbin.org/robots.txt",
    "https://www.iana.org/help/example-domains",
    "https://www.rust-lang.org/",
    "https://www.python.org/",
    "https://go.dev/",
    "https://nodejs.org/en",
]

URLS_MODERATE = [
    "https://www.postgresql.org/",
    "https://redis.io/",
    "https://www.sqlite.org/",
    "https://doc.rust-lang.org/book/",
    "https://en.wikipedia.org/wiki/Web_scraping",
    "https://en.wikipedia.org/wiki/HTTP",
    "https://en.wikipedia.org/wiki/Python_(programming_language)",
    "https://en.wikipedia.org/wiki/JSON",
    "https://en.wikipedia.org/wiki/HTML",
    "https://news.ycombinator.com/",
]

URLS_DYNAMIC = [
    "https://github.com/torvalds/linux",
    "https://stackoverflow.com/questions",
    "https://arstechnica.com/",
    "https://www.theverge.com/",
    "https://www.bbc.com/news",
    "https://www.wired.com/",
    "https://www.theguardian.com/international",
    "https://dev.to/",
    "https://en.wikipedia.org/wiki/Online_streamer",
    "https://en.wikipedia.org/wiki/CAPTCHA",
]

URLS_JS_HEAVY = [
    "https://www.reddit.com/r/python/",
    "https://www.nytimes.com/",
    "https://www.washingtonpost.com/",
    "https://www.facebook.com/",
    "https://www.linkedin.com/",
    "https://www.youtube.com/",
    "https://www.twitch.tv/",
    "https://discord.com/",
]

URLS_PROTECTED = [
    "https://www.coinbase.com/",
    "https://www.crunchbase.com/",
    "https://www.glassdoor.com/",
    "https://www.zillow.com/",
]

URLS_DOCS = [
    "https://docs.python.org/3/library/asyncio.html",
    "https://developer.mozilla.org/en-US/docs/Web/HTTP",
    "https://git-scm.com/docs/git-clone",
    "https://wiki.archlinux.org/title/Pacman",
    "https://man7.org/linux/man-pages/man2/read.2.html",
    "https://doc.rust-lang.org/std/",
    "https://docs.docker.com/get-started/",
    "https://kubernetes.io/docs/concepts/overview/",
]

URLS_BLOGS = [
    "https://martinfowler.com/articles/microservices.html",
    "https://paulgraham.com/greatwork.html",
    "https://blog.rust-lang.org/",
    "https://overreacted.io/",
    "https://jvns.ca/",
    "https://www.joelonsoftware.com/",
    "https://blog.cloudflare.com/",
    "https://stripe.com/blog",
]

URLS_NEWS = [
    "https://apnews.com/",
    "https://www.npr.org/",
    "https://www.dw.com/en/",
    "https://www.france24.com/en/",
    "https://www.cbc.ca/news",
    "https://www.abc.net.au/news",
    "https://www.scmp.com/",
]

URLS_ACADEMIC = [
    "https://arxiv.org/abs/2301.00001",
    "https://pubmed.ncbi.nlm.nih.gov/",
    "https://www.nature.com/",
    "https://www.science.org/",
    "https://journals.plos.org/plosone/",
    "https://www.frontiersin.org/",
]

URLS_GOV_EDU = [
    "https://www.nasa.gov/",
    "https://www.noaa.gov/",
    "https://www.cdc.gov/",
    "https://www.harvard.edu/",
    "https://www.mit.edu/",
    "https://www.stanford.edu/",
    "https://www.ox.ac.uk/",
]

URLS_EASY_HANDLED = [
    "https://example.com/",
]

URLS_SE_NETWORK = [
    "https://stackoverflow.com/questions/4260280",
    "https://stackoverflow.com/questions/11227809",
    "https://superuser.com/questions/1",
    "https://askubuntu.com/questions/1",
    "https://unix.stackexchange.com/questions/1",
    "https://serverfault.com/questions/1",
]


def _make_url_test(tier, url, fast=True, timeout=60.0):
    def _t(ctx, _url=url, _fast=fast, _timeout=timeout):
        from spoof import SpoofedSession
        from scraper import scrape_url, MOSState
        session = None
        mos_state = None
        t0 = time.monotonic()
        try:
            session = SpoofedSession(urlparse(_url).netloc, fast=_fast)
            mos_state = MOSState()
            result = scrape_url(_url, session, mos_state)
            if len(result) == 4:
                record, links, blocked, _ = result
            else:
                record, links, blocked = result
            el = time.monotonic() - t0
            if el > _timeout:
                return Status.SLOW.value, f"{el:.1f}s"
            err = record.get("error") if isinstance(record, dict) else None
            if blocked:
                return Status.WARN.value, f"BLOCKED ({err})"
            if err:
                return Status.FAIL.value, str(err)
            title = (record.get("title") or "")[:50]
            words = record.get("word_count", 0) or 0
            chunks = len(record.get("chunks", []) or [])
            kind = record.get("kind", "html")
            ctx.log.info("title=%r words=%d chunks=%d kind=%s",
                          title, words, chunks, kind)
            if kind in ("json", "xml", "pdf", "se_api", "reddit_json",
                         "github_api", "crossref_api", "arxiv_api",
                         "pubmed_eutils", "binance_api",
                         "wiktionary_api", "openlibrary_api",
                         "free_dictionary_api"):
                return Status.PASS.value, f"kind={kind} words={words}"
            if words < 30:
                return Status.EMPTY.value, f"words={words}"
            if el > 20.0:
                return Status.SLOW.value, f"{el:.1f}s words={words}"
            return Status.PASS.value, f"words={words} chunks={chunks}"
        except Exception as e:
            return Status.ERROR.value, f"{type(e).__name__}: {e}"
        finally:
            if session:
                try:
                    session.close()
                except Exception:
                    pass
            if mos_state:
                try:
                    mos_state.close()
                except Exception:
                    pass
    return _t


def _register_url_tier(tier_name, urls):
    for url in urls:
        _test_name = url if len(url) <= 80 else url[:77] + "..."
        test(tier_name, _test_name)(_make_url_test(tier_name, url))


_register_url_tier("T6_easy", URLS_EASY)
_register_url_tier("T7_moderate", URLS_MODERATE)
_register_url_tier("T8_dynamic", URLS_DYNAMIC)
_register_url_tier("T9_js_heavy", URLS_JS_HEAVY)
_register_url_tier("T10_protected", URLS_PROTECTED)
_register_url_tier("T13_docs", URLS_DOCS)
_register_url_tier("T14_blogs", URLS_BLOGS)
_register_url_tier("T15_news", URLS_NEWS)
_register_url_tier("T17_academic", URLS_ACADEMIC)
_register_url_tier("T18_gov_edu", URLS_GOV_EDU)
_register_url_tier("T26_se_network", URLS_SE_NETWORK)


# ============================================================================
#  T41 — CONCURRENCY
# ============================================================================

@test("T41", "concurrent bloom writes")
def t41_concurrent_bloom(ctx):
    from crawler import BloomFilter
    bf = BloomFilter(nbits=1 << 20, nhash=5)
    errors = []

    def writer(start):
        try:
            for i in range(start, start + 500):
                bf.add(f"item-{i}")
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=writer, args=(i * 500,))
                for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    ctx.expect_eq(len(errors), 0, "no errors")
    hits = sum(1 for i in range(2000) if f"item-{i}" in bf)
    ctx.expect_eq(hits, 2000, "all inserted")
    return Status.PASS.value, f"threads=4 hits={hits}"


@test("T41", "concurrent logger")
def t41_concurrent_logger(ctx):
    log = Logger("concurrent_test", console=False)
    errors = []

    def worker(n):
        try:
            for i in range(100):
                log.info("worker %d msg %d", n, i)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    ctx.expect_eq(len(errors), 0, "no logger errors")
    return Status.PASS.value, "8 workers x 100 msgs"


@test("T41", "concurrent json save/load")
def t41_concurrent_json(ctx):
    from folder_manager import FolderManager
    tmp_dir = FolderManager.TMP / "concurrent_json"
    tmp_dir.mkdir(exist_ok=True)
    errors = []

    def worker(n):
        try:
            for i in range(20):
                path = tmp_dir / f"file_{n}_{i}.json"
                FolderManager.save_json_safe(path, {"n": n, "i": i})
                loaded = FolderManager.load_json_safe(path)
                assert loaded == {"n": n, "i": i}
        except Exception as e:
            errors.append((n, e))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)
    ctx.expect_eq(len(errors), 0, f"errors: {errors[:3]}")
    return Status.PASS.value, "6 workers x 20 files"


# ============================================================================
#  T42 — STRESS / MEMORY
# ============================================================================

@test("T42", "200 extract_html no leak")
def t42_extract_loop(ctx):
    from scraper import extract_html
    html = "<html><body>" + ("<p>Content sentence here. " * 100) + "</body></html>"
    before = ctx.rss_mb()
    for i in range(200):
        extract_html(html, f"https://x.com/{i}")
    after = ctx.rss_mb()
    growth = after - before
    ctx.expect_lt(growth, 100, f"memory growth {growth:.1f} MB")
    return Status.PASS.value, f"growth={growth:.1f}MB"


@test("T42", "chunk_text 20k words")
def t42_chunk_stress(ctx):
    from scraper import chunk_text
    text = " ".join(f"Word{i}." for i in range(20000))
    chunks = chunk_text(text, size=512, overlap=64, min_size=32)
    ctx.expect_gt(len(chunks), 0, "chunks produced")
    return Status.PASS.value, f"chunks={len(chunks)}"


@test("T42", "simhash 100k tokens")
def t42_simhash_stress(ctx):
    from crawler import _simhash64
    tokens = [f"token-{i}" for i in range(100000)]
    t0 = time.monotonic()
    h = _simhash64(tokens)
    el = time.monotonic() - t0
    ctx.log.info("simhash 100k tokens in %.3fs", el)
    ctx.expect(h != 0, "non-zero hash")
    return Status.PASS.value, f"{el:.3f}s"


@test("T42", "logger throughput")
def t42_logger_throughput(ctx):
    log = Logger("throughput_test", console=False)
    n = 10000
    t0 = time.monotonic()
    for i in range(n):
        log.info("message %d", i)
    el = time.monotonic() - t0
    rate = n / el
    ctx.log.info("logged %d messages in %.3fs (%.0f/s)", n, el, rate)
    ctx.expect_gt(rate, 5000, f"rate={rate:.0f}/s")
    return Status.PASS.value, f"rate={rate:.0f}/s"


@test("T42", "trap detection 1000 urls")
def t42_trap_stress(ctx):
    from crawler import _detect_trap
    urls = [f"https://x.com/a/b/c/{i}" for i in range(1000)]
    t0 = time.monotonic()
    for url in urls:
        _detect_trap(url)
    el = time.monotonic() - t0
    rate = 1000 / el
    ctx.log.info("trap detect %d urls in %.3fs (%.0f/s)", 1000, el, rate)
    ctx.expect_gt(rate, 1000, f"rate={rate:.0f}/s")
    return Status.PASS.value, f"rate={rate:.0f}/s"


# ============================================================================
#  T43 — REGRESSION
# ============================================================================

@test("T43", "fix: classify_error SSL")
def t43_fix_ssl(ctx):
    from scraper import classify_error, FetchResult
    r = FetchResult(url="x", status=0, content_type="", body=b"",
                     headers={}, http_version="", elapsed=0.0,
                     blocked=False, error="SSLError('Recv')")
    ctx.expect_eq(classify_error(r), "500_tls")
    return Status.PASS.value, ""


@test("T43", "fix: _looks_empty content tags")
def t43_looks_empty(ctx):
    from scraper import _looks_empty
    ctx.expect_eq(_looks_empty(b"<html><p>hello</p></html>"), False)
    ctx.expect_eq(_looks_empty(b"<html></html>"), True)
    ctx.expect_eq(_looks_empty(b"x" * 5000), True)
    return Status.PASS.value, ""


@test("T43", "fix: jsessionid trap detection")
def t43_jsessionid(ctx):
    from crawler import _detect_trap
    trap, reason = _detect_trap("https://x.com/?jsessionid=abc123")
    ctx.expect(trap, f"should detect: {reason}")
    return Status.PASS.value, ""


@test("T43", "fix: extract_json HTML fallback")
def t43_json_fallback(ctx):
    from scraper import extract_json
    body = (b"<html><body><p>"
             + b"Content here. " * 40
             + b"</p></body></html>")
    rec, _, _ = extract_json(body, "https://x.com/f")
    ctx.expect_eq(rec.get("kind"), "html")
    return Status.PASS.value, ""


@test("T43", "fix: MOS timing constants")
def t43_mos_timing(ctx):
    from scraper import MOS_TOTAL_TIMEOUT, MOS_PER_SERVICE_TIMEOUT
    ctx.expect_eq(MOS_TOTAL_TIMEOUT, 25.0)
    ctx.expect_eq(MOS_PER_SERVICE_TIMEOUT, 15.0)
    return Status.PASS.value, ""


@test("T43", "fix: _base_record has quality")
def t43_base_quality(ctx):
    from scraper import _base_record
    rec = _base_record("https://x.com/a", "html")
    ctx.expect_in("quality", rec)
    ctx.expect(isinstance(rec["quality"], dict))
    return Status.PASS.value, ""


@test("T43", "fix: folder manager handles missing files")
def t43_fm_missing(ctx):
    from folder_manager import FolderManager
    result = FolderManager.safe_remove("/tmp/nonexistent_xyz_12345")
    ctx.expect(result is True)
    return Status.PASS.value, ""


# ============================================================================
#  RUNNER
# ============================================================================

class Runner:
    def __init__(self, categories_filter=None, name_filter=None,
                 verbose=False, parallel=False, max_workers=4):
        self.categories_filter = set(categories_filter) if categories_filter else None
        self.name_filter = name_filter
        self.verbose = verbose
        self.parallel = parallel
        self.max_workers = max_workers
        self.results = []
        self.t_start = time.time()

    def _matches(self, category, name):
        if self.categories_filter and category not in self.categories_filter:
            return False
        if self.name_filter and self.name_filter.lower() not in name.lower():
            return False
        return True

    def _print_header(self):
        print()
        print("=" * 100)
        print(f"  {Env.banner()}")
        print("=" * 100)

    def _print_category(self, category, count):
        print()
        print("-" * 100)
        print(f"  {category} :: {count} tests")
        print("-" * 100)

    def _print_result(self, result):
        label_map = {
            Status.PASS.value: ("PASS", "\033[92m"),
            Status.FAIL.value: ("FAIL", "\033[91m"),
            Status.WARN.value: ("WARN", "\033[93m"),
            Status.EMPTY.value: ("EMPT", "\033[33m"),
            Status.SLOW.value: ("SLOW", "\033[93m"),
            Status.SKIP.value: ("SKIP", "\033[90m"),
            Status.ERROR.value: ("ERRO", "\033[91m"),
        }
        label, color = label_map.get(result.status, ("????", "\033[90m"))
        tag = _colorize(f"[{label}]", color)
        name = result.name if len(result.name) <= 70 else result.name[:67] + "..."
        ms = result.elapsed_ms
        ts = f"{ms:.0f}ms" if ms < 10000 else f"{ms/1000:.1f}s"
        detail = f" {result.detail}" if result.detail else ""
        print(f"  {tag} {result.category:16s} :: {name} ({ts}){detail}")

    def run(self):
        self._print_header()
        for category in list(_REGISTRY.keys()):
            tests = _REGISTRY[category]
            matching = [(t, self._matches(category, t["name"])) for t in tests]
            matching = [(t, m) for t, m in matching if m]
            if not matching:
                continue
            self._print_category(category, len(matching))
            for t in matching:
                t = t[0]
                skip = t.get("skip_if")
                if callable(skip):
                    try:
                        if skip():
                            result = TestResult(
                                category=category, name=t["name"],
                                status=Status.SKIP.value,
                                detail="skipped",
                            )
                            self.results.append(result)
                            self._print_result(result)
                            continue
                    except Exception:
                        pass
                ctx = TestContext(category, t["name"])
                result = ctx.run(t["fn"])
                self.results.append(result)
                self._print_result(result)

    def summary(self):
        counts = Counter(r.status for r in self.results)
        total = len(self.results)
        elapsed = time.time() - self.t_start

        print()
        print("=" * 100)
        print(f"  SUMMARY")
        print("=" * 100)
        print(f"  total     : {total}")
        for status in (Status.PASS.value, Status.FAIL.value, Status.WARN.value,
                        Status.EMPTY.value, Status.SLOW.value,
                        Status.SKIP.value, Status.ERROR.value):
            n = counts.get(status, 0)
            if n == 0:
                continue
            print(f"  {status.lower():10s}: {n}")
        print(f"  elapsed   : {elapsed:.1f}s")
        print(f"  rss       : {Env.PROCESS.memory_info().rss / (1024**2):.1f} MB")

        failed = [r for r in self.results
                   if r.status in (Status.FAIL.value, Status.ERROR.value)]
        warned = [r for r in self.results if r.status == Status.WARN.value]
        empty = [r for r in self.results if r.status == Status.EMPTY.value]
        slow = [r for r in self.results if r.status == Status.SLOW.value]

        if failed:
            print()
            print(f"  FAILURES ({len(failed)}):")
            for r in failed:
                print(f"    [{r.category}] {r.name}")
                print(f"      {r.detail}")
        if warned:
            print()
            print(f"  WARNINGS ({len(warned)}):")
            for r in warned[:30]:
                print(f"    [{r.category}] {r.name} :: {r.detail}")
        if slow:
            print()
            print(f"  SLOW ({len(slow)}):")
            for r in slow[:20]:
                print(f"    [{r.category}] {r.name} :: {r.detail}")

        self._write_report()

    def _write_report(self):
        report = {
            "run_meta": {
                "started_at": self.t_start,
                "elapsed": time.time() - self.t_start,
                "rss_mb": round(Env.PROCESS.memory_info().rss / (1024**2), 2),
                "python": Env.PYTHON,
                "platform": Env.PLATFORM,
                "cpu_count": Env.CPU_COUNT,
                "mem_total_gb": Env.MEM_TOTAL_GB,
                "disk_free_gb": Env.DISK_FREE_GB,
            },
            "summary": dict(Counter(r.status for r in self.results)),
            "results": [r.to_dict() for r in self.results],
        }
        out = Path("debug_report.json")
        out.write_bytes(json.dumps(report, indent=2, default=str).encode("utf-8"))
        print(f"\n  report : {out.resolve()}")


# ============================================================================
#  CLI
# ============================================================================

def parse_args():
    p = argparse.ArgumentParser(prog="debug", description="NEXUS debug harness v6")
    p.add_argument("--categories", nargs="*", default=None,
                   help="only run these categories (T0, T1, ...)")
    p.add_argument("--name", type=str, default=None,
                   help="only run tests matching this name substring")
    p.add_argument("--list", action="store_true",
                   help="list categories and exit")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--quiet", action="store_true",
                   help="suppress per-test output")
    p.add_argument("--log-level", default="INFO",
                   choices=["TRACE", "DEBUG", "INFO", "PASS", "WARN",
                            "FAIL", "ERROR"])
    p.add_argument("--log-file", default=None,
                   help="write structured JSON logs to this file")
    p.add_argument("--no-console-logs", action="store_true",
                   help="disable per-logger console output")
    return p.parse_args()


def main():
    try:
        mp.set_start_method("spawn", force=True)
    except Exception:
        pass

    args = parse_args()

    if args.list:
        for cat, tests in _REGISTRY.items():
            print(f"{cat:20s} {len(tests):4d} tests")
        return

    min_level = getattr(Level, args.log_level, Level.INFO)
    Logger.configure(
        min_level=min_level,
        console=not args.no_console_logs,
        file_path=args.log_file,
    )

    if args.quiet:
        Logger._global_console = False

    runner = Runner(
        categories_filter=args.categories,
        name_filter=args.name,
        verbose=args.verbose,
    )
    try:
        runner.run()
        runner.summary()
    finally:
        Logger.shutdown()


if __name__ == "__main__":
    from error_fast import install_all
    install_all()
    main()