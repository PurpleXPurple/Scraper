# USAGE

Complete usage guide for the NEXUS universal crawler.

---

## Requirements

- Python 3.14+ (tested on 3.14.7)
- Windows 10/11 or Linux/macOS
- ~200 MB free disk for typical runs
- Libraries from `libraries.txt` plus `psutil`

---

## Install

```powershell
cd (Current Project Location OR Import It)
pip install -r libraries.txt
pip install psutil
```

That's it. No accounts, no API keys, no Docker.

---

## Quick start

```powershell
python scraper.py --link "https://en.wikipedia.org/wiki/Online_streamer" --depth 2 --workers 4
```

Runs until the frontier is empty or you press Ctrl-C. Output lands in `.data/output/shards/`.

---

## `scraper.py` — main entrypoint

### Flags

| Flag | Type | Default | Purpose |
|---|---|---|---|
| `--link URL` | repeatable | — | Seed URL. Use multiple times for multi-seed. |
| `--sitemap URL` | string | — | Fetch sitemap.xml and use all `<loc>` entries as seeds. |
| `--depth N` | int | `4` | Maximum crawl depth from seed. `0` = seeds only. |
| `--workers N` | int | CPU count | Worker processes. |
| `--queue-cap N` | int | `500` | Frontier cap. Recommended 5000+ for large sites. |
| `--out PATH` | string | `.data/output/output.ndjson` | Flat output path when sharding disabled. |
| `--fast` | flag | — | Max concurrency, no jitter. Uses `MAX_WORKERS_FAST_MULT × workers`. |
| `--inf` | flag | — | Infinite mode. Never auto-stops on idle. |
| `--antiblock` | flag | — | Retry blocked URLs via blocked queue. |
| `--verify` | flag | — | Run verification (Wayback, Common Crawl, URLScan, DoH) on each record. |
| `--enrich` | flag | — | Run enrichment (Wikipedia, DDG, Datamuse, kiprio, Microlink). |
| `--clean TIER` | choice | — | Wipe a data tier before starting. |
| `--dry-run` | flag | — | With `--clean`, show what would be removed without removing. |
| `--preload-only` | flag | — | Run the preloader and exit. Verifies deps are warm. |
| `--no-preload` | flag | — | Skip the preloader (not recommended). |
| `--api URL` | string | — | API mode: fetch a JSON endpoint and write raw response. |
| `--pagination MODE` | choice | `auto` | `auto`, `cursor`, `page`, `next`, `link`, `none`. |
| `--params JSON` | string | `{}` | Query params for `--api` mode. |
| `--max-pages N` | int | `1000` | Max pages to fetch in API mode. |

### `--clean` tiers

| Tier | Wipes |
|---|---|
| `all` | every tier, then re-bootstraps |
| `state` | `crawl.state.json`, `queue.txt`, `done.txt`, `errors.txt`, `blocked.txt`, `journal.ndjson`, `crawl.pid`, `crawl.lock` |
| `db` | `dedup.sqlite`, `bloom.bin`, `mos_cache.sqlite`, `extraction.sqlite`, `api_router_cache.sqlite` |
| `cache` | `domain_rates.json`, `mos_budget.json`, `mos_host_prefs.json`, `dead_letter.jsonl`, `error_fast.json`, `se_quota.json`, `se_breaker.json`, `se_stats.json`, `api_router_budget.json`, `apis_guru_list.json`, cookies, bootstrap cache |
| `logs` | `crawl.log` |
| `agent` | `embeddings.bin`, `entities.jsonl`, `topics.jsonl` |
| `output` | `manifest.json`, `output.ndjson` |
| `shards` | `.data/output/shards/*` |
| `quarantine` | `.data/output/quarantine/*` |
| `cookies` | per-domain cookie jars |
| `tmp` | scratch space |
| `legacy` | migrates root-level files into `.data/` |

### Common recipes

**Single domain, moderate depth:**
```powershell
python scraper.py --link "https://en.wikipedia.org/wiki/Online_streamer" --depth 3 --workers 8
```

**Multi-seed with cap:**
```powershell
python scraper.py `
  --link "https://stackoverflow.com/questions/4260280" `
  --link "https://en.wikipedia.org/wiki/HTTP" `
  --link "https://news.ycombinator.com/" `
  --depth 1 --workers 6 --queue-cap 5000
```

**Fresh start every time:**
```powershell
python scraper.py --link "https://site.com/" --clean all --depth 2 --workers 4
```

**Preview a clean without wiping:**
```powershell
python scraper.py --clean output --dry-run
```

**Sitemap-driven crawl:**
```powershell
python scraper.py --sitemap "https://site.com/sitemap.xml" --depth 1 --workers 8
```

**API mode:**
```powershell
python scraper.py --api "https://api.github.com/repos/torvalds/linux" --out linux.json
```

**Verify preload only:**
```powershell
python scraper.py --preload-only
```

---

## `debug.py` — test harness

### Flags

| Flag | Type | Default | Purpose |
|---|---|---|---|
| `--categories T0 T1 ...` | list | all | Only run these test categories. |
| `--name SUBSTRING` | string | — | Only run tests whose name contains substring. |
| `--list` | flag | — | List all categories and test counts, then exit. |
| `--quiet` | flag | — | Suppress per-test console output. |
| `--verbose` | flag | — | Extra detail. |
| `--log-level LEVEL` | choice | `INFO` | `TRACE`, `DEBUG`, `INFO`, `PASS`, `WARN`, `FAIL`, `ERROR`. |
| `--log-file PATH` | string | — | Write structured JSON logs to this file. |
| `--no-console-logs` | flag | — | Disable per-logger console output. |

### Test categories

| Category | Count | Covers |
|---|---|---|
| T0 | 3 | Environment, cleanup, folder manager bootstrap |
| T1 | 7 | Imports for every module |
| T2 | 15 | Config invariants |
| T3 | 10 | Spoof engine, SOD pool |
| T4 | 17 | Crawler internals (bloom, simhash, frontier, health, yield, bootstrap, DLQ, change, traps) |
| T5 | 25 | Scraper internals (regex, extraction, chunking, NLP, classifier) |
| T5b | 11 | Folder manager (diagnostics, error categories, retries, JSON, locks) |
| T5c | 5 | SE API (parsers, quota, stats) |
| T5d | 4 | API router (hardware, tuner, has_route, budget) |
| T6_easy | 10 | example.com, httpbin, iana, rust, python, go, nodejs |
| T7_moderate | 10 | Postgres, Redis, SQLite, Rust docs, Wikipedia, HN |
| T8_dynamic | 10 | GitHub, Stack Overflow, Ars, Verge, BBC, Wired, Guardian, dev.to |
| T9_js_heavy | 8 | Reddit, NYT, WaPo, Facebook, LinkedIn, YouTube, Twitch, Discord |
| T10_protected | 4 | Coinbase, Crunchbase, Glassdoor, Zillow |
| T13_docs | 8 | Python docs, MDN, git, ArchWiki, man7, Rust std, Docker, K8s |
| T14_blogs | 8 | Fowler, PG, Rust blog, overreacted, jvns, Joel, Cloudflare, Stripe |
| T15_news | 7 | AP, NPR, DW, France24, CBC, ABC AU, SCMP |
| T17_academic | 6 | arXiv, PubMed, Nature, Science, PLOS, Frontiers |
| T18_gov_edu | 7 | NASA, NOAA, CDC, Harvard, MIT, Stanford, Oxford |
| T26_se_network | 6 | Full SE question fetches via API |
| T41 | 3 | Concurrency (bloom, logger, JSON) |
| T42 | 5 | Stress (extraction loop, chunk, simhash, logger, trap) |
| T43 | 7 | Regression (6 fixes + base_record) |

### Common recipes

**List categories:**
```powershell
python debug.py --list
```

**System tests only (fast):**
```powershell
python debug.py --categories T0 T1 T2 T3 T4 T5 T5b T5c T5d --no-console-logs
```

**Concurrency + stress:**
```powershell
python debug.py --categories T41 T42 T43
```

**Easy URLs only:**
```powershell
python debug.py --categories T6_easy
```

**SE network test:**
```powershell
python debug.py --categories T5c T26_se_network
```

**Full run with structured log:**
```powershell
python debug.py --log-file .data/logs/debug.json
```

**Filter by name:**
```powershell
python debug.py --name "MOS classifier"
```

### Reading the output

Console uses color-coded status tags:

- `[PASS]` green
- `[FAIL]` red
- `[WARN]` yellow — blocked by anti-bot, not a code bug
- `[EMPT]` orange — got HTML but too few words
- `[SLOW]` yellow — elapsed > 20s
- `[SKIP]` gray — not applicable
- `[ERRO]` red — unhandled exception

Structured report at `debug_report.json`:
```json
{
  "run_meta": { "started_at", "elapsed", "rss_mb", "python", "platform",
                "cpu_count", "mem_total_gb", "disk_free_gb" },
  "summary": { "PASS": N, "FAIL": N, ... },
  "results": [ { category, name, status, detail, elapsed_ms, rss_mb, cpu_pct,
                 extra, traceback } ]
}
```

---

## `error_fast.py` — error handling

### Flags

| Flag | Purpose |
|---|---|
| `--report` | Print full stats (noise suppressor, loop manager, error registry). |
| `--save` | Dump stats to `.data/cache/error_fast.json`. |
| `--test` | Run 4 self-tests: cffi timer noise, cancelled, safe_run, fast_catch. |
| `--classify "message"` | Classify an arbitrary error message. |

### Common recipes

```powershell
python error_fast.py --test
python error_fast.py --report
python error_fast.py --save
python error_fast.py --classify "Event loop is closed"
python error_fast.py --classify "SSL: CERTIFICATE_VERIFY_FAILED"
python error_fast.py --classify "Connection reset by peer"
python error_fast.py --classify "429 Too Many Requests"
python error_fast.py --classify "jsondecode: Expecting value"
```

### Python API

```python
from error_fast import install_all, safe_asyncio_run, fast_catch, Kind, Recovery

install_all()  # runs once at import in scraper.py, no-op here

async def my_coro():
    return 42

result = safe_asyncio_run(my_coro())  # persistent loop, no closed-loop crash

@fast_catch(default=None)
def risky():
    raise RuntimeError("Event loop is closed")

value = risky()  # returns None, logged to ErrorFast registry
```

Context managers:
```python
from error_fast import swallow, retry, Kind

with swallow(Kind.CONNECTION):
    risky_network_call()

with retry(times=3, delay=0.5, backoff=2.0):
    flaky_operation()
```

---

## `api_router.py` — API discovery

### Flags

| Flag | Purpose |
|---|---|
| `--probe URL` | Run the full 32-detector chain on a URL. |
| `--show-hardware` | Print detected hardware profile and tuner settings. |
| `--show-diagnostics` | Run folder manager diagnostics. |
| `--show-cache` | Print cache row counts. |

### Common recipes

```powershell
python api_router.py --show-hardware
python api_router.py --probe https://stripe.com/
python api_router.py --probe https://github.com/torvalds/linux
python api_router.py --show-cache
```

`--probe` output is JSON:
```json
{
  "url": "...",
  "host": "...",
  "api_type": "openapi",
  "endpoint": "...",
  "spec_url": "...",
  "spec_format": "json",
  "detector": "m13_openapi_paths",
  "confidence": 0.95,
  "metadata": { ... }
}
```

---

## `se_api.py` — Stack Exchange client

### CLI

```powershell
python -c "from se_api import se_fetch_url_sync; rec, err = se_fetch_url_sync('https://stackoverflow.com/questions/4260280'); print('error:', err); print('words:', rec.get('word_count') if rec else 0)"
```

### Python API

```python
from se_api import (
    se_site_for_url, se_parse_question_id, se_parse_tag,
    se_fetch_url, se_fetch_url_sync,
    se_fetch_question, se_fetch_answers, se_fetch_comments,
    se_fetch_related, se_fetch_search, se_fetch_tag,
    se_stats, se_quota_status, se_save,
)
import asyncio

# Sync
rec, err = se_fetch_url_sync("https://stackoverflow.com/questions/4260280")

# Async
rec, err = asyncio.run(se_fetch_url("https://stackoverflow.com/questions/4260280"))

# Diagnostics
print(se_stats())
print(se_quota_status())
se_save()
```

---

## Configuration

All tunables live in `config.py`. Edit the file directly.

### Sections

| Section | Purpose |
|---|---|
| RUNTIME | Version, platform detection |
| CONCURRENCY / WORKERS | Worker count, RSS limits, domain rate |
| NETWORK | Timeouts, jitter, redirects, retries |
| SPOOF / FINGERPRINT | TLS, HTTP/2, header order |
| SOD | Worker pool size, recycle, stickiness |
| CRAWL CONTROL | Depth, links per page, queue cap |
| BLOCKED / ANTIBLOCK | Retry windows, status codes, body markers |
| DEDUP | Bloom bits, SimHash Hamming, MinHash Jaccard |
| EXTRACTION / QUALITY | OCR, PDF caps, word count, readability thresholds |
| EXTRACTION SCORING | Weighted scoring factors |
| CHUNKING | Token window, overlap, dedup |
| SUMMARY | Top sentences count |
| ENTITIES V2 | Frequency filters, reporting verbs, first names |
| TOPICS | N-gram max, min score |
| KEYWORDS | Algorithm, per-doc cap |
| LANGUAGE DETECTION | Allowlist, detector order |
| PII REDACTION | Per-type toggles |
| AGENT OUTPUT SCHEMA | Field list, include flags |
| PROVENANCE | Request/response header hashing |
| EXTRACTION CACHE | SQLite TTL, validation |
| FAILURE CATEGORIES / QUARANTINE | Per-category routing |
| STORAGE PATHS | Derived from `FolderManager` |
| AGENT MANIFEST | Write interval, counts, shards |
| AGENT SHARDING | Size thresholds, naming |
| AGENT FILTERING | Min/max tokens, blocked domains |
| SEEDS | Default seed list |
| BROWSER PROFILES | 8 profiles across 5 browser families |
| LOGGING | Level, rotation, targets |
| TELEMETRY | Optional stats emitter |
| AUDIT | Post-run audit flags |
| MOS | Mixture Of Services policies and budgets |
| VERIFICATION | Wayback, Common Crawl, URLScan, DoH |
| ENRICHMENT | Wikipedia, DDG, Datamuse, kiprio, Microlink |
| WAYBACK-FIRST | Host list for preemptive archive |
| FREE PROXIES | Optional free proxy list sources |
| API ROUTER | Enabled, timeouts, caps |
| STACK EXCHANGE API | Key, max answers, route-before-direct |
| BROWSER FALLBACK | Disabled by design |

### Common tweaks

**Lower memory ceiling:**
```python
MAX_RSS_MB = 500
```

**Higher crawl throughput:**
```python
MAX_WORKERS = 16
MAX_WORKERS_FAST_MULT = 3
DOMAIN_TOKEN_BUCKET_RATE = 10.0
```

**Skip low-quality pages:**
```python
QUALITY_MIN_WORDS = 100
QUALITY_MIN_FLESCH = 30.0
```

**Smaller chunks for RAG:**
```python
AGENT_CHUNK_SIZE_TOKENS = 256
AGENT_CHUNK_OVERLAP_TOKENS = 32
```

**Enable strict language filtering:**
```python
LANGUAGE_FILTER_ENABLED = True
LANGUAGE_ALLOWLIST = ["en", "de", "fr"]
```

**Enable PII redaction:**
```python
AGENT_PII_REDACT_ENABLED = True
AGENT_PII_REDACT_EMAIL = True
AGENT_PII_REDACT_PHONE = True
```

---

## Output

### Directory layout

```
.data/
├── state/          resume state
├── db/             dedup + caches (SQLite)
├── cache/          JSON caches and budgets
├── logs/           crawl.log
├── agent/          embeddings, entities, topics
├── output/
│   ├── manifest.json
│   ├── shards/     shard-00000.ndjson, shard-00001.ndjson, ...
│   └── quarantine/ empty.ndjson, low_quality.ndjson, js_required.ndjson, ...
├── cookies/        per-domain cookie jars
└── tmp/            scratch
```

### Record schema

Every record in `shard-XXXXX.ndjson` is one line of JSON matching this structure:

```json
{
  "id": "content_hash",
  "url": "https://...",
  "canonical_url": "https://...",
  "domain": "example.com",
  "tld": "com",
  "title": "Page Title",
  "language": "en",
  "published_date": "2024-01-15",
  "updated_date": "2024-03-20",
  "crawled_at": 1789219800.123,
  "content_hash": "blake2b-16hex",
  "simhash": 1234567890,
  "source_signature": "8hex",
  "idempotency_key": "16hex",
  "extractor_version": "4.0.0",
  "config_hash": "32hex",
  "license": "CC BY-SA 4.0",
  "quality": { "word_count": 659, "flesch_reading_ease": 40.98, ... },
  "word_count": 659,
  "token_count": 907,
  "char_count": 4578,
  "sentence_count": 35,
  "reading_time_seconds": 197.7,
  "flesch_reading_ease": 40.98,
  "flesch_kincaid_grade": 12.21,
  "gunning_fog": 14.45,
  "smog_index": 13.70,
  "automated_readability_index": 15.86,
  "coleman_liau_index": 15.71,
  "dale_chall_score": 11.75,
  "text_standard": "11th and 12th grade",
  "difficulty": 188,
  "topics": [ {"term": "...", "score": 0.05} ],
  "entities": [ {"type": "PERSON", "value": "...", "weight": 1.0} ],
  "keywords": [ {"term": "...", "score": 0.03} ],
  "summary": "Extractive summary text...",
  "sections": [ {"heading": "...", "text": "...", "subsections": []} ],
  "chunks": [ {"index": 0, "total": 2, "text": "...", "token_count": 510,
                "heading_context": "...", "parent_url": "...",
                "parent_title": "..."} ],
  "links": [ "https://..." ],
  "metadata": { "source_type": "html", "language": "en", ... },
  "provenance": { "service": "direct", ... },
  "content": {
    "site_navigation": { "primary": [], "help": [], "actions": [] },
    "announcement": null,
    "table_of_contents": [],
    "article": { "heading": "", "intro": "", "sections": [], "references": [] },
    "metadata": {},
    "footer_links": []
  },
  "schema_version": "4.0.0",
  "kind": "html"
}
```

`kind` values: `html`, `pdf`, `json`, `xml`, `text`, `se_api`, `direct_handler`, `api_discovered`, `reddit_json`, `github_api`, `crossref_api`, `arxiv_api`, `pubmed_eutils`, `binance_api`, `wiktionary_api`, `openlibrary_api`, `free_dictionary_api`.

### Manifest

`.data/output/manifest.json`:
```json
{
  "schema_version": "4.0.0",
  "config_version": "4.0.0",
  "config_generation": 4,
  "config_hash": "32hex",
  "generated_at": 1789219800.123,
  "state": { "generation", "started_at", "enqueued", "completed", "failed",
              "dup", "blocked", "quarantined", "traps_detected",
              "circuit_opened", "api_routed" },
  "telemetry": null,
  "shards": { ".data\\output\\shards\\shard-00000.ndjson": 42 },
  "categories": { "empty": 1, "low_quality": 3 }
}
```

---

## Inspecting output

### PowerShell

**Count records:**
```powershell
(Get-Content .data\output\shards\shard-00000.ndjson).Count
```

**Read one record:**
```powershell
$r = Get-Content .data\output\shards\shard-00000.ndjson -TotalCount 1 | ConvertFrom-Json
$r.title
$r.word_count
$r.chunks.Count
$r.entities.Count
```

**Read multiple records:**
```powershell
$lines = Get-Content .data\output\shards\shard-00000.ndjson
foreach ($line in $lines[0..4]) {
    $r = $line | ConvertFrom-Json
    "---"
    "kind:  $($r.kind)"
    "title: $($r.title)"
    "words: $($r.word_count)"
    "chunks:$($r.chunks.Count)"
    "kw:    $($r.keywords.Count)"
}
```

**State:**
```powershell
$s = Get-Content .data\state\crawl.state.json | ConvertFrom-Json
"completed: $($s.completed)"
"enqueued:  $($s.enqueued)"
"dup:       $($s.dup)"
"written:   $($s.records_written)"
"dropped:   $($s.queue_dropped)"
```

**Manifest:**
```powershell
Get-Content .data\output\manifest.json | ConvertFrom-Json | Format-List
```

**Folder summary:**
```powershell
python -c "from folder_manager import FolderManager; print(FolderManager.summarize())"
```

**Diagnostics:**
```powershell
python -c "from folder_manager import FolderManager; print(FolderManager.diagnose()['summary'])"
```

### Linux / macOS

**Count:**
```bash
wc -l .data/output/shards/shard-00000.ndjson
```

**Read:**
```bash
head -1 .data/output/shards/shard-00000.ndjson | python -m json.tool
```

**jq filter:**
```bash
jq -r 'select(.word_count > 500) | "\(.word_count) \(.title)"' .data/output/shards/shard-00000.ndjson
```

---

## Maintenance

### Rotate logs

```powershell
python -c "from folder_manager import FolderManager; print(FolderManager.rotate_logs(keep=5))"
```

### Rotate shards older than 30 days

```powershell
python -c "from folder_manager import FolderManager; print(FolderManager.rotate_shards(keep_days=30))"
```

### Sweep temp files

```powershell
python -c "from folder_manager import FolderManager; print(FolderManager.sweep_tmp(max_age_hours=12))"
```

### Migrate legacy root files

```powershell
python scraper.py --clean legacy
```

### Full reset

```powershell
python scraper.py --clean all
```

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'X'`

Run:
```powershell
pip install -r libraries.txt
pip install psutil
```

### `PermissionError` on file deletion (Windows)

The file is locked by another process. Close any editor or Excel previews and retry. `FolderManager.safe_remove` retries 4× with exponential backoff and strips the readonly bit.

### `Event loop is closed` flood

Should not appear. `error_fast.NoiseSuppressor` silences it. If it does, run:
```powershell
python error_fast.py --test
```

to verify suppressors install correctly.

### `Exception ignored from cffi callback`

Same fix. `error_fast.NoiseSuppressor` handles it.

### Crawl never finishes

Check `.data/state/crawl.state.json` for `queue_dropped`. If it's high, raise `MAX_QUEUE_SIZE`. If it's zero and `completed` is stuck at zero, workers are blocked. Check `.data/logs/crawl.log`.

### High memory

Lower `MAX_RSS_MB` in config. The monitor kills workers exceeding it.

### Sites consistently blocked

Add to `MOS_FIRST_HOSTS` in config:
```python
MOS_FIRST_HOSTS = (..., "yourhost.com",)
```

That bypasses direct fetch and routes straight through MOS.

### SE quota exhausted

Check:
```powershell
python -c "from se_api import se_quota_status; print(se_quota_status())"
```

Wait until UTC midnight for daily reset, or register a free Stack Apps key and set `SE_API_KEY` in config.

### Turnstile-blocked sites

`imdb.com`, `binance.com`, `quora.com`, `pinterest.com` — hard Turnstile challenges with no keyless bypass. They route to MOS, which tries all 22 services and gives up. Correct behavior.

---

## Full workflow example

```powershell
# 1. Clean slate
python scraper.py --clean all

# 2. Verify preload
python scraper.py --preload-only

# 3. Run a real crawl
python scraper.py `
  --link "https://en.wikipedia.org/wiki/Online_streamer" `
  --link "https://stackoverflow.com/questions/4260280" `
  --link "https://news.ycombinator.com/" `
  --depth 2 --workers 8 --queue-cap 5000

# 4. Inspect output
(Get-Content .data\output\shards\shard-00000.ndjson).Count

$s = Get-Content .data\state\crawl.state.json | ConvertFrom-Json
"completed: $($s.completed)  dup: $($s.dup)  written: $($s.records_written)"

python -c "from folder_manager import FolderManager; print(FolderManager.summarize())"

# 5. Run diagnostics
python -c "from se_api import se_stats, se_quota_status; import json; print(json.dumps({'stats': se_stats(), 'quota': se_quota_status()}, indent=2))"
python error_fast.py --report

# 6. Run full debug if anything looks off
python debug.py --log-file .data/logs/debug.json
```

---

## Automated test harness

Save as `run_tests.ps1`:

```powershell
$ErrorActionPreference = 'Continue'
"=== NEXUS TEST SESSION START $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz') ===" | Out-File debugshit.txt -Encoding utf8 -Force
& {
    python error_fast.py --test
    python error_fast.py --report
    python error_fast.py --classify "Event loop is closed"
    python error_fast.py --classify "SSL: CERTIFICATE_VERIFY_FAILED"
    python -c "import config, folder_manager, error_fast, spoof, crawler, se_api, api_router, scraper; print('ALL_IMPORTS_OK')"
    python -c "from folder_manager import FolderManager; FolderManager.bootstrap(force=True); print(FolderManager.diagnose()['summary'])"
    python scraper.py --preload-only
    python debug.py --categories T0 T1 T2 T3 T4 T5 T5b T5c T5d T41 T42 T43 --no-console-logs
    python debug.py --categories T6_easy T26_se_network
    python -c "from se_api import se_stats, se_quota_status; import json; print(json.dumps({'stats': se_stats(), 'quota': se_quota_status()}, indent=2))"
} *>&1 | Tee-Object -FilePath debugshit.txt -Append
"=== NEXUS TEST SESSION END $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz') ===" | Tee-Object -FilePath debugshit.txt -Append
Write-Host "DONE. Saved to debugshit.txt ($((Get-Item debugshit.txt).Length) bytes)"
```

Run:
```powershell
.\run_tests.ps1
```

Full session output lands in `debugshit.txt` and streams to console live.

---

## Environment variables

None required. All configuration is via `config.py`.

---

## Exit codes

`scraper.py`:
- `0` — completed or Ctrl-C
- `1` — preload failure, run lock held by another process, or fatal config mismatch

`debug.py`:
- `0` — all tests non-FAIL
- `1` — one or more FAIL

`error_fast.py`:
- `0` — always (diagnostic tool)

---

## See also

- `CHANGELOG.md` — full project history
- `expectederrors.txt` — 500 HTTP error categories driving MOS policies
- `resultsexample.json` — reference output schema
- `libraries.txt` — pinned dependency versions