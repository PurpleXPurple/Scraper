# Changelog

Complete project history for the NEXUS universal crawler. Every iteration, every file, every fix, every decision.

---

## Project identity

- **Name:** NEXUS
- **Purpose:** Universal cross-domain web crawler for AI dataset generation
- **Constraint:** No browsers, no accounts, no API keys required for core path
- **Libraries:** Only those in `libraries.txt` plus `psutil`, `curl-cffi`, `patchright`, `nodriver`, `camoufox` (browser fallbacks rejected)
- **Author:** Purple

---

## [4.0.0] — 2026-09-12

**Theme:** Distributed crawling infrastructure, API-first architecture, adaptive tuning, error containment.

---

### Added — `folder_manager.py` (new file, ~470 lines)

Centralized path management. Every runtime artifact moves from project root into `.data/`.

**Tier structure:**
```
.data/
├── state/      crawl.state.json, queue.txt, done.txt, errors.txt,
│               blocked.txt, journal.ndjson, crawl.pid, crawl.lock
├── db/         dedup.sqlite, bloom.bin, mos_cache.sqlite, extraction.sqlite,
│               api_router_cache.sqlite
├── cache/      domain_rates.json, mos_budget.json, mos_host_prefs.json,
│               dead_letter.jsonl, error_fast.json, se_quota.json,
│               se_breaker.json, se_stats.json, api_router_budget.json,
│               apis_guru_list.json, cookies/, bootstrap/
├── logs/       crawl.log, debug.json
├── agent/      embeddings.bin, entities.jsonl, topics.jsonl
├── output/     manifest.json, output.ndjson
│   ├── shards/
│   └── quarantine/
├── cookies/    per-domain cookie jars
└── tmp/        scratch space
```

**Public API:**
- `FolderManager.bootstrap(force=False, min_free_gb=None)` — idempotent, PID-aware, sentinel-driven
- `FolderManager.tier(name)` — resolve tier name to Path
- `FolderManager.disk_free_gb()` — free space probe
- `FolderManager.check_disk(min_free_gb)` — raises `DiskSpaceError` if low
- `FolderManager.ensure_writable()` — writes PID-suffixed probe in every tier, cleans in finally
- `FolderManager.safe_remove(path, retries=4)` — Windows-safe rmtree with readonly stripping
- `FolderManager.clear_tier(tier, dry_run=False)` — wipe one tier, collect per-file errors
- `FolderManager.clear_all(dry_run=False)` — wipe all tiers, re-bootstrap
- `FolderManager.migrate_legacy(dry_run=False)` — move root files into `.data/`
- `FolderManager.sweep_tmp(max_age_hours=6.0)` — remove stale `.tmp`, `-wal`, `-shm`
- `FolderManager.rotate_logs(keep=5)` — delete oldest log files
- `FolderManager.rotate_shards(keep_days=30)` — delete old shards
- `FolderManager.report(detailed=False)` — file counts and sizes per tier
- `FolderManager.summarize()` — one-screen text summary
- `FolderManager.acquire_run_lock(timeout=10)` — prevents concurrent crawlers
- `FolderManager.release_run_lock()`
- `FolderManager.diagnose()` — runs 14 self-checks

**Error taxonomy (15 categories):**
```python
class ErrorCategory(str, Enum):
    GENERIC, BOOTSTRAP, DISK, PERMISSION, LOCKED, PATH, SYMLINK,
    CORRUPT, CONCURRENT, CASE, HANDLE, ENCODING, STATE, IO, UNKNOWN
```

**Exception classes:**
- `FolderError` (base)
- `BootstrapError` (not recoverable)
- `DiskSpaceError`
- `NotWritableError` (not recoverable)
- `LockedFileError` (retryable)
- `PathTooLongError`
- `SymlinkLoopError`
- `CorruptedStateError`
- `ConcurrentAccessError` (retryable)
- `CaseCollisionError` (not recoverable)
- `HandleExhaustedError` (retryable)
- `EncodingMismatchError`
- `StateMismatchError`
- `IOFailureError`

**`ErrorClassifier`** maps OS exceptions:
- `PermissionError` → `LOCKED`
- `FileExistsError` → `CONCURRENT`
- `IsADirectoryError`/`NotADirectoryError` → `IO`
- `OSError errno=28` → `DISK`
- `OSError errno=36` → `PATH`
- `OSError errno=40` → `SYMLINK`
- `OSError errno=24` → `HANDLE`
- `OSError winerror=32/33` → `LOCKED`
- `OSError winerror=206` → `PATH`
- `UnicodeError` → `ENCODING`
- `json.JSONDecodeError` → `CORRUPT`
- `FileNotFoundError` → returns `None` (treated as success for deletion)

**`ErrorHandler`** — retry logic:
- `RETRYABLE = {LOCKED, CONCURRENT, HANDLE}` — retry with exponential backoff
- `FATAL = {PERMISSION, BOOTSTRAP, CASE}` — raise immediately
- `register(kind, hook)` — per-category hooks
- `run(fn, *args, category_hint=None)` — main dispatcher

**`FileLock`** — cross-process atomic lock:
- Uses `os.open(path, O_CREAT | O_EXCL | O_WRONLY)`
- Polls with timeout, cleans stale locks (>4× timeout)
- Context manager interface

**`Diagnostics`** class with 14 checks:
1. Python version ≥ 3.9
2. Disk space > 0.5 GB
3. Data writable
4. Long paths (20-level deep test)
5. Case collisions in tiers
6. Symlinks in tiers
7. JSON validity (domain_rates, mos_budget, mos_host_prefs)
8. SQLite integrity (dedup, mos_cache, extraction)
9. Open handle count < 1000
10. Orphan probe files
11. Bootstrap sentinel present
12. Stale locks
13. Encoding roundtrip
14. Tier size computation

**Windows-specific:**
- `_long_path()` prefixes `\\?\` for paths ≥ 240 chars
- `_clear_readonly()` strips readonly bit before deletion
- `_on_rmtree_error()` retries on trapped `PermissionError`
- `_retry()` with exponential backoff for antivirus-held locks

**Atomic file operations:**
- `_atomic_write(path, data, fsync=True)` — tmp + fsync + os.replace
- `save_json_safe(path, obj)` — JSON-safe with corrupt detection
- `load_json_safe(path, default, backup_dir)` — backs up corrupt files to `corrupt/`

**Migration logic:**
```python
LEGACY_FILES = {
    "crawl.state.json": STATE,
    "queue.txt": STATE,
    "queue.journal": STATE,
    "done.txt": STATE,
    "errors.txt": STATE,
    "blocked.txt": STATE,
    "journal.ndjson": STATE,
    "crawl.pid": STATE,
    "dedup.sqlite": DB,
    "bloom.bin": DB,
    "crawl.log": LOGS,
    "output.ndjson": OUTPUT,
}
LEGACY_DIRS = {
    ".cache/": CACHE,
    ".agent/": AGENT,
}
```

**PID-aware cleanup:**
- Every probe file named `.write_probe.{pid}`
- `atexit` handler removes `.write_probe.{pid}` and `.diag.{pid}` files
- Bootstrap skips in child processes via `_bootstrap_if_parent()`

**Fixed 9 known failure modes:**
1. Race condition on shared probe file (PID-suffix)
2. Bare `except Exception` masking `FileNotFoundError` (`missing_ok=True`)
3. Module-level `bootstrap()` in spawned children (parent check)
4. `threading.Lock` doesn't protect cross-process (atomic O_EXCL)
5. Misattributed traceback from spawn (auto-resolves)
6. Orphan probe files (finally cleanup)
7. Windows readonly file deletion (chmod strip)
8. Long path failures (\\?\ prefix)
9. Partial bootstrap state (atomic sentinel)

---

### Added — `error_fast.py` (new file, ~430 lines)

Fast error handling and noise suppression.

**Error kinds (20):**
```python
class Kind(str, Enum):
    LOOP_CLOSED       # "Event loop is closed"
    CFFI_TIMER        # "Exception ignored from cffi callback"
    ASYNC_CANCELLED   # asyncio.CancelledError
    KEYBOARD_INTERRUPT # Ctrl-C
    TIMEOUT           # network timeout
    CONNECTION        # reset/refused/aborted
    SSL_TLS           # cert/handshake failures
    DNS               # resolution failures
    HTTP_4XX          # client errors
    HTTP_5XX          # server errors
    RATE_LIMIT        # 429
    PARSE             # json/html/xml parse
    DECODE            # unicode/encoding
    IMPORT            # module imports
    FILE_IO           # file not found
    PERMISSION        # permission denied
    DISK              # disk full
    MEMORY            # out of memory
    DEPENDENCY        # missing version
    UNKNOWN           # fallback
```

**Recovery strategies (6):**
```python
class Recovery(str, Enum):
    IGNORE       # silently continue
    RETRY        # retry with backoff
    RETRY_LOOP   # recreate event loop and retry
    FALLBACK     # try alternate path
    ESCALATE     # propagate up
    ABORT        # stop everything
```

**Classification patterns:** 25 compiled regexes covering the error messages, ordered by specificity.

**`NoiseSuppressor`** — kills curl_cffi timer flood:
- Replaces `sys.unraisablehook` at interpreter level
- Replaces asyncio exception handler
- Filters by 4 noise fragments:
  - `"Exception ignored from cffi callback"`
  - `"Event loop is closed"`
  - `"async_curl._timer = async_curl.loop.call_later"`
  - `"_check_closed"`
- Counts suppressed messages per process

**`LoopManager`** — one persistent asyncio loop per process:
- `get_loop()` — creates or returns existing
- `run(coro, timeout=None)` — runs on persistent loop, never closes
- `_drain(loop)` — cancels pending tasks on failure
- `close()` — explicit shutdown only
- `stats()` — runs count, has_loop, loop_closed, loop_running
- Fixes: `asyncio.run()` closing the loop while curl_cffi timers still fire

**`patch_asyncio()`** — optional global replacement of `asyncio.run` with `LoopManager.run`. Off by default.

**`ErrorFast`** class:
- Thread-safe event registry with 5000-entry rolling buffer
- Per-kind, per-recovery, per-type counters
- Unique traceback hash tracking (dedup identical failures)
- `record(exc, kind=None, recovery=None)` — auto-classify if not given
- `register(kind, hook)` — per-kind callbacks
- `stats()` — full snapshot
- `save(path)` — dump to JSON

**Traceback hashing:** `blake2b` over last 6 stack frames + exception type. Same failure at same location gets same hash.

**Decorators:**
```python
@fast_catch(default=None, kinds=None, reraise=False)
@fast_async_catch(default=None, kinds=None, reraise=False)
```

**Context managers:**
```python
with swallow(Kind.CONNECTION):
    ...

with retry(times=3, delay=0.5, backoff=2.0, kinds=None):
    ...
```

**Safe wrappers:**
- `safe_asyncio_run(coro, timeout=None)` — uses `LoopManager`, retries on loop-closed
- `safe_async_session_close(session)` — closes AsyncSession without timer noise

**CLI:**
- `--report` — print full stats
- `--save` — dump to `.data/cache/error_fast.json`
- `--test` — 4 self-tests (loop closed, cffi timer, cancelled, safe_run)
- `--classify "message"` — classify any error message

**Test output (from run):**
```
[test] simulating the cffi timer noise...
[test] safe_asyncio_run returned 42
[test] fast_catch swallowed loop-closed error
[test] all checks passed
```

---

### Added — `api_router.py` (new file, ~1900 lines)

32-method adaptive API discovery system.

**`Hardware` profiler:**
- CPU physical/logical cores via `psutil.cpu_count()`
- RAM total via `psutil.virtual_memory()`
- Disk free via `psutil.disk_usage()`
- Tier classification:
  - `workstation` — ≥16 cores, ≥32 GB RAM, ≥100 GB disk
  - `laptop` — ≥8 cores, ≥16 GB RAM, ≥50 GB disk
  - `small` — ≥4 cores, ≥8 GB RAM, ≥20 GB disk
  - `minimal` — below

**`AdaptiveTuner` per-tier config:**

| Setting | workstation | laptop | small | minimal |
|---|---|---|---|---|
| concurrency | 32 | 16 | 8 | 4 |
| tier_timeout | 12.0s | 15.0s | 20.0s | 25.0s |
| per_probe_timeout | 8.0s | 10.0s | 12.0s | 15.0s |
| js_bundle_size_mb | 20 | 10 | 5 | 2 |
| js_max_bundles | 12 | 8 | 4 | 2 |
| source_map_size_mb | 30 | 15 | 8 | 3 |
| probe_paths_batch | 24 | 16 | 10 | 6 |
| cache_memory_mb | 256 | 128 | 64 | 32 |
| osint_enabled | True | True | True | False |
| ct_lookups_per_hour | 100 | 40 | 15 | 0 |
| wayback_lookups_per_hour | 200 | 80 | 30 | 0 |

- `detector_priority(name, base)` — weight by observed success and median latency
- `detector_timeout(name)` — 2× observed p95 latency, capped at 2× tier timeout
- `set_network_latency(ms)` — scales per-probe timeout 0.7× to 1.5×
- Latency probe: `HEAD https://www.google.com/generate_204`

**`AdaptiveBudget`:**
- Per-service hourly and daily counters
- `allowed(service, limit_hour, limit_day)`
- `record(service)`
- Persists to `.data/cache/api_router_budget.json`

**`DiscoveryCache`:**
- SQLite tables: `detections (host, detector)`, `host_summary (host)`
- 7-day TTL on both
- Negative caching (skip re-probing known-empty hosts)

**32 detection methods across 6 tiers:**

**Tier 1 — Direct handler registry (9 entries):**
- `stackexchange` → `_handler_stackexchange`
- `stackoverflow` → `_handler_stackexchange`
- `superuser`, `serverfault`, `askubuntu`, `mathoverflow` → same handler

**Tier 2 — RFC / well-known (6 methods):**
- **M01** `.well-known/api-catalog` (RFC 9727) — parses linkset, extracts `rel="service-desc"`
- **M02** `.well-known/openapi.json` / `.yaml` / no-extension
- **M03** `.well-known/openid-configuration` — OIDC provider detection
- **M04** `.well-known/oauth-authorization-server` (RFC 8414)
- **M05** `.well-known/security.txt` (RFC 9116) — contact hints
- **M06** `.well-known/mcp` — Model Context Protocol server card

**Tier 3 — HTML content (4 methods):**
- **M07** `<link rel="service-desc"|"service-doc"|"api-catalog">`
- **M08** JSON-LD `@type: WebAPI|APIReference|EntryPoint`
- **M09** SPA inline configs: `__NEXT_DATA__`, `__NUXT__`, `window.__INITIAL_STATE__`, `window.__DATA__`, `window.__APP_STATE__`, `__APOLLO_STATE__`, `__REDUX_STATE__`, `window.__PRELOADED_STATE__`
- **M10** meta tags: `api-base`, `api-url`, `api-host`, `csrf-token`, `generator`

**Tier 4 — Protocol probing (6 methods):**
- **M11** HTTP `OPTIONS` — Allow header analysis, ≥3 API methods required
- **M12** HTTP `HEAD` — Content-Type detection for 6 JSON variants
- **M13** OpenAPI path probes (17 paths in parallel batches)
- **M14** Swagger UI / ReDoc detection (10 UI paths)
- **M15** GraphQL introspection (8 paths, `{__schema{queryType{name} mutationType{name}}}`)
- **M16** SOAP/WSDL/WADL (8 paths)

**Tier 5 — JavaScript analysis (4 methods):**
- **M17** JS bundle regex — 8 patterns over up to 12 bundles at 20 MB each
  - `/api/`, `/v[1-9]/`, `fetch(`, `axios.get(`, `XMLHttpRequest.open`, `https://api.`, `/graphql`, `/rest/`
- **M18** Source map discovery — `//# sourceMappingURL=` + `sourcesContent[]` analysis
- **M19** WebSocket URL extraction — `wss?://`, `new WebSocket(`, `socket.io`, `SockJS`
- **M20** Framework fingerprint — 16 frameworks with per-framework probe paths:
  - Next.js, Nuxt, Django REST, Rails API, Strapi, Laravel, Spring Boot, FastAPI, Flask-RESTX, GraphQL Yoga, Express, ASP.NET Core, Phoenix, WordPress, Ghost

**Tier 6 — External OSINT (12 methods):**
- **M21** Certificate Transparency via `crt.sh` — subdomain enumeration
- **M22** DNS SRV/TXT/CNAME queries via Google DoH
- **M23** Wayback CDX historical URLs filtered for `/api/`, `/v1/`, `/graphql`
- **M24** Favicon hash lookup against known products (14 fingerprints)
- **M25** APIs.guru directory lookup (40 MB, cached 24h)
- **M26** RapidAPI marketplace search
- **M27** IP/ASN/CDN detection via ip-api.com — 9 CDN names
- **M28** HSTS preload status
- **M29** RDAP nameserver query
- **M30** HTTP redirect chain analysis
- **M31** CSP report URI extraction
- **M32** Common subdomain enumeration (10 prefixes)

**Result schema:**
```python
@dataclass
class ApiDiscoveryResult:
    url: str
    host: str
    api_type: str           # openapi|graphql|rest|soap|wadl|json|marketplace|ct_only
    endpoint: str
    spec_url: Optional[str]
    spec_format: str        # json|yaml|xml|graphql_sdl
    detector: str
    confidence: float
    metadata: dict
```

**Detector isolation:** each detector runs in its own task with a per-tier timeout. Failures are swallowed. First success at or above tier's `min_confidence` returns.

**CLI:**
- `--probe URL` — full 32-detector chain
- `--show-hardware` — profile + tuner snapshot
- `--show-diagnostics` — run folder manager checks
- `--show-cache` — cache stats

---

### Added — `se_api.py` (rewritten, ~1200 lines, version 2.0.0)

Hardened Stack Exchange API client.

**Anti-detection machinery:**
- 3 endpoints rotated: `api.stackexchange.com/2.3`, `/2.2`, `stackexchange.com/2.3`
- 7 User-Agents (Chrome 136/131, Safari 18.4, Firefox 135, Opera 95, iPhone Safari, Linux Chrome)
- 7 impersonate targets: `chrome136`, `chrome131`, `chrome142`, `safari184`, `firefox135`
- Per-request jitter: `uniform(0.15, 1.1)` seconds
- Full jitter backoff: `delay = random.uniform(0, base ** attempt)` capped at 45s
- Retry-After honored on 429
- `backoff` field honored from SE responses (dynamic throttle)
- Randomized `Accept-Encoding` (3 variants), `Accept-Language` (4 locales), `Cache-Control` (3 options)

**Quota tracking:**
- Persists to `.data/cache/se_quota.json`
- Tracks `quota_remaining` from responses
- Refuses requests when below `SE_QUOTA_SAFE_MARGIN = 40`

**Per-endpoint breaker:**
- 5 failures opens endpoint for 60s
- Success resets counter
- Persists to `.data/cache/se_breaker.json`

**Stats tracking:**
- Total requests, successes, failures, 429s
- Backoffs honored, retries
- Median latency in ms
- Per-endpoint and per-UA counts
- Persists to `.data/cache/se_stats.json`

**API methods:**

| Method | Endpoint | Purpose |
|---|---|---|
| `se_fetch_question` | `/questions/{id}` | Single question with body |
| `se_fetch_answers` | `/questions/{id}/answers` | Answers sorted by votes |
| `se_fetch_comments` | `/questions/{id}/comments` | Comments (special `withbody` filter) |
| `se_fetch_related` | `/questions/{id}/related` | Related question IDs |
| `se_fetch_search` | `/search/advanced` | Full-text + tag search |
| `se_fetch_tag` | `/questions` with `tagged` | Tag-listing |

**Sync and async variants of every method.**

**`se_site_for_url(url)`** — maps 180+ subdomains to SE API `site` parameter. Handles:
- `stackoverflow.com`, `serverfault.com`, `superuser.com`, `askubuntu.com`, `mathoverflow.net`, `stackapps.com`
- All `*.stackexchange.com` subdomains
- Localized `*.stackoverflow.com` (es, pt, ru, ja, ko, fr, de, it, pl, tr, vi, th, id, bn, uk, gr, ro, nl, cs, hu, fi, sv, da, no, he, ar, fa, hi)

**URL parsers:**
- `se_parse_question_id(url)` — from `/questions/{id}` or `/q/{id}`
- `se_parse_answer_id(url)` — from `#answer-{id}` or `/{qid}#{aid}`
- `se_parse_tag(url)` — from `/questions/tagged/{tag}` or `/tags/{tag}`
- `se_parse_user_id(url)` — from `/users/{id}` or `/u/{id}`

**`se_item_to_record(item, site, url, answers, comments, related)`** — builds full nexus record with:
- Question body as first section
- Accepted answer + all answers (up to 20) as sections
- Comments aggregated under a single section
- Related question IDs in metadata
- Tags as topics
- Owner display name, reputation, user_id in metadata
- Score, view_count, answer_count, is_answered
- Publication date from `creation_date`
- Link as canonical URL

**`se_fetch_url_sync(url)` / `se_fetch_url(url)`** — one-shot: fetches question + answers + comments + related in parallel, returns full record.

**Quota/stats/breaker diagnostics:**
- `se_stats()` — full snapshot
- `se_quota_status()` — used today, quota remaining, exhausted flag
- `se_save()` — persist all three JSON files

---

### Added — `spoof.py` (rewritten — SOD integration)

**`SODWorker`** — session-bound identity with 27 slots:
- `profile`, `impersonate`, `ua`, `sec_ch_ua`, `sec_ch_ua_mobile`, `sec_ch_ua_platform`
- `accept`, `accept_encoding`, `priority`
- `locale`, `header_order`, `extra_fp`, `akamai`
- `proxy`, `created_at`, `requests_served`
- `_nonce`, `_last_url`, `_last_ts`, `_lock`

**`SODPool`** — worker pool:
- Default size 16 (`SOD_WORKER_POOL_SIZE`)
- Sticky domain→worker mapping (`SOD_STICKY_DOMAIN`)
- Recycles workers after 600s (`SOD_WORKER_RECYCLE_SECONDS`)
- `acquire(domain)` returns same worker for same domain

**23-layer spoofing stack:**

*TLS layer (7):*
1. JA3/JA4 via `impersonate`
2. JA3N via `tls_permute_extensions=True`
3. GREASE via `tls_grease=True`
4. ALPS via `CurlOpt.SSL_ENABLE_ALPS`
5. Cert compression via `tls_cert_compression="brotli"`
6. Session ticket via `CurlOpt.SSL_ENABLE_TICKET`
7. PSK session resumption

*HTTP/2 layer (5):*
8. SETTINGS frame via `CurlOpt.HTTP2_SETTINGS`
9. WINDOW_UPDATE via `CurlOpt.HTTP2_WINDOW_UPDATE`
10. Stream priority via `CurlOpt.HTTP2_STREAMS`
11. Pseudo-header order via `CurlOpt.HTTP2_PSEUDO_HEADERS_ORDER`
12. Header order via `CurlOpt.HTTPHEADER_ORDER`

*Application layer (11):*
13. HTTP/1.1 header order via `default_headers=False`
14. Client hints (sec-ch-ua family)
15. Accept-Encoding (zstd only for Chrome)
16. Locale rotation (12 locales)
17. Referer chain tracking
18. Sec-Fetch-* computed from referer
19. Timing jitter (0.7–2.4s normal, 0–0.05s fast)
20. Session persistence per domain
21. Proxy binding
22. Fingerprint rotation via `rotate_fingerprint()`
23. HTTP/3 QUIC optional via `CurlHttpVersion.V3ONLY`

**`_build_akamai_string(impersonate)`** — full 4-part Akamai fingerprint:
- Chrome: `1:65536;2:0;3:1000;4:6291456;6:262144|15663105|3:0:0:201,5:0:0:101,7:0:0:1|m,a,s,p`
- Firefox: `1:65536;2:0;3:1000;4:131072;5:16384|12517377|3:0:0:201,5:0:0:101,7:0:0:1|m,p,a,s`
- Safari: `2:0;4:4194304;3:100|10420225|0|m,s,a,p`

**`_enforce_consistency(profile, header_order)`** — refuses to build sessions with cross-layer mismatches:
- Chrome must have `sec-ch-ua`
- Firefox/Safari must NOT have `sec-ch-ua`
- Chrome header_order must include `sec-ch-ua`

**`SpoofedSession`** — facade for backwards compatibility:
- `__init__(domain, fast=False, profile_override=None, proxy=None)`
- Property proxies for `_last_url` and `_last_ts`
- `_jitter()`, `_referer()`, `_build_headers()`
- `get()`, `post()`, `rotate_fingerprint()`, `rotate_proxy()`, `close()`

**Fixed:** `TypeError` from invalid `extra_fp` keys (`tls_enable_alps`, `tls_enable_ticket`, `tls_record_size_limit`). These are now set via `CurlOpt` in `_apply_curl_options` instead.

**Fixed:** `SpoofedSession._last_url` and `_last_ts` not proxying to worker's attributes.

---

### Added — `scraper.py` (rewritten — 4.0.0, ~3000 lines)

**`Preloader`** class with 20 warmup steps:
1. `folder_manager` — FolderManager.bootstrap
2. `error_fast` — install suppressors
3. `regexes` — compile all 7 module regexes
4. `stopwords` — load all language stopword sets
5. `tld` — get_tld warm cache
6. `trafilatura` — run bare_extraction on sample
7. `justext` — run justext on sample
8. `selectolax` — parse sample
9. `htmldate` — run find_date
10. `dateparser` — parse 2 dates
11. `textstat` — run all 11 metrics
12. `pymupdf` — create/close PDF
13. `babel` — parse 2 locales
14. `tzlocal` — get timezone
15. `pyphen` — load hyphenation dict
16. `curl_cffi` — construct session
17. `entity_patterns` — run 9 regexes
18. `lang_stopword_map` — access config
19. `api_router` — import check
20. `se_api` — import check
21. `config_hash` — compute once

Each step is timed and reported. Failures logged but don't abort. Total preload: ~0.72s.

**`_error_fast_install()`** at module top:
```python
from error_fast import install_all as _error_fast_install, ...
_error_fast_install()
```

**Every `asyncio.run()` replaced with `safe_asyncio_run()`:**
- In `scrape_url` → `mos_fetch` calls
- In `main` → API mode runner
- In `_try_api_router` → route_sync wrapper

**Every `_AsyncRequestsSession` constructed with `default_headers=False`** so our header ordering survives.

**`mos_fetch` hardened:**
- Whole function wrapped in try/except
- `asyncio.CancelledError` returns `None`
- `async with AsyncSession` closes on persistent loop

**`_fetch_via_relay` catches `CancelledError` explicitly** and returns a benign `FetchResult`.

**`_one_service` catches `CancelledError`** at every await point.

**`_try_api_router` double-checks returned records** — bare `{"error": ...}` dicts return `None` instead of propagating.

**`verify_url` and `enrich_record`** wrap everything in try/except with `default_headers=False`.

**`@lru_cache(maxsize=1)` on `_config_hash()`** — computed once per process.

**`_ZERO_QUALITY` shared dict** — reduces allocation on error records.

**`_adaptive_extract_text` fast path** — trafilatura runs first; if ≥ 300 words (`MOS_FAST_ACCEPT_WORDS`), justext and selectolax walks are skipped entirely. Saves ~40% extraction CPU.

**Deferred imports in `_get_pyphen`** so the module loads fast.

---

### Added — `crawler.py` (rewritten — 4.0.0, ~2000 lines)

**`MercatorFrontier` — priority decay:**
- 8 front bands
- Items in frontier > 600s promoted one band up
- `decay(threshold_seconds=600.0)` called every 200 ticks

**`HostHealth` — continuous scoreboard:**
- Score range 0.0 – 1.0
- Success: +0.05 × min(consecutive_successes, 4)
- Failure: −0.15 × min(consecutive_failures, 3)
- Rate factors: `>= 0.7` full, `>= 0.4` half, `>= 0.2` one per minute, `< 0.2` skip

**`HealthRegistry`** — thread-safe per-host lookup

**`YieldTracker`** — rolling window of useful/failed per domain and path-pattern:
- `domain_yield(host)` returns mean signal from −0.5 to 1.0
- `path_yield(url)` same for `/{seg1}/{seg2}` patterns

**`DomainBootstrap`** — one-time per domain:
- Fetches 4 sitemap paths
- Parses robots.txt for `Sitemap:` directives
- Extracts RSS/Atom links from `<link rel="alternate">`
- Returns up to 100 seed URLs
- Cached per host for 24h in `.data/cache/bootstrap/`

**`AdaptiveConcurrency`** class scaffold — will wire into main loop in 4.1

**Frontier drain** — 400 items per tick inside main loop
**Idle check** — includes `frontier_empty`
**Shared counter** — `completed_count = mp.Value("i", 0)` incremented per result
**Startup log** — `crawler starting: seeds=N workers=N depth=N queue_cap=N`
**Shutdown log** — `crawler stopped: completed=N enqueued=N dup=N written=N`

**Fixed:** `_SESSION_ID_RE` and `_HEX_TOKEN_RE` start-of-string matching `(?:^|[?&])`
**Fixed:** `_CALENDAR_RE` compiled once at module load
**Fixed:** `_call_scrape` normalizes 3-tuple and 4-tuple returns
**Fixed:** writer honors `quarantine_category` field
**Fixed:** `dead_letter.jsonl` path from `FolderManager.CACHE`

---

### Added — `debug.py` (rewritten — v6, ~2300 lines)

**`Logger` class:**
- 8 levels: TRACE (5), DEBUG (10), INFO (20), PASS (25), WARN (30), FAIL (35), ERROR (40), FATAL (50)
- Per-level ANSI colors
- Three sinks: console, `AsyncFileWriter`, `RingBuffer`
- `with_context(**kwargs)` returns `_ContextLogger`
- `timer(label)` context manager
- `event(name, **fields)`, `counter(name, delta)`
- `timing_stats()`, `event_counts()`, `counter_snapshot()`

**`AsyncFileWriter`:**
- Background thread with queue
- 200-line or 1s flush batches
- JSON-per-line output
- Non-blocking on caller

**`RingBuffer`:**
- 50,000-entry deque
- Thread-safe append/snapshot/drain

**`TestContext`:**
- Rich assertions: `expect`, `expect_eq`, `expect_neq`, `expect_in`, `expect_gt`, `expect_lt`, `expect_raises`
- Per-test logger
- RSS and CPU tracking
- Nanosecond elapsed time

**Test registry** with `@test(category, name)` decorator.

**~180 tests across 20 categories:**

| Category | Count | Description |
|---|---|---|
| T0 | 3 | Environment, cleanup, folder manager |
| T1 | 7 | Imports for every module |
| T2 | 15 | Config invariants |
| T3 | 9 | Spoof engine + SOD pool |
| T4 | 17 | Crawler internals + HostHealth + YieldTracker + DomainBootstrap |
| T5 | 22 | Scraper internals + MOS classifier |
| T5b | 12 | Folder manager + error categories + JSON roundtrip + locks |
| T5c | 5 | SE API parsers + quota + stats |
| T5d | 4 | API router hardware + tuner + has_route + budget |
| T6_easy | 10 | https://example.com, httpbin, iana, rust-lang, python.org, go.dev, nodejs |
| T7_moderate | 10 | Postgres, Redis, SQLite, Rust docs, Wikipedia, HN |
| T8_dynamic | 10 | GitHub, Stack Overflow, Ars, Verge, BBC, Wired, Guardian |
| T9_js_heavy | 8 | Reddit, NYT, WaPo, Facebook, LinkedIn, YouTube, Twitch, Discord |
| T10_protected | 4 | Coinbase, Crunchbase, Glassdoor, Zillow |
| T13_docs | 8 | Python docs, MDN, git-scm, ArchWiki, man7, Rust std, Docker, K8s |
| T14_blogs | 8 | Fowler, PG, Rust blog, overreacted, jvns, Joel, Cloudflare, Stripe |
| T15_news | 7 | AP, NPR, DW, France24, CBC, ABC AU, SCMP |
| T17_academic | 6 | arXiv, PubMed, Nature, Science, PLOS, Frontiers |
| T18_gov_edu | 7 | NASA, NOAA, CDC, Harvard, MIT, Stanford, Oxford |
| T26_se_network | 6 | Full SE question fetches via API |
| T41 | 3 | Concurrency (bloom, logger, JSON) |
| T42 | 5 | Stress (extraction loop, chunk, simhash, logger, trap) |
| T43 | 7 | Regression (6 fixes + base_record) |

**CLI:**
- `--categories T0 T1 ...` — subset
- `--name "substring"` — filter
- `--list` — list all categories
- `--quiet` — suppress per-test
- `--log-level TRACE|DEBUG|INFO|PASS|WARN|FAIL|ERROR`
- `--log-file PATH` — structured JSON output
- `--no-console-logs`

**Structured report** at `debug_report.json`:
```json
{
  "run_meta": { "started_at", "elapsed", "rss_mb", "python", "platform",
                "cpu_count", "mem_total_gb", "disk_free_gb" },
  "summary": { "PASS": N, "FAIL": N, ... },
  "results": [ {category, name, status, detail, elapsed_ms, rss_mb,
                cpu_pct, extra, traceback} ]
}
```

---

### Added — `config.py` (rewritten — 4.0.0)

**New config blocks:**

`MOS_*` — Mixture Of Services:
```python
MOS_ENABLED = True
MOS_HEDGE_ENABLED = True
MOS_HEDGE_POLICIES = {"cloudflare_turnstile", "503_unavailable", "504_timeout"}
MOS_HEDGE_DELAY_MS = 800
MOS_STICKY_TTL = 86400
MOS_STICKY_SUCCESS_THRESHOLD = 3
MOS_STICKY_FAILURE_THRESHOLD = 3
MOS_DAILY_BUDGET = { ... 22 services ... }
MOS_BUDGET_WARN_RATIO = 0.80
MOS_BUDGET_STOP_RATIO = 0.95
MOS_FIRST_HOSTS = ( ... 11 hosts ... )
```

`API_ROUTER_*`:
```python
API_ROUTER_ENABLED = True
API_ROUTER_TIMEOUT = 15
API_ROUTER_MAX_ITEMS = 100
```

`SE_API_*`:
```python
SE_API_ENABLED = True
SE_API_KEY = None
SE_API_MAX_ANSWERS = 20
SE_API_TIMEOUT = 15
SE_ROUTE_BEFORE_DIRECT = True
SE_ACCEPT_EMPTY_TITLE = False
```

`SOD_*`:
```python
SOD_WORKER_POOL_SIZE = 16
SOD_WORKER_RECYCLE_SECONDS = 600
SOD_STICKY_DOMAIN = True
SOD_ROTATE_ON_BLOCK = True
```

`BROWSER_FALLBACK_*` — present but `BROWSER_FALLBACK_ENABLED = False` (user rejected browsers)

**Updated constants:**
- `CONFIG_VERSION = "4.0.0"`
- `CONFIG_GENERATION = 4`
- `EXTRACTOR_VERSION = "4.0.0"`
- `AGENT_SCHEMA_VERSION = "4.0.0"`

**`QUARANTINE_CATEGORIES`** extended:
```python
("empty", "low_quality", "language_mismatch", "duplicate_content",
 "schema_invalid", "extraction_error", "js_required", "pdf_truncated",
 "blocked_permanent", "empty_extraction")
```

**`BROWSER_PROFILES`** extended to 8 profiles:
- chrome136, chrome131, chrome142 (Chrome)
- safari184, safari184_ios (Safari)
- firefox135 (Firefox)
- tor145 (Tor)
- edge101 (Edge)

Each with `family` tag for dispatch.

---

### Changed — Global behavior

- **Storage:** all runtime artifacts under `.data/` tree. Root keeps only code and docs.
- **Event loop:** persistent per-process `LoopManager`. No more `asyncio.run()` closing the loop.
- **Noise:** `NoiseSuppressor` silences cffi timer flood at interpreter level.
- **Crawler frontier:** Mercator dual-queue with priority decay.
- **Rate limiting:** health-aware adaptive rate factor per domain.
- **Circuit breaker:** continuous health score replaces boolean open/closed.
- **Extraction:** trafilatura-first fast path (skip fallbacks if ≥ 300 words).
- **Error handling:** every async call wrapped; `CancelledError` caught at every level.
- **API-first routing:** `api_router.has_route(url)` before direct fetch.
- **`_config_hash` cached** with `@lru_cache(maxsize=1)`.
- **`_ZERO_QUALITY` shared dict** for error records.
- **`_DEFAULT_ROUTER` singleton** in `api_router` thread-safe.

---

### Fixed — Complete bug list

**Configuration bugs:**
- `ImportError: cannot import name 'MOS_ENABLED' from 'config'` — added entire MOS block
- `ImportError: cannot import name 'SOD_WORKER_POOL_SIZE'` — added SOD block
- `ImportError: cannot import name 'API_ROUTER_ENABLED'` — added API router block
- `ImportError: cannot import name 'SE_API_ENABLED'` — added SE block
- `ImportError: cannot import name 'MOS_FIRST_HOSTS'` — added

**Spoof bugs:**
- `TypeError: ExtraFingerprints.__init__() got an unexpected keyword argument 'tls_enable_alps'` — removed from `extra_fp`, moved to `CurlOpt.SSL_ENABLE_ALPS`
- Same for `tls_enable_ticket` and `tls_record_size_limit`
- `safari18_4` invalid impersonate target → `safari184`
- Header order assertion failures on random profile → force specific family in test
- `SpoofedSession._last_url` not proxying to worker → property + setter

**Config bugs:**
- `REQUEST_TIMEOUT` tuple vs int in debug harness → debug harness accepts tuple
- `get_tld` called without `fix_protocol=True` → always False

**Crawler bugs:**
- Trap detector missed `jsessionid` at start-of-string → `(?:^|[?&])`
- `_CALENDAR_RE` compiled per-call → compiled at module load
- `_SESSION_ID_RE` missing start-of-string variant → fixed
- `state.completed` stuck at 0 → shared `mp.Value`
- Frontier never drained → `FRONTIER_DRAIN_PER_TICK = 400` inside main loop
- Idle check didn't include frontier → added `frontier_empty`
- `crawl.log` empty → startup and shutdown log lines
- Writer never wrote records → reads `record["word_count"]` not nested path

**Scraper bugs:**
- `KeyError: 'content'` in `extract_xml`, `extract_text_plain`, `extract_pdf` → `_base_record` provides full schema
- `KeyError: 'content'` in `extract_json` → same
- `JSONDecodeError` in `extract_json` for non-JSON bodies → HTML fallback
- `_looks_empty` false positive on 15-byte HTML → reordered checks
- `classify_error` did not handle `result.error` field → added error branch
- `classify_error` did not check `_has_js_markers` before `empty_ssr_body` → reordered
- `_has_js_markers` scanned only 8 KB → extended to 32 KB
- MOS escalation never fired → `escalate` field wired through `_extract_fetch_result`
- `_try_api_router` propagated error dicts → double-check added

**Folder manager bugs:**
- `FileNotFoundError` on `.write_probe` during `multiprocessing.spawn` → PID-suffixed probes
- Bare `except Exception` masked `FileNotFoundError` → explicit catch with `missing_ok=True`
- Module-level `bootstrap()` ran in every spawned child → `_bootstrap_if_parent()` check
- `threading.Lock` didn't protect cross-process → atomic O_EXCL file lock
- Orphan probe files on partial bootstrap → `finally` cleanup
- Windows readonly file deletion failed → `_clear_readonly_tree` before rmtree
- Long path failures → `\\?\` prefix on Windows paths ≥ 240 chars
- Partial bootstrap left stale state → atomic sentinel + `finally` cleanup
- `ensure_writable` raised `NotWritableError` on harmless missing probe → `FileNotFoundError` treated as success

**Error_fast bugs:**
- `asyncio.get_event_loop_policy()` deprecated in Python 3.14 → warning (fix planned)
- cffi timer noise after loop closed → `NoiseSuppressor` intercepts at interpreter level
- `RuntimeError: Event loop is closed` from curl_cffi timers → `LoopManager` keeps loop alive

**Debug harness bugs:**
- `T4 trap detector` expected `2027/12/25` as trap → changed to `2030/12/25`
- `T5 MOS classifier` expected `None` for 15-byte HTML → changed to `empty_ssr_body`
- `test_url` didn't handle 4-tuple return → handles 3 and 4 tuple
- `_classify_key` misattributed blocked records → parses status from error message
- `T3 referer chain` set `_last_url` on facade → property proxy

**Import bugs (chronological):**
1. `from Scraper.config import` — invalid package path → `from config import`
2. NLTK `LookupError: Resource 'punkt_tab' not found` → NLTK entirely removed
3. `TypeError: ExtraFingerprints.__init__() got an unexpected keyword argument` → see spoof bugs
4. `ImportError: cannot import name 'Path' from 'scraper'` → added `from pathlib import Path`
5. `ImportError: cannot import name 'MOS_ENABLED'` → config additions
6. `ImportError: cannot import name 'SOD_WORKER_POOL_SIZE'` → config additions
7. `ImportError: cannot import name 'API_ROUTER_ENABLED'` → config additions
8. `from urllib.parse import urlparse, urljoin, urldefrag` missing in debug.py → added

**Windows-specific bugs:**
- `PermissionError` on readonly file deletion → `_clear_readonly()` before every unlink
- `WinError 2` on race-deleted probe file → `missing_ok=True`
- `WinError 206` on paths > 260 chars → `\\?\` prefix
- `WinError 32/33` on locked files → retry with backoff
- `event loop is closed` during cffi timer callbacks → persistent loop

---

### Removed — Deliberate exclusions

**Dependencies:**
- NLTK (`punkt`, `punkt_tab`, `stopwords` corpora) — dependency weight not justified for pure keyword extraction
- All NLTK auto-download code and lock handling

**Files:**
- `browser_fallback.py` — user rejected headless browser usage ("No... Browsers... No. headless. Browsers... :(")

**Services (account-required):**
- Cloudflare Workers relay — requires account
- Google Apps Script relay — requires Google account
- Deno Deploy / Vercel Edge relay — require accounts
- ScrapingBee — requires API key
- Browserless — requires token
- Jina Reader with API key (keyless path retained)
- Wayback SPN2 with auth
- URLScan submit endpoint (read-only search retained)
- Firecrawl with API key (keyless path retained)

**Infrastructure:**
- Docker / Firecrawl self-hosted (user: "Ignore Docker")
- ScrapingBee (requires key)

**Code:**
- Module-level `FolderManager.bootstrap()` call (moved to explicit parent-only function)
- `_NLTK_LOCK` and NLTK corpus handling
- Static `URLQueue` (replaced by `MercatorFrontier`)
- Static `CircuitBreaker` (replaced by `HostHealth` score)
- `asyncio.run()` direct calls (replaced by `safe_asyncio_run`)

---

### Deprecated

- `asyncio.get_event_loop_policy()` in `error_fast.NoiseSuppressor.install()` — Python 3.14 emits `DeprecationWarning`, slated for removal in 3.16. Will switch to `asyncio.get_running_loop()` detection in v4.1.
- `_CacheDir_LEGACY = ".cache"` and `AGENT_DIR_LEGACY = ".agent"` constants in config — retained for backwards compat only.

---

### Security

- **Cross-process file locking** — atomic `os.open(O_CREAT|O_EXCL|O_WRONLY)` prevents concurrent crawler corruption
- **Corrupt JSON state backup** — moved to `corrupt/` subdirectory before rejection
- **Windows readonly stripping** — `chmod` before every recursive deletion
- **Path traversal detection** — trap detector rejects `..` in paths
- **Long-path prefix** — `\\?\` applied on Windows
- **TLS fingerprint diversity** — 8 browser profiles × 7 impersonates × GREASE × TLS permutation
- **Header randomization** — 7 UAs × 4 locales × 3 encodings × 3 cache-control
- **Domain health scoring** — respects server capacity, reduces rate automatically
- **Quota tracking** — refuses to burn external service quotas

---

### Milestones

| Date | Event | Outcome |
|---|---|---|
| 2026-09-09 | Project start | 4-file crawler design |
| 2026-09-09 | First debug run | 180 failures on `ExtraFingerprints` |
| 2026-09-09 | First successful Wikipedia fetch | Full record with all fields |
| 2026-09-10 | v2.0.0 shipped | CLI, resume, blocked queue, 82 records |
| 2026-09-11 | v3.0.0 MOS | 229/261 tests passing |
| 2026-09-11 | SE API integration | Stack Overflow unblocked |
| 2026-09-11 | 32-method API router plan confirmed | api_router designed |
| 2026-09-12 | v4.0.0 | Folder manager, error_fast, api_router, SOD spoof |

---

### Test results progression

| Run | Pass | Fail | Warn | Empty | Total |
|---|---|---|---|---|---|
| v1 initial | 78 | 180 | 0 | 3 | 261 |
| v1 first fix | 227 | 6 | 17 | 11 | 261 |
| v2 (after fixes) | 229 | 2 | 19 | 10 | 261 |
| v3 (MOS) | 229 | 2 | 19 | 10 | 261 |
| v4 (error_fast) | TBD | TBD | TBD | TBD | ~180 |

**Known unfixable failures:**
- `aljazeera.com` — 15s network timeout (server-side latency)
- `imdb.com`, `binance.com` — hard 202 bot wall (Turnstile)
- `quora.com`, `pinterest.com` — SPA shells with empty SSR

---

## [3.0.0] — 2026-09-11

**Theme:** Mixture Of Services (MOS). Multi-service escalation for blocked URLs.

### Added

**MOS dispatcher** — policy-driven service selection:
- 22 policies covering 500 HTTP error categories
- Weighted scoring: `score = weight × reliability × weight_factor × stickiness / (1 + latency)`
- Hedged request race for slow-error policies

**23 keyless services in registry:**

| Service | Endpoint | Reliability | Latency (p50) |
|---|---|---|---|
| jina_reader | `r.jina.ai/{url}` | 0.95 | 1.8s |
| firecrawl_keyless | `api.firecrawl.dev/v2/scrape` | 0.92 | 2.5s |
| replyfast_md | `md.replyfast.co.uk/api/convert` | 0.90 | 0.6s |
| web2md | `web2md.org/api` | 0.85 | 0.8s |
| microlink | `api.microlink.io` | 0.90 | 1.2s |
| kiprio_readability | `kiprio.com/api/readability` | 0.88 | 1.4s |
| wayback_available | `archive.org/wayback/available` | 0.80 | 0.6s |
| wayback_cdx | `web.archive.org/cdx/search/cdx` | 0.75 | 0.9s |
| commoncrawl_cdx | `index.commoncrawl.org` | 0.70 | 1.1s |
| archive_today | `archive.ph/newest` | 0.65 | 1.3s |
| urlscan_search | `urlscan.io/api/v1/search` | 0.85 | 0.8s |
| corsproxy_io | `corsproxy.io/?` | 0.80 | 0.9s |
| allorigins | `api.allorigins.win/raw` | 0.75 | 1.0s |
| cors_lol | `cors.lol/?` | 0.70 | 1.0s |
| corsfix | `corsfix.com/` | 0.80 | 0.9s |
| killcors | `killcors.com/` | 0.70 | 1.0s |
| ddg_ia | `api.duckduckgo.com` | 0.80 | 0.5s |
| wikipedia_summary | `en.wikipedia.org/api/rest_v1` | 0.95 | 0.4s |
| datamuse | `api.datamuse.com/words` | 0.95 | 0.3s |
| rss2json | `api.rss2json.com/v1/api.json` | 0.90 | 0.8s |

**Budget tracking:**
- Per-service daily quota
- 80% warn → weight × 0.5
- 95% stop → drop from candidates
- Persists to `.data/cache/mos_budget.json`

**Host preference learning:**
- ≥ 3 successes → preference × 1.5
- ≥ 3 failures → preference × 0.3
- 24h TTL
- Persists to `.data/cache/mos_host_prefs.json`

**Response cache:**
- SQLite keyed by `(url_hash, service)`
- 7-day TTL
- Auto-populated on success

**MOS policy table (22 entries):**
- `js_required`, `empty_ssr_body`
- `401_auth`, `403_waf`, `403_geo`, `429_rate`
- `500_transient`, `500_database`, `500_resource_exhaustion`, `500_routing`, `500_tls`, `500_protocol`, `500_app_bug`, `500_cms`, `500_cache`, `500_backend_timeout`, `500_middleware`
- `502_bad_gateway`, `503_unavailable`, `504_timeout`
- `cloudflare_turnstile`, `cloudflare_interstitial`
- `bot_wall_js`, `bot_wall_captcha`

**Error classifier:**
- 13 status-code cases
- 4 error-field cases
- 8 body-pattern cases for 500s

**Verification layer:**
- Wayback availability check
- Common Crawl CDX lookup
- URLScan domain search
- 3 DoH resolvers (Cloudflare, Google, Quad9)

**Enrichment layer:**
- Wikipedia REST summary
- DuckDuckGo Instant Answer
- Datamuse semantic expansion
- kiprio Readability
- Microlink metadata

**Wayback-first host list:**
```python
WAYBACK_FIRST_HOSTS = (
    "x.com", "twitter.com", "facebook.com", "instagram.com",
    "reuters.com", "nytimes.com", "wsj.com",
)
```

### Changed

- Extraction scoring now uses `EXTRACTION_SCORING_ENABLED` with 8 weighted factors
- Chunk deduplication with SimHash Hamming threshold 6
- Entity extraction v2 with frequency filter, reporting-verb proximity, boundary check, first-name dictionary weighting

### Fixed

- `cloudflare_interstitial` classifier for `cf-chl-` bodies
- `_has_js_markers` scanning 32 KB
- Blocked hosts route to MOS via `classify_error`

---

## [2.0.0] — 2026-09-10

**Theme:** CLI, resume, blocked queue, queue cap.

### Added

**CLI flags:**
- `--link` (repeatable seed URLs)
- `--inf` (infinite mode)
- `--fast` (max concurrency, no jitter)
- `--antiblock` (retry blocked URLs)
- `--depth N`
- `--workers N`
- `--queue-cap N`
- `--out PATH`
- `--sitemap URL`

**`queue.txt`** — TSV format:
```
url\tdepth\tpriority
```
- Comment lines start with `#`
- Atomic rewrite via `.tmp` + `os.replace`

**Resume logic:**
1. Load `crawl.state.json`
2. Load `done.txt` via `mmap` into set
3. Load `queue.txt` filtering done URLs
4. Replay `journal.ndjson`
5. Filter seeds through dedup
6. Bootstrap

**Blocked queue:**
- 50–80s randomized retry (`random.uniform(50.0, 80.0)`)
- `MAX_BLOCKED_RETRIES = 5`
- 1.5× exponential backoff multiplier

**Blocked detection:**
- Status codes: 403, 408, 429, 503, 520, 521, 522, 523, 524
- Body markers: `cf-chl-`, `just a moment`, `cloudflare`, `attention required`, `checking your browser`, `ddos protection`, `access denied`, `ray id`, `turnstile`, `g-recaptcha`, `h-captcha`

**Adaptive rate limiter:**
- Per-domain token bucket
- 429 → rate × 0.5 (floor 0.5 req/s)
- 100 consecutive 2xx → rate × 1.1 (ceiling 20 req/s)
- Persists to `.data/cache/domain_rates.json`

**Adaptive backoff:**
- Base 1.5, max 300s
- Exponential on consecutive failures

**Circuit breaker:**
- 5 failures opens for 60s
- Half-open state after timeout

**Dead letter queue:**
- Writes to `.cache/dead_letter.jsonl`
- Records URL, error, attempts, timestamp

**Trap detector:**
- Repeating path segments (≥ 4 repetitions)
- Calendar traps (year > current + 2)
- Session IDs in query: `jsessionid`, `phpsessid`, `aspsessionid`, `sid`, `sessionid`
- Hex tokens ≥ 32 chars
- Query param explosion (> 30 params)
- URLs > 2000 chars
- Path traversal (`..`)

**Change detector:**
- ETag tracking
- Last-Modified tracking
- Per-host change rate as exponential moving average

**Mercator frontier:**
- 8 front bands
- Band weights: `(16, 8, 4, 2, 1, 1, 1, 1)`
- Per-host back queues

**Cross-domain TLD+1 filter** via `get_tld(fix_protocol=True)`

**`--clean` CLI flag** — tier granularity: `all`, `state`, `db`, `cache`, `logs`, `agent`, `output`, `shards`, `quarantine`, `cookies`, `tmp`, `legacy`

### Changed

- `MAX_QUEUE_SIZE = 500` enforced on both in-memory and on-disk queue
- Frontier uses heap ordering by `(priority, depth, counter)`

### Fixed

- Frontier never drained from `link_q` into `task_q`
- Trap detector missed start-of-string `jsessionid`
- `get_tld` called without `fix_protocol=True`

---

## [1.0.0] — 2026-09-09

**Theme:** Initial release. Four-file universal crawler.

### Added

**`scraper.py`** — fetch, extract, chunk:
- `SpoofedSession.get()` for HTTP
- Content-type detection and dispatch
- Multi-stage extraction pipeline
- Structured extraction (JSON-LD, OG, canonical, microdata)
- NLP-lite (keywords, entities, summary, PII redaction)
- Sentence-based chunking with token window and overlap
- SimHash and MinHash dedup
- PDF extraction with PyMuPDF and OCR fallback
- XML/RSS/sitemap parsing with `defusedxml`

**`crawler.py`** — orchestration:
- Multiprocessing worker pool
- Dedup store with Bloom filter
- Sharded NDJSON writer
- Quarantine writer
- Manifest writer
- RSS watchdog via `psutil`
- Cache flusher (`ipconfig /flushdns` on Windows, `drop_caches` on Linux)
- Temp cleaner

**`spoof.py`** — 9-layer spoofing:
1. TLS/JA3 via `impersonate`
2. HTTP/2 fingerprint
3. Header order
4. GREASE values
5. User-Agent rotation
6. Accept-Language rotation
7. Referer chain
8. Timing jitter
9. Cookie/session persistence

**`config.py`** — 300+ tunables in 20 sections

**`debug.py`** — initial harness with 11 tiers

**Extraction pipeline:**
- `trafilatura.bare_extraction` → justext → selectolax paragraph walk
- Extraction scoring with 8 weighted factors
- Trafilatura-first fast path

**Structured data extraction:**
- JSON-LD `<script type="application/ld+json">`
- OpenGraph meta tags
- Twitter Card meta tags
- Canonical URL `<link rel="canonical">`
- Microdata

**NLP-lite:**
- TF-IDF keywords with bigram/trigram boost
- Topic extraction (multi-word phrases)
- Regex entity extraction (9 types: EMAIL, URL, MONEY, PERCENT, DATE, YEAR, PHONE, PERSON, ORG)
- Extractive sentence-frequency summary
- PII redaction (email, phone, SSN, credit card, IP)

**Chunking:**
- Sentence-based with token window (default 512 tokens)
- Overlap (default 64 tokens)
- Min size (default 32 tokens)
- Heading context attachment

**PDF extraction:**
- `pymupdf.open()` for native text
- `page.get_textpage_ocr()` for OCR fallback (only when < 50 chars extractable)
- `get_text("blocks")` for paragraph reconstruction

**XML parsing:**
- `defusedxml.ElementTree.fromstring` primary
- `lxml.etree.fromstring` fallback
- RSS/Atom/sitemap specific extractors

**Content-type detection:**
- Magic bytes + Content-Type header
- 6 kinds: `pdf`, `json`, `xml`, `html`, `text`, `unknown`

**Block detection:**
- Status codes from `BLOCKED_STATUS_CODES`
- Body markers from `BLOCKED_BODY_MARKERS`

**Windows and Linux support:**
- Cache flushing (`ipconfig /flushdns` vs `drop_caches`)
- Temp directory cleanup
- Process killing (`taskkill` vs `os.kill`)
- Read-only bit stripping

---

## Versioning scheme

`MAJOR.MINOR.PATCH`

- **MAJOR** — breaking config, state file format, or on-disk layout. Requires `--force-resume` to continue from previous state.
- **MINOR** — new features, new services, new detectors. Backward compatible.
- **PATCH** — bug fixes, minor tuning. State file compatible.

State files carry `config_version` and `config_generation`. Resume refuses when versions differ unless `--force-resume` is passed.

---

## Current file inventory

```
Scraper/
├── scraper.py              ~3000 lines  fetch + extract + chunk
├── crawler.py              ~2000 lines  orchestration + multiprocessing
├── spoof.py                ~800 lines   23-layer spoofing + SOD pool
├── api_router.py           ~1900 lines  32-method API discovery
├── se_api.py               ~1200 lines  Stack Exchange API client
├── error_fast.py           ~430 lines   error classification + noise suppression
├── folder_manager.py       ~470 lines   centralized path management
├── config.py               ~1400 lines  300+ tunables
├── debug.py                ~2300 lines  180-test harness
├── libraries.txt           dependency list
├── expectederrors.txt      500 HTTP error categories
├── resultsexample.json     reference output schema
├── CHANGELOG.md            this file
└── .data/                  runtime data tree
    ├── state/              crawl.state.json, queue.txt, done.txt, blocked.txt, etc.
    ├── db/                 dedup.sqlite, bloom.bin, mos_cache.sqlite, extraction.sqlite
    ├── cache/              domain_rates.json, mos_budget.json, mos_host_prefs.json, etc.
    ├── logs/               crawl.log
    ├── agent/              embeddings.bin, entities.jsonl, topics.jsonl
    ├── output/             manifest.json, shards/, quarantine/
    ├── cookies/            per-domain cookie jars
    └── tmp/                scratch space
```

---

## Test result progression

| Run | Date | Pass | Fail | Warn | Empty | Total | Notes |
|---|---|---|---|---|---|---|---|
| Initial | 09-09 | 78 | 180 | 0 | 3 | 261 | `ExtraFingerprints` crash |
| Fix 1 | 09-10 | 227 | 6 | 17 | 11 | 261 | Config additions |
| Fix 2 | 09-10 | 229 | 2 | 19 | 10 | 261 | Trap + classifier fixes |
| MOS | 09-11 | 229 | 2 | 19 | 10 | 261 | MOS escalation |
| v4 | 09-12 | TBD | TBD | TBD | TBD | ~180 | error_fast integration |

### Known unfixable failures

| URL | Status | Reason |
|---|---|---|
| `aljazeera.com` | Timeout | Server-side latency > 15s |
| `imdb.com` | 202 blocked | Turnstile challenge |
| `binance.com` | 202 blocked | Turnstile challenge |
| `quora.com` | EMPTY | SPA shell, no SSR |
| `pinterest.com` | EMPTY | SPA shell, no SSR |
| `reddit.com/r/python` | EMPTY | SPA shell (Reddit JSON path not wired) |

---

## Dependency changes

### Added (beyond `libraries.txt`)
- `psutil` — process memory/CPU/RSS monitoring

### Removed
- `nltk` — never used for actual functionality, only keyword extraction. Pure regex is sufficient.
- `browser_fallback` — user rejected headless browser usage.

### Considered but rejected
- `patchright`, `nodriver`, `camoufox` — headless browsers. User: "No... Browsers... No. headless. Browsers... :("
- Account-based services (Cloudflare Workers, Google Apps Script, ScrapingBee, Browserless)
- Docker (user: "Ignore Docker")

---

## Architectural decisions

| Decision | Rationale |
|---|---|
| Multiprocessing over threading | curl_cffi CFFI calls release GIL but session state is not thread-safe. Process isolation guarantees safety. |
| `mp.set_start_method("spawn", force=True)` | Windows requires spawn. Linux defaults to fork which breaks CFFI. |
| Persistent asyncio loop | curl_cffi's `AsyncSession` schedules timer callbacks that outlive the coroutine. `asyncio.run()` closes the loop prematurely. |
| SQLite for dedup | Faster than flat files for lookups. WAL mode for concurrent reads. Bloom filter as fast pre-filter. |
| `orjson` over stdlib `json` | 10–14× faster serialization. |
| `selectolax.lexbor` over BeautifulSoup | 12–17× faster parsing. |
| `blake2b` over `sha256` | Faster, adjustable digest size, keyed mode available. |
| PID-suffixed probe files | Multiprocessing spawn race. Each process writes its own. |
| Atomic sentinel + finally cleanup | Partial bootstrap failures leave no state. |
| `\\?\` prefix on Windows | Bypass MAX_PATH 260 limit. |
| `missing_ok=True` on unlink | Other processes may have already cleaned up. |
| Module-level `install_all()` for error_fast | Suppressors must be installed before any asyncio code runs. |
| `@lru_cache(maxsize=1)` on `_config_hash` | Called once per record; caching is huge win. |

---

## Unreleased / planned for 4.1.0

- Wire `AdaptiveConcurrency` into main loop with `mp.Value` shared worker count
- Fix `asyncio.get_event_loop_policy()` deprecation warning
- Per-site extractors for high-value domains (news, docs, forums)
- Vector embedding attachment for RAG-ready chunks
- Semantic dedup via a small local embedding model
- Wayback SPN2 archival pre-flight for URLs that fail all MOS paths

### Wanted but rejected
- Tor circuit rotation (requires Tor daemon)
- Headless browser fallback (user rejected)
- Account-based API paths (user rejected)

---

## Credits

Built by AboSmrh with iterative development across 4 major versions.

Technologies used:
- `curl_cffi` — TLS/HTTP fingerprint impersonation
- `selectolax` — fast HTML parsing
- `trafilatura` — robust article extraction
- `justext` — boilerplate removal
- `lxml`, `lxml_html_clean` — XML/HTML processing
- `pymupdf` — PDF text and OCR
- `textstat` — readability metrics
- `regex`, `pyphen`, `tld`, `courlan` — text utilities
- `babel`, `tzlocal`, `dateparser`, `htmldate`, `python-dateutil` — dates and locales
- `defusedxml` — safe XML
- `orjson` — fast JSON
- `psutil` — process monitoring
- `click`, `tqdm`, `colorama` — CLI
- `joblib`, `cloudpickle` — parallel processing
- `nltk`, `numpy`, `chardet` — removed or unused
- `pip`, `setuptools` — tooling

---