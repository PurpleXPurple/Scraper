import os
import sys
import time
import json
import shutil
import stat
import atexit
import logging
import threading
import contextlib
import traceback
from pathlib import Path
from enum import Enum


_LOG = logging.getLogger("folder_manager")
_IS_WIN = os.name == "nt"
_PID = os.getpid()


# ============================================================================
#  ERROR TAXONOMY — 15 CATEGORIES
# ============================================================================

class ErrorCategory(str, Enum):
    GENERIC = "generic"
    BOOTSTRAP = "bootstrap"
    DISK = "disk"
    PERMISSION = "permission"
    LOCKED = "locked"
    PATH = "path"
    SYMLINK = "symlink"
    CORRUPT = "corrupt"
    CONCURRENT = "concurrent"
    CASE = "case"
    HANDLE = "handle"
    ENCODING = "encoding"
    STATE = "state"
    IO = "io"
    UNKNOWN = "unknown"


class FolderError(Exception):
    category = ErrorCategory.GENERIC
    recoverable = True

    def __init__(self, msg, *, path=None, cause=None, context=None):
        super().__init__(msg)
        self.path = path
        self.cause = cause
        self.context = context or {}

    def to_dict(self):
        return {
            "category": self.category.value,
            "message": str(self),
            "path": str(self.path) if self.path else None,
            "cause": repr(self.cause) if self.cause else None,
            "recoverable": self.recoverable,
            "context": self.context,
        }


class BootstrapError(FolderError):
    category = ErrorCategory.BOOTSTRAP
    recoverable = False


class DiskSpaceError(FolderError):
    category = ErrorCategory.DISK
    recoverable = True


class NotWritableError(FolderError):
    category = ErrorCategory.PERMISSION
    recoverable = False


class LockedFileError(FolderError):
    category = ErrorCategory.LOCKED
    recoverable = True


class PathTooLongError(FolderError):
    category = ErrorCategory.PATH
    recoverable = True


class SymlinkLoopError(FolderError):
    category = ErrorCategory.SYMLINK
    recoverable = True


class CorruptedStateError(FolderError):
    category = ErrorCategory.CORRUPT
    recoverable = True


class ConcurrentAccessError(FolderError):
    category = ErrorCategory.CONCURRENT
    recoverable = True


class CaseCollisionError(FolderError):
    category = ErrorCategory.CASE
    recoverable = False


class HandleExhaustedError(FolderError):
    category = ErrorCategory.HANDLE
    recoverable = True


class EncodingMismatchError(FolderError):
    category = ErrorCategory.ENCODING
    recoverable = True


class StateMismatchError(FolderError):
    category = ErrorCategory.STATE
    recoverable = True


class IOFailureError(FolderError):
    category = ErrorCategory.IO
    recoverable = True


# ============================================================================
#  ERROR CLASSIFIER — maps OS exceptions to categories
# ============================================================================

class ErrorClassifier:
    @staticmethod
    def classify(exc):
        if isinstance(exc, FolderError):
            return exc
        name = type(exc).__name__
        errno = getattr(exc, "errno", None)
        winerror = getattr(exc, "winerror", None)

        if isinstance(exc, FileNotFoundError):
            return None

        if isinstance(exc, PermissionError):
            return LockedFileError(
                f"permission denied: {exc}", cause=exc,
                context={"winerror": winerror, "errno": errno},
            )
        if isinstance(exc, FileExistsError):
            return ConcurrentAccessError(
                f"file already exists: {exc}", cause=exc,
            )
        if isinstance(exc, IsADirectoryError):
            return IOFailureError(
                f"expected file, got directory: {exc}", cause=exc,
            )
        if isinstance(exc, NotADirectoryError):
            return IOFailureError(
                f"expected directory, got file: {exc}", cause=exc,
            )
        if isinstance(exc, OSError):
            if errno == 28:
                return DiskSpaceError(f"disk full: {exc}", cause=exc)
            if errno == 36:
                return PathTooLongError(f"path too long: {exc}", cause=exc)
            if errno == 40:
                return SymlinkLoopError(f"symlink loop: {exc}", cause=exc)
            if errno == 24:
                return HandleExhaustedError(f"too many open files: {exc}", cause=exc)
            if winerror == 206:
                return PathTooLongError(f"windows path too long: {exc}", cause=exc)
            if winerror in (32, 33):
                return LockedFileError(f"file in use: {exc}", cause=exc)
            if winerror in (5,):
                return NotWritableError(f"access denied: {exc}", cause=exc)
            if winerror in (112,):
                return DiskSpaceError(f"disk full: {exc}", cause=exc)
            return IOFailureError(f"os error: {exc}", cause=exc)
        if isinstance(exc, (UnicodeError, UnicodeDecodeError, UnicodeEncodeError)):
            return EncodingMismatchError(f"encoding error: {exc}", cause=exc)
        if isinstance(exc, (json.JSONDecodeError,)):
            return CorruptedStateError(f"json decode: {exc}", cause=exc)

        return FolderError(f"unclassified: {name}: {exc}", cause=exc,
                            context={"type": name})


# ============================================================================
#  ERROR HANDLER — retries, backoff, category dispatch
# ============================================================================

class ErrorHandler:
    RETRYABLE = frozenset({
        ErrorCategory.LOCKED,
        ErrorCategory.CONCURRENT,
        ErrorCategory.HANDLE,
    })
    FATAL = frozenset({
        ErrorCategory.PERMISSION,
        ErrorCategory.BOOTSTRAP,
        ErrorCategory.CASE,
    })

    def __init__(self, max_retries=4, base_delay=0.15, backoff=2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.backoff = backoff
        self._hooks = {}

    def register(self, category, hook):
        self._hooks.setdefault(category, []).append(hook)

    def _fire(self, category, error, attempt):
        for hook in self._hooks.get(category, ()):
            try:
                hook(error, attempt)
            except Exception:
                pass

    def run(self, fn, *args, category_hint=None, **kwargs):
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return fn(*args, **kwargs)
            except FolderError as e:
                last_error = e
                self._fire(e.category, e, attempt)
                if e.category in self.FATAL:
                    raise
                if e.category in self.RETRYABLE and attempt < self.max_retries - 1:
                    time.sleep(self.base_delay * (self.backoff ** attempt))
                    continue
                raise
            except FileNotFoundError:
                raise
            except Exception as e:
                classified = ErrorClassifier.classify(e)
                if classified is None:
                    raise
                last_error = classified
                self._fire(classified.category, classified, attempt)
                if classified.category in self.FATAL:
                    raise classified from e
                if classified.category in self.RETRYABLE and attempt < self.max_retries - 1:
                    time.sleep(self.base_delay * (self.backoff ** attempt))
                    continue
                raise classified from e
        if last_error is not None:
            raise last_error
        raise FolderError("run loop exited without result")


_HANDLER = ErrorHandler()


# ============================================================================
#  PATH HELPERS — Windows-safe, long-path-aware
# ============================================================================

def _long_path(p):
    s = str(Path(p).absolute())
    if not _IS_WIN:
        return s
    if s.startswith("\\\\?\\"):
        return s
    if s.startswith("\\\\"):
        return "\\\\?\\UNC\\" + s[2:]
    if len(s) >= 240:
        return "\\\\?\\" + s
    return s


def _clear_readonly(path):
    try:
        mode = Path(path).stat().st_mode
        Path(path).chmod(mode | stat.S_IWRITE | stat.S_IREAD)
    except Exception:
        pass


def _on_rmtree_error(func, path, exc_info):
    try:
        _clear_readonly(path)
        func(path)
    except Exception:
        pass


def _probe_name(tier_path):
    return tier_path / f".write_probe.{_PID}"


def _atomic_write(path, data, fsync=True):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + f".tmp.{_PID}")
    try:
        with open(_long_path(tmp), "wb") as f:
            f.write(data)
            f.flush()
            if fsync:
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass
        os.replace(_long_path(tmp), _long_path(p))
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except Exception:
                pass


def _safe_size(path):
    try:
        p = Path(path)
        if not p.exists():
            return 0
        if p.is_file():
            return p.stat().st_size
        total = 0
        for root, dirs, files in os.walk(_long_path(p)):
            for name in files:
                try:
                    total += (Path(root) / name).stat().st_size
                except Exception:
                    pass
        return total
    except Exception:
        return 0


def _case_collision_check(directory):
    try:
        seen = {}
        for child in Path(directory).iterdir():
            low = child.name.lower()
            if low in seen and seen[low] != child.name:
                return (seen[low], child.name)
            seen[low] = child.name
        return None
    except Exception:
        return None


# ============================================================================
#  CROSS-PROCESS LOCK — atomic O_EXCL create on .lock file
# ============================================================================

class FileLock:
    def __init__(self, path, timeout=30.0, poll=0.1):
        self.path = Path(path)
        self.timeout = timeout
        self.poll = poll
        self._fd = None

    def acquire(self):
        start = time.monotonic()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                fd = os.open(_long_path(self.path),
                             os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(_PID).encode("ascii"))
                self._fd = fd
                return True
            except FileExistsError:
                try:
                    age = time.time() - self.path.stat().st_mtime
                except Exception:
                    age = 0
                if age > self.timeout * 4:
                    try:
                        self.path.unlink()
                    except Exception:
                        pass
                    continue
                if time.monotonic() - start > self.timeout:
                    return False
                time.sleep(self.poll)
            except OSError as e:
                classified = ErrorClassifier.classify(e)
                if classified is not None and classified.category in ErrorHandler.FATAL:
                    raise classified from e
                if time.monotonic() - start > self.timeout:
                    return False
                time.sleep(self.poll)

    def release(self):
        if self._fd is not None:
            try:
                os.close(self._fd)
            except Exception:
                pass
            self._fd = None
        try:
            if self.path.exists():
                self.path.unlink()
        except Exception:
            pass

    def __enter__(self):
        if not self.acquire():
            raise ConcurrentAccessError(
                f"could not acquire lock within {self.timeout}s",
                path=self.path,
            )
        return self

    def __exit__(self, *exc):
        self.release()
        return False


# ============================================================================
#  SELF-DIAGNOSTICS — 15 checks
# ============================================================================

class Diagnostics:
    def __init__(self, fm):
        self.fm = fm
        self.results = []

    def _add(self, name, ok, detail="", category=None):
        self.results.append({
            "name": name, "ok": bool(ok), "detail": detail,
            "category": category.value if category else None,
        })

    def _check_python_version(self):
        ok = sys.version_info >= (3, 9)
        self._add("python>=3.9", ok, f"{sys.version.split()[0]}")

    def _check_disk_space(self):
        free = self.fm.disk_free_gb()
        ok = free < 0 or free > 0.5
        self._add("disk_space", ok, f"{free:.2f} GB free",
                   ErrorCategory.DISK if not ok else None)

    def _check_writable(self):
        probe = self.fm.DATA / f".diag.{_PID}"
        try:
            probe.write_bytes(b"ok")
            probe.unlink()
            self._add("data_writable", True, str(self.fm.DATA))
        except Exception as e:
            self._add("data_writable", False, repr(e),
                       ErrorCategory.PERMISSION)

    def _check_long_paths(self):
        depth = 20
        parts = ["x" * 30] * depth
        test = self.fm.TMP.joinpath(*parts)
        try:
            test.mkdir(parents=True, exist_ok=True)
            probe = test / "probe.txt"
            probe.write_bytes(b"ok")
            probe.unlink()
            shutil.rmtree(self.fm.TMP / ("x" * 30), ignore_errors=True)
            self._add("long_paths", True, f"{len(str(test))} chars")
        except Exception as e:
            self._add("long_paths", False, repr(e), ErrorCategory.PATH)

    def _check_case_collision(self):
        for tier in self.fm.TIERS:
            d = self.fm.tier(tier)
            collision = _case_collision_check(d)
            if collision:
                self._add(f"case_collision[{tier}]", False,
                           f"{collision[0]} vs {collision[1]}",
                           ErrorCategory.CASE)
                return
        self._add("case_collision", True)

    def _check_symlinks(self):
        for tier in self.fm.TIERS:
            d = self.fm.tier(tier)
            try:
                for child in d.iterdir():
                    if child.is_symlink():
                        self._add(f"symlink[{tier}]", False, str(child),
                                   ErrorCategory.SYMLINK)
                        return
            except Exception:
                continue
        self._add("symlinks", True)

    def _check_json_state(self):
        candidates = [
            self.fm.CACHE / "domain_rates.json",
            self.fm.CACHE / "mos_budget.json",
            self.fm.CACHE / "mos_host_prefs.json",
        ]
        for path in candidates:
            if not path.exists():
                continue
            try:
                with open(_long_path(path), "rb") as f:
                    json.loads(f.read())
            except Exception as e:
                self._add(f"json_valid[{path.name}]", False, repr(e),
                           ErrorCategory.CORRUPT)
                return
        self._add("json_valid", True)

    def _check_sqlite(self):
        import sqlite3
        for name in ("dedup.sqlite", "mos_cache.sqlite", "extraction.sqlite"):
            path = self.fm.DB / name
            if not path.exists():
                continue
            try:
                conn = sqlite3.connect(str(path), timeout=5)
                conn.execute("PRAGMA integrity_check").fetchone()
                conn.close()
            except Exception as e:
                self._add(f"sqlite[{name}]", False, repr(e),
                           ErrorCategory.CORRUPT)
                return
        self._add("sqlite", True)

    def _check_handles(self):
        try:
            import psutil
            proc = psutil.Process(_PID)
            n = proc.num_fds() if hasattr(proc, "num_fds") else len(proc.open_files())
            ok = n < 1000
            self._add("open_handles", ok, f"{n} open", ErrorCategory.HANDLE if not ok else None)
        except Exception:
            self._add("open_handles", True, "skipped")

    def _check_probes(self):
        orphan = []
        for tier in self.fm.TIERS:
            d = self.fm.tier(tier)
            if not d.exists():
                continue
            for child in d.glob(".write_probe.*"):
                if not child.name.endswith(f".{_PID}"):
                    orphan.append(str(child))
        ok = not orphan
        self._add("orphan_probes", ok,
                   f"{len(orphan)} orphans" if orphan else "clean")

    def _check_bootstrap_sentinel(self):
        sentinel = self.fm.DATA / ".bootstrapped"
        ok = sentinel.exists()
        self._add("bootstrap_sentinel", ok, str(sentinel))

    def _check_locks(self):
        locks = list(self.fm.DATA.rglob("*.lock"))
        stale = []
        for lock in locks:
            try:
                age = time.time() - lock.stat().st_mtime
                if age > 300:
                    stale.append(str(lock))
            except Exception:
                pass
        self._add("stale_locks", not stale,
                   f"{len(stale)} stale" if stale else "clean")

    def _check_encoding(self):
        try:
            "test".encode("utf-8").decode("utf-8")
            self._add("encoding", True, sys.getfilesystemencoding())
        except Exception as e:
            self._add("encoding", False, repr(e), ErrorCategory.ENCODING)

    def _check_tier_sizes(self):
        try:
            report = self.fm.report()
            total = sum(e["size_kb"] for e in report["tiers"].values())
            self._add("tier_sizes", True, f"{total:.1f} KB total")
        except Exception as e:
            self._add("tier_sizes", False, repr(e), ErrorCategory.IO)

    def run(self):
        checks = [
            self._check_python_version,
            self._check_disk_space,
            self._check_writable,
            self._check_long_paths,
            self._check_case_collision,
            self._check_symlinks,
            self._check_json_state,
            self._check_sqlite,
            self._check_handles,
            self._check_probes,
            self._check_bootstrap_sentinel,
            self._check_locks,
            self._check_encoding,
            self._check_tier_sizes,
        ]
        for check in checks:
            try:
                check()
            except Exception as e:
                self._add(check.__name__, False, repr(e))
        return self.results

    def summary(self):
        ok = sum(1 for r in self.results if r["ok"])
        fail = len(self.results) - ok
        lines = [f"diagnostics: {ok} ok, {fail} failed"]
        for r in self.results:
            mark = "ok  " if r["ok"] else "FAIL"
            extra = f"  [{r['category']}]" if r["category"] else ""
            lines.append(f"  [{mark}] {r['name']:28s} {r['detail']}{extra}")
        return "\n".join(lines)


# ============================================================================
#  FOLDER MANAGER
# ============================================================================

class FolderManager:
    ROOT = Path(__file__).resolve().parent
    DATA = ROOT / ".data"

    STATE = DATA / "state"
    DB = DATA / "db"
    CACHE = DATA / "cache"
    LOGS = DATA / "logs"
    AGENT = DATA / "agent"
    OUTPUT = DATA / "output"
    SHARDS = OUTPUT / "shards"
    QUARANTINE = OUTPUT / "quarantine"
    COOKIES = CACHE / "cookies"
    TMP = DATA / "tmp"

    _ALL = (DATA, STATE, DB, CACHE, LOGS, AGENT, OUTPUT,
            SHARDS, QUARANTINE, COOKIES, TMP)

    TIERS = ("state", "db", "cache", "logs", "agent", "output",
             "shards", "quarantine", "cookies", "tmp")

    SENTINEL = DATA / ".bootstrapped"
    MIN_FREE_GB = 0.5

    _lock = threading.RLock()
    _bootstrapped = False
    _boot_lock = threading.Lock()
    _cleanup_registered = False

    # ----------------------------------------------------------------
    #  TIER RESOLUTION
    # ----------------------------------------------------------------

    @classmethod
    def tier(cls, name):
        if name not in cls.TIERS:
            raise FolderError(f"unknown tier: {name!r}",
                               context={"tier": name})
        return getattr(cls, name.upper())

    # ----------------------------------------------------------------
    #  BOOTSTRAP (idempotent, PID-aware, cross-process safe)
    # ----------------------------------------------------------------

    @classmethod
    def _register_atexit(cls):
        if cls._cleanup_registered:
            return
        try:
            atexit.register(cls._cleanup_probes)
            cls._cleanup_registered = True
        except Exception:
            pass

    @classmethod
    def _cleanup_probes(cls):
        for d in cls._ALL:
            try:
                for probe in d.glob(f".write_probe.{_PID}"):
                    try:
                        probe.unlink(missing_ok=True)
                    except Exception:
                        pass
                for diag in d.glob(f".diag.{_PID}"):
                    try:
                        diag.unlink(missing_ok=True)
                    except Exception:
                        pass
            except Exception:
                pass

    @classmethod
    def bootstrap(cls, force=False, min_free_gb=None):
        min_free_gb = min_free_gb if min_free_gb is not None else cls.MIN_FREE_GB
        with cls._boot_lock:
            if cls._bootstrapped and not force:
                return
            cls._register_atexit()

            if not force and cls._sentinel_valid():
                cls._bootstrapped = True
                return

            errors = []
            created = []
            try:
                for d in cls._ALL:
                    try:
                        d.mkdir(parents=True, exist_ok=True)
                        created.append(d)
                    except Exception as e:
                        errors.append((d, e))

                if errors:
                    raise BootstrapError(
                        "bootstrap failed: " + "; ".join(
                            f"{d}: {e!r}" for d, e in errors
                        ),
                        context={"failed": [str(d) for d, _ in errors]},
                    )

                cls.ensure_writable()
                cls.check_disk(min_free_gb)
                cls._write_sentinel()
                cls._bootstrapped = True
            except Exception:
                cls._cleanup_probes()
                raise

    @classmethod
    def _sentinel_valid(cls):
        try:
            if not cls.SENTINEL.exists():
                return False
            for d in cls._ALL:
                if not d.exists() or not d.is_dir():
                    return False
            return True
        except Exception:
            return False

    @classmethod
    def _write_sentinel(cls):
        payload = json.dumps({
            "pid": _PID,
            "ts": time.time(),
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "tiers": list(cls.TIERS),
        }).encode("utf-8")
        try:
            _atomic_write(cls.SENTINEL, payload)
        except Exception:
            pass

    # ----------------------------------------------------------------
    #  WRITABILITY PROBE
    # ----------------------------------------------------------------

    @classmethod
    def ensure_writable(cls):
        with _HANDLER.run.__self__ if False else contextlib.nullcontext():
            probes = []
            try:
                for d in cls._ALL:
                    probe = _probe_name(d)
                    try:
                        probe.write_bytes(b"ok")
                        probes.append(probe)
                    except Exception as e:
                        classified = ErrorClassifier.classify(e)
                        if classified is not None:
                            raise NotWritableError(
                                f"cannot write to {d}: {e!r}",
                                path=d, cause=e,
                            ) from e
                        raise
                for probe in probes:
                    try:
                        probe.unlink(missing_ok=True)
                    except Exception:
                        pass
            finally:
                for probe in probes:
                    try:
                        probe.unlink(missing_ok=True)
                    except Exception:
                        pass

    # ----------------------------------------------------------------
    #  DISK SPACE
    # ----------------------------------------------------------------

    @classmethod
    def disk_free_gb(cls):
        try:
            usage = shutil.disk_usage(_long_path(cls.ROOT))
            return usage.free / (1024 ** 3)
        except Exception:
            return -1.0

    @classmethod
    def check_disk(cls, min_free_gb=None):
        min_free_gb = min_free_gb if min_free_gb is not None else cls.MIN_FREE_GB
        free = cls.disk_free_gb()
        if free < 0:
            return
        if free < min_free_gb:
            raise DiskSpaceError(
                f"only {free:.2f} GB free, need >= {min_free_gb:.2f} GB",
                context={"free_gb": free, "min_gb": min_free_gb},
            )

    # ----------------------------------------------------------------
    #  LOW-LEVEL FILE OPS
    # ----------------------------------------------------------------

    @classmethod
    def safe_remove(cls, path, retries=None):
        p = Path(path)
        if not p.exists():
            return True
        if retries is None:
            retries = _HANDLER.max_retries

        def _do():
            _clear_readonly(p)
            if p.is_dir():
                shutil.rmtree(_long_path(p), onerror=_on_rmtree_error)
            else:
                p.unlink()
            return True

        try:
            with cls._lock:
                return _HANDLER.run(_do)
        except FolderError as e:
            _LOG.warning("safe_remove failed for %s: %s", p, e.to_dict())
            return False
        except FileNotFoundError:
            return True

    @classmethod
    def _iter_contents(cls, d):
        try:
            return list(Path(d).iterdir())
        except FileNotFoundError:
            return []
        except Exception as e:
            classified = ErrorClassifier.classify(e)
            if classified is not None:
                raise classified from e
            return []

    @classmethod
    def _size_of(cls, path):
        return _safe_size(path)

    @classmethod
    def _clear_readonly_tree(cls, path):
        if not path.exists():
            return
        try:
            for root, dirs, files in os.walk(_long_path(path), topdown=False):
                for name in files:
                    _clear_readonly(Path(root) / name)
                for name in dirs:
                    _clear_readonly(Path(root) / name)
        except Exception:
            pass

    # ----------------------------------------------------------------
    #  TIER CLEARING
    # ----------------------------------------------------------------

    @classmethod
    def clear_tier(cls, tier, dry_run=False):
        if tier == "all":
            return cls.clear_all(dry_run=dry_run)
        d = cls.tier(tier)
        removed = 0
        failed = 0
        freed = 0
        errors = []
        if not d.exists():
            return {"tier": tier, "removed": 0, "failed": 0,
                    "freed_kb": 0, "dry_run": dry_run, "errors": errors}
        cls._clear_readonly_tree(d)
        for child in cls._iter_contents(d):
            size = cls._size_of(child)
            if dry_run:
                removed += 1
                freed += size
                continue
            try:
                if cls.safe_remove(child):
                    removed += 1
                    freed += size
                else:
                    failed += 1
                    errors.append({"path": str(child),
                                    "reason": "safe_remove returned False"})
            except FolderError as e:
                failed += 1
                errors.append(e.to_dict())
            except Exception as e:
                failed += 1
                errors.append({"path": str(child), "reason": repr(e)})
        return {
            "tier": tier, "removed": removed, "failed": failed,
            "freed_kb": round(freed / 1024, 1),
            "dry_run": dry_run, "errors": errors,
        }

    @classmethod
    def clear_all(cls, dry_run=False):
        results = {}
        total_removed = 0
        total_failed = 0
        total_freed = 0
        all_errors = []
        for tier in cls.TIERS:
            r = cls.clear_tier(tier, dry_run=dry_run)
            results[tier] = r
            total_removed += r["removed"]
            total_failed += r["failed"]
            total_freed += r["freed_kb"]
            all_errors.extend(r.get("errors", []))
        if not dry_run:
            try:
                cls.SENTINEL.unlink(missing_ok=True)
            except Exception:
                pass
            cls.bootstrap(force=True)
        return {
            "tiers": results,
            "removed": total_removed,
            "failed": total_failed,
            "freed_kb": round(total_freed, 1),
            "dry_run": dry_run,
            "errors": all_errors,
        }

    # ----------------------------------------------------------------
    #  MAINTENANCE
    # ----------------------------------------------------------------

    @classmethod
    def sweep_tmp(cls, max_age_hours=6.0):
        cutoff = time.time() - max_age_hours * 3600
        removed = 0
        patterns = (".tmp", ".tmp.", "-wal", "-shm")
        for d in (cls.TMP, cls.CACHE, cls.STATE, cls.DB, cls.OUTPUT):
            if not d.exists():
                continue
            for child in cls._iter_contents(d):
                name = child.name
                if not any(mark in name for mark in patterns):
                    continue
                try:
                    mtime = child.stat().st_mtime
                except Exception:
                    continue
                if mtime < cutoff:
                    if cls.safe_remove(child):
                        removed += 1
        return removed

    @classmethod
    def rotate_logs(cls, keep=5):
        logs = sorted(
            cls.LOGS.glob("*.log*"),
            key=lambda p: p.stat().st_mtime if p.exists() else 0,
            reverse=True,
        )
        removed = 0
        for old in logs[keep:]:
            if cls.safe_remove(old):
                removed += 1
        return removed

    @classmethod
    def rotate_shards(cls, keep_days=30.0):
        cutoff = time.time() - keep_days * 86400
        removed = 0
        for shard in cls.SHARDS.glob("*.ndjson"):
            try:
                if shard.stat().st_mtime < cutoff:
                    if cls.safe_remove(shard):
                        removed += 1
            except Exception:
                continue
        return removed

    # ----------------------------------------------------------------
    #  LEGACY MIGRATION
    # ----------------------------------------------------------------

    @classmethod
    def migrate_legacy(cls, dry_run=False):
        plan = {
            "crawl.state.json": cls.STATE,
            "queue.txt": cls.STATE,
            "queue.journal": cls.STATE,
            "done.txt": cls.STATE,
            "errors.txt": cls.STATE,
            "blocked.txt": cls.STATE,
            "journal.ndjson": cls.STATE,
            "crawl.pid": cls.STATE,
            "dedup.sqlite": cls.DB,
            "bloom.bin": cls.DB,
            "crawl.log": cls.LOGS,
            "output.ndjson": cls.OUTPUT,
        }
        moved = []
        skipped = []
        failed = []
        for name, dest in plan.items():
            src = cls.ROOT / name
            if not src.exists():
                skipped.append(name)
                continue
            if dry_run:
                moved.append(name)
                continue
            try:
                dest.mkdir(parents=True, exist_ok=True)
                target = dest / name
                if target.exists():
                    cls.safe_remove(target)
                shutil.move(_long_path(src), _long_path(target))
                moved.append(name)
            except Exception as e:
                classified = ErrorClassifier.classify(e)
                failed.append({"name": name,
                                "error": classified.to_dict() if classified else repr(e)})

        legacy_dirs = {
            cls.ROOT / ".cache": cls.CACHE,
            cls.ROOT / ".agent": cls.AGENT,
        }
        for src, dest in legacy_dirs.items():
            if not src.exists():
                continue
            if dry_run:
                moved.append(src.name)
                continue
            try:
                dest.mkdir(parents=True, exist_ok=True)
                for child in src.iterdir():
                    target = dest / child.name
                    if target.exists():
                        cls.safe_remove(target)
                    shutil.move(_long_path(child), _long_path(target))
                cls.safe_remove(src)
                moved.append(src.name)
            except Exception as e:
                classified = ErrorClassifier.classify(e)
                failed.append({"name": src.name,
                                "error": classified.to_dict() if classified else repr(e)})

        return {"moved": moved, "skipped": skipped, "failed": failed,
                "dry_run": dry_run}

    # ----------------------------------------------------------------
    #  CORRUPT STATE RECOVERY
    # ----------------------------------------------------------------

    @classmethod
    def load_json_safe(cls, path, default=None, backup_dir=None):
        p = Path(path)
        if not p.exists():
            return default
        backup_dir = Path(backup_dir) if backup_dir else p.parent / "corrupt"
        try:
            with open(_long_path(p), "rb") as f:
                data = f.read()
            return json.loads(data)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as e:
            try:
                backup_dir.mkdir(parents=True, exist_ok=True)
                stamp = time.strftime("%Y%m%d-%H%M%S")
                backup = backup_dir / f"{p.name}.{stamp}.corrupt"
                shutil.copy2(_long_path(p), _long_path(backup))
                _LOG.warning("corrupt file backed up: %s -> %s", p, backup)
            except Exception:
                pass
            raise CorruptedStateError(
                f"corrupt state file: {p}",
                path=p, cause=e,
            ) from e
        except Exception as e:
            classified = ErrorClassifier.classify(e)
            if classified is not None:
                raise classified from e
            raise

    @classmethod
    def save_json_safe(cls, path, obj):
        try:
            data = json.dumps(obj, default=str).encode("utf-8")
            _atomic_write(path, data)
        except Exception as e:
            classified = ErrorClassifier.classify(e)
            if classified is not None:
                raise classified from e
            raise

    # ----------------------------------------------------------------
    #  REPORTING
    # ----------------------------------------------------------------

    @classmethod
    def report(cls, detailed=False):
        out = {
            "root": str(cls.ROOT),
            "data": str(cls.DATA),
            "disk_free_gb": round(cls.disk_free_gb(), 2),
            "pid": _PID,
            "tiers": {},
        }
        for tier in cls.TIERS:
            d = cls.tier(tier)
            files = 0
            bytes_total = 0
            newest = 0.0
            oldest = float("inf")
            if d.exists():
                try:
                    for f in d.rglob("*"):
                        if not f.is_file():
                            continue
                        try:
                            st = f.stat()
                        except Exception:
                            continue
                        files += 1
                        bytes_total += st.st_size
                        newest = max(newest, st.st_mtime)
                        oldest = min(oldest, st.st_mtime)
                except Exception:
                    pass
            entry = {
                "path": str(d),
                "files": files,
                "size_kb": round(bytes_total / 1024, 1),
            }
            if detailed and files:
                entry["newest_ts"] = newest
                entry["oldest_ts"] = oldest if oldest != float("inf") else 0
            out["tiers"][tier] = entry
        return out

    @classmethod
    def summarize(cls):
        r = cls.report()
        lines = [
            f"FolderManager root: {r['root']}",
            f"Data root         : {r['data']}",
            f"Disk free         : {r['disk_free_gb']} GB",
            f"PID               : {r['pid']}",
        ]
        for tier, e in r["tiers"].items():
            lines.append(f"  {tier:12s} {e['files']:6d} files  "
                         f"{e['size_kb']:10.1f} KB")
        return "\n".join(lines)

    # ----------------------------------------------------------------
    #  RUN LOCK
    # ----------------------------------------------------------------

    @classmethod
    def lock_file_path(cls):
        return cls.STATE / "crawl.lock"

    @classmethod
    def acquire_run_lock(cls, timeout=10.0):
        lock = cls.lock_file_path()
        lock.parent.mkdir(parents=True, exist_ok=True)
        try:
            if lock.exists():
                try:
                    old_pid = int(lock.read_text().strip())
                except Exception:
                    old_pid = -1
                if old_pid > 0 and old_pid != _PID:
                    try:
                        import psutil
                        if psutil.pid_exists(old_pid):
                            return False
                    except Exception:
                        pass
            _atomic_write(lock, str(_PID).encode("ascii"))
            return True
        except Exception:
            return True

    @classmethod
    def release_run_lock(cls):
        try:
            lock = cls.lock_file_path()
            if lock.exists():
                try:
                    pid = int(lock.read_text().strip())
                    if pid == _PID:
                        lock.unlink()
                except Exception:
                    pass
        except Exception:
            pass

    # ----------------------------------------------------------------
    #  DIAGNOSTICS ENTRY POINT
    # ----------------------------------------------------------------

    @classmethod
    def diagnose(cls):
        d = Diagnostics(cls)
        results = d.run()
        return {"results": results, "summary": d.summary()}


# ============================================================================
#  MODULE ENTRY
# ============================================================================

def _bootstrap_if_parent():
    """Only bootstrap in the parent process. Children inherit the sentinel."""
    try:
        import multiprocessing as _mp
        current = _mp.current_process()
        if current.name != "MainProcess":
            return
    except Exception:
        pass
    try:
        FolderManager.bootstrap()
    except Exception as e:
        _LOG.error("bootstrap failed: %r", e)
        raise


_bootstrap_if_parent()