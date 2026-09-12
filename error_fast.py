import os
import re
import sys
import time
import types
import asyncio
import logging
import warnings
import threading
import contextlib
import traceback
import multiprocessing as mp
from collections import defaultdict, Counter, deque, OrderedDict
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Optional, Iterable

from folder_manager import FolderManager, _atomic_write


# ============================================================================
#  ERROR KINDS
# ============================================================================

class Kind(str, Enum):
    LOOP_CLOSED = "loop_closed"
    CFFI_TIMER = "cffi_timer"
    ASYNC_CANCELLED = "async_cancelled"
    KEYBOARD_INTERRUPT = "keyboard_interrupt"
    TIMEOUT = "timeout"
    CONNECTION = "connection"
    SSL_TLS = "ssl_tls"
    DNS = "dns"
    HTTP_4XX = "http_4xx"
    HTTP_5XX = "http_5xx"
    RATE_LIMIT = "rate_limit"
    PARSE = "parse"
    DECODE = "decode"
    IMPORT = "import"
    FILE_IO = "file_io"
    PERMISSION = "permission"
    DISK = "disk"
    MEMORY = "memory"
    DEPENDENCY = "dependency"
    UNKNOWN = "unknown"


class Recovery(str, Enum):
    IGNORE = "ignore"
    RETRY = "retry"
    RETRY_LOOP = "retry_loop"
    FALLBACK = "fallback"
    ESCALATE = "escalate"
    ABORT = "abort"


# ============================================================================
#  CLASSIFICATION PATTERNS
# ============================================================================

@dataclass
class Pattern:
    regex: re.Pattern
    kind: Kind
    recovery: Recovery
    description: str = ""


_PATTERNS: list[Pattern] = []


def _compile(pattern: str, kind: Kind, recovery: Recovery, desc: str = ""):
    _PATTERNS.append(Pattern(re.compile(pattern, re.IGNORECASE),
                              kind, recovery, desc))


_compile(r"event loop is closed",
          Kind.LOOP_CLOSED, Recovery.IGNORE,
          "asyncio loop closed during callbacks")
_compile(r"exception ignored from cffi callback",
          Kind.CFFI_TIMER, Recovery.IGNORE,
          "curl_cffi timer fired after loop closed")
_compile(r"cancellederror|task was cancelled",
          Kind.ASYNC_CANCELLED, Recovery.RETRY_LOOP,
          "async task cancelled by loop shutdown")
_compile(r"keyboardinterrupt",
          Kind.KEYBOARD_INTERRUPT, Recovery.ABORT,
          "user interrupt")
_compile(r"timed? ?out|timeout error|read timeout|connect timeout",
          Kind.TIMEOUT, Recovery.RETRY,
          "network timeout")
_compile(r"connection (?:reset|refused|aborted|closed)|"
          r"remote end closed|connectionerror",
          Kind.CONNECTION, Recovery.RETRY,
          "connection failure")
_compile(r"ssl|tls|certificate|cert verify",
          Kind.SSL_TLS, Recovery.RETRY,
          "tls handshake failure")
_compile(r"name or service not known|nodename nor servname|"
          r"getaddrinfo|dns",
          Kind.DNS, Recovery.RETRY,
          "dns resolution failure")
_compile(r"status[^\d]*(4\d\d)|http 4\d\d|not found|forbidden|unauthorized",
          Kind.HTTP_4XX, Recovery.FALLBACK,
          "client http error")
_compile(r"status[^\d]*(5\d\d)|http 5\d\d|internal server|bad gateway|"
          r"service unavailable|gateway timeout",
          Kind.HTTP_5XX, Recovery.RETRY,
          "server http error")
_compile(r"429|too many requests|rate limit",
          Kind.RATE_LIMIT, Recovery.RETRY,
          "rate limited")
_compile(r"jsondecode|orjson|expecting value|invalid json",
          Kind.PARSE, Recovery.FALLBACK,
          "json parse error")
_compile(r"lxml|selectolax|parse|xml\.etree|htmlparser",
          Kind.PARSE, Recovery.FALLBACK,
          "html/xml parse error")
_compile(r"unicodedecode|unicodeencode|codec can't|encoding",
          Kind.DECODE, Recovery.FALLBACK,
          "encoding error")
_compile(r"importerror|modulenotfound|cannot import",
          Kind.IMPORT, Recovery.ESCALATE,
          "module import failure")
_compile(r"filenotfound|no such file|directory not empty",
          Kind.FILE_IO, Recovery.IGNORE,
          "file not found")
_compile(r"permission denied|access denied|permissionerror",
          Kind.PERMISSION, Recovery.ESCALATE,
          "permission failure")
_compile(r"disk full|no space left",
          Kind.DISK, Recovery.ESCALATE,
          "disk full")
_compile(r"memoryerror|out of memory|cannot allocate",
          Kind.MEMORY, Recovery.ESCALATE,
          "out of memory")
_compile(r"no module named|version mismatch|requirement",
          Kind.DEPENDENCY, Recovery.ESCALATE,
          "missing or incompatible dependency")


def classify(exc: BaseException) -> tuple[Kind, Recovery, str]:
    """Fast classification: type first, then message."""
    if isinstance(exc, KeyboardInterrupt):
        return Kind.KEYBOARD_INTERRUPT, Recovery.ABORT, "interrupt"
    if isinstance(exc, asyncio.CancelledError):
        return Kind.ASYNC_CANCELLED, Recovery.RETRY_LOOP, "cancelled"
    if isinstance(exc, asyncio.TimeoutError):
        return Kind.TIMEOUT, Recovery.RETRY, "async timeout"
    if isinstance(exc, TimeoutError):
        return Kind.TIMEOUT, Recovery.RETRY, "timeout"
    if isinstance(exc, PermissionError):
        return Kind.PERMISSION, Recovery.ESCALATE, "permission"
    if isinstance(exc, FileNotFoundError):
        return Kind.FILE_IO, Recovery.IGNORE, "not found"
    if isinstance(exc, (ConnectionError, ConnectionResetError,
                         ConnectionRefusedError, ConnectionAbortedError)):
        return Kind.CONNECTION, Recovery.RETRY, "connection"
    if isinstance(exc, MemoryError):
        return Kind.MEMORY, Recovery.ESCALATE, "memory"
    if isinstance(exc, ImportError):
        return Kind.IMPORT, Recovery.ESCALATE, "import"
    if isinstance(exc, UnicodeError):
        return Kind.DECODE, Recovery.FALLBACK, "encoding"

    msg = str(exc)[:500]
    for pat in _PATTERNS:
        if pat.regex.search(msg):
            return pat.kind, pat.recovery, pat.description
    return Kind.UNKNOWN, Recovery.ESCALATE, ""


# ============================================================================
#  ERROR EVENT
# ============================================================================

@dataclass
class Event:
    ts: float
    kind: Kind
    recovery: Recovery
    exception_type: str
    message: str
    traceback_hash: str
    count: int = 1

    def to_dict(self):
        d = asdict(self)
        d["kind"] = self.kind.value
        d["recovery"] = self.recovery.value
        return d


# ============================================================================
#  NOISE SUPPRESSOR — handles the cffi timer flood
# ============================================================================

class NoiseSuppressor:
    """Silences the curl_cffi timer callback flood that occurs when
    asyncio.run() closes the loop before cffi's pending timers fire.
    The suppression is at the interpreter level, not per-call."""

    NOISE_FRAGMENTS = (
        "Exception ignored from cffi callback",
        "Event loop is closed",
        "async_curl._timer = async_curl.loop.call_later",
        "_check_closed",
    )

    _installed = False
    _suppressed = 0
    _lock = threading.Lock()

    @classmethod
    def install(cls):
        if cls._installed:
            return
        cls._installed = True
        try:
            sys.unraisablehook = cls._unraisable_hook
        except Exception:
            pass
        try:
            loop = asyncio.get_event_loop_policy().get_event_loop()
            loop.set_exception_handler(cls._loop_exception_handler)
        except Exception:
            pass

    @classmethod
    def _is_noise(cls, text):
        for frag in cls.NOISE_FRAGMENTS:
            if frag in text:
                return True
        return False

    @classmethod
    def _unraisable_hook(cls, unraisable):
        try:
            msg = str(unraisable.exc_value) if unraisable.exc_value else ""
            tb_text = ""
            if unraisable.exc_traceback:
                tb_text = "".join(traceback.format_tb(
                    unraisable.exc_traceback
                ))
            combined = msg + " " + tb_text + " " + str(unraisable.object)
            if cls._is_noise(combined):
                with cls._lock:
                    cls._suppressed += 1
                return
        except Exception:
            pass
        try:
            sys.__unraisablehook__(unraisable)
        except Exception:
            pass

    @classmethod
    def _loop_exception_handler(cls, loop, context):
        try:
            msg = context.get("message", "")
            exc = context.get("exception")
            exc_msg = str(exc) if exc else ""
            if cls._is_noise(msg + " " + exc_msg):
                with cls._lock:
                    cls._suppressed += 1
                return
        except Exception:
            pass

    @classmethod
    def stats(cls):
        with cls._lock:
            return {"installed": cls._installed,
                    "suppressed": cls._suppressed}


# ============================================================================
#  PERSISTENT EVENT LOOP — fixes the closed-loop problem
# ============================================================================

class LoopManager:
    """Maintains one long-lived asyncio event loop per process. Replaces
    asyncio.run() so curl_cffi's timers can fire safely between runs."""

    _loop: Optional[asyncio.AbstractEventLoop] = None
    _thread: Optional[threading.Thread] = None
    _lock = threading.Lock()
    _running = threading.Event()
    _runs = 0

    @classmethod
    def get_loop(cls) -> asyncio.AbstractEventLoop:
        with cls._lock:
            if cls._loop is None or cls._loop.is_closed():
                cls._loop = asyncio.new_event_loop()
                cls._loop.set_exception_handler(
                    NoiseSuppressor._loop_exception_handler
                )
            return cls._loop

    @classmethod
    def run(cls, coro, timeout=None):
        loop = cls.get_loop()
        try:
            if not loop.is_running():
                if timeout is not None:
                    return loop.run_until_complete(
                        asyncio.wait_for(coro, timeout=timeout)
                    )
                return loop.run_until_complete(coro)
        except (asyncio.CancelledError, KeyboardInterrupt):
            cls._drain(loop)
            raise
        except RuntimeError as e:
            if "event loop is closed" in str(e).lower():
                with cls._lock:
                    cls._loop = None
                loop = cls.get_loop()
                if timeout is not None:
                    return loop.run_until_complete(
                        asyncio.wait_for(coro, timeout=timeout)
                    )
                return loop.run_until_complete(coro)
            raise
        finally:
            with cls._lock:
                cls._runs += 1

    @classmethod
    def _drain(cls, loop):
        try:
            pending = [t for t in asyncio.all_tasks(loop)
                        if not t.done()]
            for t in pending:
                t.cancel()
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
        except Exception:
            pass

    @classmethod
    def close(cls):
        with cls._lock:
            if cls._loop is not None and not cls._loop.is_closed():
                try:
                    cls._drain(cls._loop)
                    cls._loop.close()
                except Exception:
                    pass
                cls._loop = None

    @classmethod
    def stats(cls):
        loop = cls._loop
        return {
            "runs": cls._runs,
            "has_loop": loop is not None,
            "loop_closed": loop.is_closed() if loop else None,
            "loop_running": loop.is_running() if loop else None,
        }


# ============================================================================
#  EVENT LOOP PATCHING
# ============================================================================

def patch_asyncio():
    """Replace asyncio.run with LoopManager.run in a safe, reversible way."""
    if getattr(asyncio, "_error_fast_patched", False):
        return False
    original_run = asyncio.run

    def _patched_run(coro, **kwargs):
        if not isinstance(coro, type(_patched_run)):
            try:
                loop = LoopManager.get_loop()
                if loop.is_running():
                    return original_run(coro, **kwargs)
                return LoopManager.run(coro)
            except Exception:
                pass
        try:
            return original_run(coro, **kwargs)
        except RuntimeError as e:
            if "event loop is closed" in str(e).lower():
                LoopManager.close()
                try:
                    return original_run(coro, **kwargs)
                except Exception:
                    raise
            raise

    asyncio.run = _patched_run
    asyncio._error_fast_patched = True
    asyncio._original_run = original_run
    return True


# ============================================================================
#  FAST DECORATORS
# ============================================================================

def fast_catch(default=None, kinds=None, reraise=False, log=False):
    """Wrap a function. Classified retries happen per Kind.RETRY/RETRY_LOOP.
    Ignored kinds return `default`. Escalated kinds either reraise or return default."""
    def decorator(fn):
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except BaseException as e:
                kind, recovery, desc = classify(e)
                ErrorFast.record(e, kind, recovery)
                if kinds is not None and kind not in kinds:
                    raise
                if recovery == Recovery.IGNORE:
                    return default
                if recovery in (Recovery.RETRY, Recovery.RETRY_LOOP):
                    for attempt in range(2):
                        try:
                            return fn(*args, **kwargs)
                        except BaseException:
                            continue
                if reraise:
                    raise
                return default
        wrapper.__name__ = fn.__name__
        wrapper.__wrapped__ = fn
        return wrapper
    return decorator


def fast_async_catch(default=None, kinds=None, reraise=False):
    def decorator(fn):
        async def wrapper(*args, **kwargs):
            try:
                return await fn(*args, **kwargs)
            except BaseException as e:
                kind, recovery, desc = classify(e)
                ErrorFast.record(e, kind, recovery)
                if kinds is not None and kind not in kinds:
                    raise
                if recovery == Recovery.IGNORE:
                    return default
                if recovery == Recovery.RETRY_LOOP:
                    return default
                if recovery == Recovery.RETRY:
                    try:
                        return await fn(*args, **kwargs)
                    except BaseException:
                        pass
                if reraise:
                    raise
                return default
        wrapper.__name__ = fn.__name__
        wrapper.__wrapped__ = fn
        return wrapper
    return decorator


# ============================================================================
#  ERROR FAST — the main registry
# ============================================================================

class ErrorFast:
    _lock = threading.Lock()
    _events: deque = deque(maxlen=5000)
    _counters: Counter = Counter()
    _by_kind: Counter = Counter()
    _by_recovery: Counter = Counter()
    _by_type: Counter = Counter()
    _tb_seen: set = set()
    _hooks: dict = defaultdict(list)
    _initialized = False

    @classmethod
    def init(cls, install_noise_suppressor=True, patch_loop=True,
             patch_asyncio_run=False, install_global_hook=False):
        if cls._initialized:
            return
        cls._initialized = True
        if install_noise_suppressor:
            NoiseSuppressor.install()
        if patch_loop:
            LoopManager.get_loop()
        if patch_asyncio_run:
            patch_asyncio()
        if install_global_hook:
            sys.excepthook = cls._global_excepthook

    @classmethod
    def register(cls, kind, hook: Callable[[BaseException, Kind, Recovery], None]):
        with cls._lock:
            cls._hooks[kind].append(hook)

    @classmethod
    def record(cls, exc: BaseException, kind: Kind = None, recovery: Recovery = None):
        if kind is None:
            kind, recovery, _ = classify(exc)
        tb_hash = _hash_tb(exc)
        with cls._lock:
            cls._counters["total"] += 1
            cls._by_kind[kind] += 1
            cls._by_recovery[recovery] += 1
            cls._by_type[type(exc).__name__] += 1
            is_new = tb_hash not in cls._tb_seen
            if is_new:
                cls._tb_seen.add(tb_hash)
            cls._events.append(Event(
                ts=time.time(),
                kind=kind,
                recovery=recovery,
                exception_type=type(exc).__name__,
                message=str(exc)[:300],
                traceback_hash=tb_hash,
                count=1,
            ))
            hooks = list(cls._hooks.get(kind, ()))
        for hook in hooks:
            try:
                hook(exc, kind, recovery)
            except Exception:
                pass
        return kind, recovery, is_new

    @classmethod
    def _global_excepthook(cls, exc_type, exc_value, tb):
        if exc_type is KeyboardInterrupt:
            sys.__excepthook__(exc_type, exc_value, tb)
            return
        cls.record(exc_value)
        kind, recovery, desc = classify(exc_value)
        if kind == Kind.CFFI_TIMER or kind == Kind.LOOP_CLOSED:
            return
        sys.__excepthook__(exc_type, exc_value, tb)

    @classmethod
    def stats(cls):
        with cls._lock:
            return {
                "total": cls._counters["total"],
                "by_kind": dict(cls._by_kind),
                "by_recovery": dict(cls._by_recovery),
                "top_types": cls._by_type.most_common(10),
                "unique_tracebacks": len(cls._tb_seen),
                "recent": [e.to_dict() for e in list(cls._events)[-20:]],
            }

    @classmethod
    def save(cls, path=None):
        path = path or str(FolderManager.CACHE / "error_fast.json")
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            data = {
                "saved_at": time.time(),
                "stats": cls.stats(),
                "suppressor": NoiseSuppressor.stats(),
                "loop": LoopManager.stats(),
            }
            _atomic_write(path, _json_bytes(data))
            return path
        except Exception:
            return None


def _hash_tb(exc):
    tb = exc.__traceback__
    parts = []
    while tb is not None:
        parts.append(f"{tb.tb_frame.f_code.co_filename}:{tb.tb_lineno}")
        tb = tb.tb_next
    sig = f"{type(exc).__name__}:{'|'.join(parts[-6:])}"
    import hashlib
    return hashlib.blake2b(sig.encode(), digest_size=8).hexdigest()


def _json_bytes(obj):
    import json
    return json.dumps(obj, default=str, indent=2).encode("utf-8")


from pathlib import Path


# ============================================================================
#  CONTEXT MANAGERS
# ============================================================================

@contextlib.contextmanager
def swallow(*kinds, default=None):
    try:
        yield
    except BaseException as e:
        kind, recovery, _ = classify(e)
        ErrorFast.record(e, kind, recovery)
        if kinds and kind not in kinds:
            raise
        if kind in (Kind.KEYBOARD_INTERRUPT, Kind.MEMORY, Kind.DISK):
            raise


@contextlib.contextmanager
def retry(times=3, delay=0.5, backoff=2.0, kinds=None):
    last = None
    for attempt in range(times):
        try:
            yield attempt
            return
        except BaseException as e:
            last = e
            kind, recovery, _ = classify(e)
            ErrorFast.record(e, kind, recovery)
            if kinds is not None and kind not in kinds:
                raise
            if recovery in (Recovery.IGNORE, Recovery.ABORT):
                raise
            if attempt == times - 1:
                raise
            time.sleep(delay * (backoff ** attempt))
    if last is not None:
        raise last


# ============================================================================
#  SAFE WRAPPERS FOR KNOWN NOISY CALLS
# ============================================================================

def safe_asyncio_run(coro, timeout=None):
    """Drop-in for asyncio.run that never leaves a closed loop behind.
    Safe for curl_cffi AsyncSession usage."""
    try:
        return LoopManager.run(coro, timeout=timeout)
    except KeyboardInterrupt:
        raise
    except RuntimeError as e:
        if "event loop is closed" in str(e).lower():
            LoopManager.close()
            return LoopManager.run(coro, timeout=timeout)
        raise


def safe_async_session_close(session):
    """Cancel and close an AsyncSession without triggering timer noise."""
    if session is None:
        return
    loop = None
    try:
        loop = LoopManager.get_loop()
    except Exception:
        pass
    if loop is None or loop.is_closed():
        return
    try:
        if not loop.is_running():
            loop.run_until_complete(session.close())
    except Exception:
        pass


# ============================================================================
#  DIAGNOSTIC
# ============================================================================

def report() -> dict:
    return {
        "noise_suppressor": NoiseSuppressor.stats(),
        "loop_manager": LoopManager.stats(),
        "error_fast": ErrorFast.stats(),
    }


def print_report():
    import json
    print(json.dumps(report(), indent=2, default=str))


def install_all():
    ErrorFast.init(
        install_noise_suppressor=True,
        patch_loop=True,
        patch_asyncio_run=False,
        install_global_hook=False,
    )


# ============================================================================
#  CLI
# ============================================================================

def _cli():
    import argparse
    p = argparse.ArgumentParser(prog="error_fast",
                                 description="fast error handling + noise suppression")
    p.add_argument("--report", action="store_true")
    p.add_argument("--save", action="store_true")
    p.add_argument("--test", action="store_true")
    p.add_argument("--classify", type=str, default=None,
                   help="classify an exception message")
    args = p.parse_args()

    install_all()

    if args.classify:
        import json
        kind, recovery, desc = classify(RuntimeError(args.classify))
        print(json.dumps({
            "message": args.classify,
            "kind": kind.value,
            "recovery": recovery.value,
            "description": desc,
        }, indent=2))
        return

    if args.test:
        print("[test] simulating the cffi timer noise...")
        try:
            raise RuntimeError("Event loop is closed")
        except RuntimeError as e:
            kind, recovery, _ = classify(e)
            ErrorFast.record(e, kind, recovery)
            assert kind == Kind.LOOP_CLOSED

        try:
            raise RuntimeError("Exception ignored from cffi callback")
        except RuntimeError as e:
            kind, recovery, _ = classify(e)
            ErrorFast.record(e, kind, recovery)
            assert kind == Kind.CFFI_TIMER

        try:
            raise asyncio.CancelledError()
        except asyncio.CancelledError as e:
            kind, recovery, _ = classify(e)
            ErrorFast.record(e, kind, recovery)
            assert kind == Kind.ASYNC_CANCELLED

        async def _test_coro():
            await asyncio.sleep(0.01)
            return 42

        result = safe_asyncio_run(_test_coro())
        assert result == 42
        print("[test] safe_asyncio_run returned", result)

        @fast_catch(default=None)
        def _raising():
            raise RuntimeError("Event loop is closed")
        assert _raising() is None
        print("[test] fast_catch swallowed loop-closed error")

        print("[test] all checks passed")
        print_report()
        return

    if args.save:
        path = ErrorFast.save()
        print(f"saved to {path}")
        return

    print_report()


if __name__ == "__main__":
    _cli()