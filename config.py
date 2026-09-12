import os
import platform

# ============================================================================
#  RUNTIME
# ============================================================================

IS_WIN = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"
IS_MAC = platform.system() == "Darwin"

CONFIG_VERSION = "4.0.0"
CONFIG_GENERATION = 4
EXTRACTOR_VERSION = "4.0.0"

STRICT_CONFIG_ENFORCEMENT = True
FORCE_RESUME_OVERRIDE_FLAG = "--force-resume"

# ============================================================================
#  CONCURRENCY / WORKERS
# ============================================================================

MAX_WORKERS = max(2, (os.cpu_count() or 4))
MAX_WORKERS_FAST_MULT = 2
MAX_RSS_MB = 900
WORKER_RECYCLE_AFTER_URLS = 5000
WORKER_RECYCLE_AFTER_SECONDS = 1800

SAME_DOMAIN_CONCURRENCY = 2
DOMAIN_TOKEN_BUCKET_RATE = 5.0
DOMAIN_TOKEN_BUCKET_BURST = 5
DOMAIN_TOKEN_BUCKET_MIN_RATE = 0.5
DOMAIN_TOKEN_BUCKET_MAX_RATE = 20.0
DOMAIN_BACKOFF_BASE = 1.5
DOMAIN_BACKOFF_MAX = 300.0
DOMAIN_FAILURE_THRESHOLD = 5
DOMAIN_COOLDOWN_SECONDS = 300
DOMAIN_RATE_ADAPTIVE = True
DOMAIN_RATE_PERSIST = True
DOMAIN_RATE_FILE = ".cache/domain_rates.json"
DOMAIN_RATE_429_FACTOR = 0.5
DOMAIN_RATE_2XX_FACTOR = 1.1
DOMAIN_RATE_2XX_WINDOW = 100

# ============================================================================
#  NETWORK
# ============================================================================

REQUEST_TIMEOUT = (15, 30)
REQUEST_TIMEOUT_FLAT = 30
CONNECT_TIMEOUT = 15
READ_TIMEOUT = 30
MAX_REDIRECTS = 10
MAX_RETRIES_PER_REQUEST = 3
RETRY_BACKOFF_BASE = 1.6

JITTER_RANGE = (0.7, 2.4)
FAST_JITTER_RANGE = (0.0, 0.05)

USER_AGENT_ROTATION = True
LOCALE_ROTATION = True
REFERER_CHAIN_ENABLED = True
COOKIE_PERSISTENCE = True
HTTP3_ENABLED = False
HTTP3_FALLBACK_TO_H2 = True

SESSION_WARMUP_ENABLED = True
SESSION_WARMUP_REQUESTS = 1
COOKIE_CACHE_ENABLED = True
COOKIE_CACHE_DIR = ".cache/cookies"
COOKIE_CACHE_TTL = 900

# ============================================================================
#  SPOOF / FINGERPRINT
# ============================================================================

TLS_GREASE = True
TLS_PERMUTE_EXTENSIONS = True
TLS_RECORD_SIZE_LIMIT = 16385
TLS_CERT_COMPRESSION = "brotli"
TLS_ENABLE_ALPS = True
TLS_ENABLE_TICKET = True
TLS_PSK_ENABLED = True

HTTP2_STREAM_WEIGHT = 256
HTTP2_NO_PRIORITY = False
HTTP2_PSEUDO_ORDER = "m,a,s,p"

AKAMAI_SETTINGS_CHROME = "1:65536;2:0;3:1000;4:6291456;6:262144"
AKAMAI_SETTINGS_FIREFOX = "1:65536;2:0;3:1000;4:131072;5:16384"
AKAMAI_SETTINGS_SAFARI = "2:0;4:4194304;3:100"
AKAMAI_WINDOW_CHROME = "15663105"
AKAMAI_WINDOW_FIREFOX = "12517377"
AKAMAI_WINDOW_SAFARI = "10420225"
AKAMAI_STREAMS_CHROME = "3:0:0:201,5:0:0:101,7:0:0:1"
AKAMAI_STREAMS_FIREFOX = "3:0:0:201,5:0:0:101,7:0:0:1"

PROXY_LIST = []
PROXY_ROTATE_PER_REQUEST = False
PROXY_ROTATE_PER_SESSION = True
PROXY_STICKY_DOMAIN = True

# ============================================================================
#  SOD — SERVICES OF DEVICES
# ============================================================================

SOD_WORKER_POOL_SIZE = 16
SOD_WORKER_RECYCLE_SECONDS = 600
SOD_STICKY_DOMAIN = True
SOD_ROTATE_ON_BLOCK = True

# ============================================================================
#  CRAWL CONTROL
# ============================================================================

MAX_DEPTH = 4
MAX_LINKS_PER_PAGE = 35
MAX_QUEUE_SIZE = 50000
CHECKPOINT_EVERY = 200
COMPACT_THRESHOLD = 0.30
IDLE_TIMEOUT = 6.0
CACHE_CLEAR_INTERVAL = 90
GC_INTERVAL = 40

TASK_QUEUE_MAX = 20000
RESULT_QUEUE_MAX = 20000
LINK_QUEUE_MAX = 20000

CROSS_DOMAIN_ALLOWLIST = []
CROSS_DOMAIN_DENYLIST = [
    "wikipedia.org/wiki/Special:",
    "wikipedia.org/wiki/Talk:",
    "wikipedia.org/wiki/Help:",
    "wikipedia.org/wiki/Wikipedia:",
    "wikipedia.org/wiki/Template:",
    "wikipedia.org/wiki/Category:",
    "wikipedia.org/w/index.php",
]
CROSS_DOMAIN_MAX_HOPS = 2
FOLLOW_NOFOLLOW = False
FOLLOW_EXTERNAL = False
RESPECT_ROBOTS = True
ROBOTS_CACHE_TTL = 3600

STREAM_SITEMAP = True
STREAM_FEED = True
STREAM_CHUNK_SIZE = 65536
MAX_SITEMAP_URLS = 200_000
MAX_FEED_ITEMS = 10_000

# ============================================================================
#  BLOCKED / ANTIBLOCK
# ============================================================================

BLOCKED_RETRY_MIN = 50.0
BLOCKED_RETRY_MAX = 80.0
BLOCKED_BACKOFF_MULTIPLIER = 1.5
MAX_BLOCKED_RETRIES = 5
BLOCKED_CHECK_INTERVAL = 3.0
BLOCKED_FINGERPRINT_ROTATE = True
BLOCKED_PROXY_ROTATE = True
BLOCKED_STATUS_CODES = {202, 403, 408, 429, 503, 520, 521, 522, 523, 524}
BLOCKED_BODY_MARKERS = (
    b"cf-chl-",
    b"just a moment",
    b"cloudflare",
    b"attention required",
    b"checking your browser",
    b"ddos protection",
    b"access denied",
    b"ray id",
    b"enable javascript and cookies",
    b"cf-browser-verification",
    b"__cf_chl_",
    b"challenge-platform",
    b"turnstile",
    b"g-recaptcha",
    b"h-captcha",
)

# ============================================================================
#  DEDUP
# ============================================================================

BLOOM_BITS = 1 << 27
BLOOM_HASHES = 7
SIMHASH_BITS = 64
SIMHASH_BANDS = 4
SIMHASH_HAMMING = 3
MINHASH_PERMS = 32
MINHASH_JACCARD = 0.85
SEMANTIC_DEDUP_ENABLED = True
SEMANTIC_DEDUP_THRESHOLD = 0.92

CHUNK_DEDUP_ENABLED = True
CHUNK_DEDUP_HAMMING = 6
CHUNK_DEDUP_PREFER_LONGER = True

# ============================================================================
#  EXTRACTION / QUALITY
# ============================================================================

OCR_MIN_TEXT_LEN = 50
OCR_DPI = 200
OCR_LANG = "eng"
OCR_TIMEOUT = 60
OCR_MULTILANG = False
OCR_MULTILANG_LANGS = "eng+deu+fra+spa"

PDF_MAX_PAGES = 200
PDF_MAX_OCR_PAGES = 20
PDF_TEXT_MODE = "blocks"
PDF_RECONSTRUCT_PARAGRAPHS = True
PDF_TRUNCATE_MARKER = True

CONTENT_MIN_CHARS = 200
CONTENT_MAX_CHARS = 10_000_000
TITLE_MAX_CHARS = 500
INTRO_MAX_CHARS = 2000
SECTION_MAX_CHARS = 100_000

QUALITY_MIN_WORDS = 30
QUALITY_MIN_FLESCH = 5.0
QUALITY_MIN_SENTENCES = 3
QUALITY_MAX_BOILERPLATE_RATIO = 0.75
QUALITY_MIN_LANG_CONFIDENCE = 0.85

NLP_COMPLEXITY_GATE_ENABLED = True
NLP_MIN_WORDS = 50
NLP_MIN_SENTENCES = 3

REGEX_INPUT_CAP = 500_000
REGEX_URL_CAP = 200_000
REGEX_WORD_CAP = 500_000

# ============================================================================
#  EXTRACTION SCORING
# ============================================================================

EXTRACTION_SCORING_ENABLED = True
EXTRACTION_SCORE_LENGTH_WEIGHT = 2.0
EXTRACTION_SCORE_BOILER_WEIGHT = 1.5
EXTRACTION_SCORE_FLESCH_WEIGHT = 1.0
EXTRACTION_SCORE_TITLE_WEIGHT = 0.5
EXTRACTION_SCORE_SECTIONS_WEIGHT = 0.8
EXTRACTION_SCORE_PUNCT_WEIGHT = 0.3
EXTRACTION_SCORE_LENGTH_CAP = 500
EXTRACTION_SCORE_SECTIONS_CAP = 10
EXTRACTION_SCORE_FLESCH_BEST = (40.0, 85.0)
EXTRACTION_SCORE_FLESCH_OK = (20.0, 95.0)

ARTICLE_ROOT_SELECTORS = (
    "article",
    "[role=main]",
    "main",
    ".post-content",
    ".article-body",
    ".entry-content",
    ".story-body",
    "#content-main",
    "#article-content",
    ".post-body",
    ".article__body",
    ".article-content",
    ".content-body",
)
ARTICLE_ROOT_MIN_CHARS = 200

# ============================================================================
#  CHUNKING
# ============================================================================

AGENT_CHUNK_ENABLED = True
AGENT_CHUNK_STRATEGY = "semantic"
AGENT_CHUNK_SIZE_TOKENS = 512
AGENT_CHUNK_OVERLAP_TOKENS = 64
AGENT_CHUNK_MIN_TOKENS = 32
AGENT_CHUNK_MAX_CHUNKS_PER_DOC = 2048
AGENT_CHUNK_PRESERVE_SENTENCES = True
AGENT_CHUNK_PRESERVE_PARAGRAPHS = True
AGENT_CHUNK_INCLUDE_HEADING_CONTEXT = True
AGENT_CHUNK_INCLUDE_URL_CONTEXT = True
AGENT_CHUNK_ATTACH_METADATA = True
AGENT_CHUNK_DEDUP_WITHIN_DOC = True
AGENT_CHUNK_OFFSET_AWARE = True

# ============================================================================
#  TOKENIZATION
# ============================================================================

AGENT_TOKENIZER = "whitespace"
AGENT_TOKENIZER_FALLBACK = "whitespace"
AGENT_TOKEN_COUNT_APPROX = True
AGENT_TOKEN_COUNT_RATIO = 1.35

# ============================================================================
#  SUMMARY
# ============================================================================

AGENT_SUMMARY_ENABLED = True
AGENT_SUMMARY_MAX_TOKENS = 256
AGENT_SUMMARY_MIN_TOKENS = 20
AGENT_SUMMARY_STRATEGY = "extractive"
AGENT_SUMMARY_TOP_SENTENCES = 5
AGENT_SUMMARY_INCLUDE_TITLE = True

# ============================================================================
#  ENTITIES V2
# ============================================================================

AGENT_ENTITY_EXTRACT_ENABLED = True
AGENT_ENTITY_TYPES = (
    "PERSON", "ORG", "GPE", "LOC", "DATE", "TIME", "MONEY",
    "PERCENT", "PRODUCT", "EVENT", "WORK_OF_ART", "LAW", "LANGUAGE",
    "EMAIL", "URL", "PHONE", "YEAR",
)
AGENT_ENTITY_MAX_PER_DOC = 200
AGENT_ENTITY_MIN_LENGTH = 2
AGENT_ENTITY_DEDUP = True
AGENT_ENTITY_CASE_INSENSITIVE_DEDUP = True

ENTITY_FREQUENCY_FILTER_ENABLED = True
ENTITY_MIN_OCCURRENCES = 2
ENTITY_REPORTING_VERBS = (
    "said", "says", "wrote", "writes", "stated", "states",
    "reported", "reports", "announced", "announces",
    "added", "adds", "noted", "notes", "claimed", "claims",
    "argued", "argues", "testified", "testifies",
)
ENTITY_REPORTING_WINDOW = 30
ENTITY_FIRSTNAME_DICT_ENABLED = True
ENTITY_FIRSTNAME_WEIGHT = 1.0
ENTITY_NON_FIRSTNAME_WEIGHT = 0.4
ENTITY_BOUNDARY_ENABLED = True
ENTITY_SECTION_AWARE = True
ENTITY_SKIP_TAGS = ("script", "style", "code", "pre", "h1", "h2", "h3", "h4", "h5", "h6")
ENTITY_AUTHOR_BOOST = True
ENTITY_ORG_SUFFIXES = (
    "Inc", "Ltd", "LLC", "Corp", "GmbH", "Co", "SA", "AG",
    "Foundation", "Institute", "University", "Ministry",
    "Agency", "Bureau", "Council", "Committee", "Association",
    "Organization", "Organisation", "Group", "Holdings",
)
ENTITY_COREF_ENABLED = True
ENTITY_COREF_MIN_LENGTH = 4
ENTITY_HEADINGS_SKIPPED = True

# ============================================================================
#  TOPICS
# ============================================================================

AGENT_TOPIC_EXTRACT_ENABLED = True
AGENT_TOPIC_MAX_PER_DOC = 20
AGENT_TOPIC_MIN_SCORE = 0.15
AGENT_TOPIC_NGRAM_MAX = 3
AGENT_TOPIC_STOPWORDS_LANG = "en"
AGENT_TOPIC_DEDUP = True

# ============================================================================
#  KEYWORDS
# ============================================================================

AGENT_KEYWORD_EXTRACT_ENABLED = True
AGENT_KEYWORD_MAX_PER_DOC = 30
AGENT_KEYWORD_ALGORITHM = "tfidf"
AGENT_KEYWORD_MIN_LENGTH = 3
AGENT_KEYWORD_DEDUP = True
AGENT_KEYWORD_LANGUAGES = ("en", "de", "fr", "es", "it", "pt", "nl", "ru", "zh", "ja")

# ============================================================================
#  LANGUAGE DETECTION
# ============================================================================

LANGUAGE_ALLOWLIST = ["en", "de", "fr", "es", "it", "pt", "nl", "ja", "ko", "zh"]
LANGUAGE_FILTER_ENABLED = False
LANGUAGE_DETECT_ORDER = (
    "html_lang", "response_header", "og_locale", "trafilatura", "ngram",
)
LANGUAGE_NGRAM_ENABLED = True
LANGUAGE_NGRAM_MIN_CONFIDENCE = 0.55
LANGUAGE_NGRAM_MIN_TEXT_LEN = 40
LANGUAGE_RECORD_SOURCE = True
ENCODING_FALLBACK = "utf-8"

# ============================================================================
#  PII REDACTION
# ============================================================================

AGENT_PII_REDACT_ENABLED = False
AGENT_PII_REDACT_EMAIL = True
AGENT_PII_REDACT_PHONE = True
AGENT_PII_REDACT_SSN = True
AGENT_PII_REDACT_CREDIT_CARD = True
AGENT_PII_REDACT_IP = False
AGENT_PII_REDACT_ADDRESS = False
AGENT_PII_REDACT_PLACEHOLDER = "[REDACTED]"

# ============================================================================
#  AGENT OUTPUT SCHEMA
# ============================================================================

AGENT_SCHEMA_VERSION = "4.0.0"
AGENT_OUTPUT_FORMAT = "ndjson"
AGENT_INCLUDE_RAW_HTML = False
AGENT_INCLUDE_RAW_TEXT = True
AGENT_INCLUDE_MARKDOWN = True
AGENT_INCLUDE_LINKS = True
AGENT_INCLUDE_METADATA = True
AGENT_INCLUDE_PROVENANCE = True
AGENT_INCLUDE_QUALITY = True
AGENT_INCLUDE_EMBEDDING_READY = True
AGENT_INCLUDE_ENTITY_HINTS = True
AGENT_INCLUDE_TOPIC_HINTS = True
AGENT_INCLUDE_LANGUAGE = True
AGENT_INCLUDE_READABILITY = True
AGENT_INCLUDE_TOKEN_COUNT = True
AGENT_INCLUDE_CONTENT_HASH = True
AGENT_INCLUDE_SOURCE_SIGNATURE = True
AGENT_INCLUDE_LICENSE = True
AGENT_INCLUDE_CANONICAL_URL = True
AGENT_INCLUDE_IDEMPOTENCY_KEY = True
AGENT_INCLUDE_EXTRACTOR_VERSION = True
AGENT_INCLUDE_CONFIG_HASH = True
AGENT_INCLUDE_EXTRACTION_SCORES = True

AGENT_RECORD_FIELDS = (
    "id",
    "url",
    "canonical_url",
    "domain",
    "tld",
    "title",
    "language",
    "published_date",
    "updated_date",
    "crawled_at",
    "content_hash",
    "simhash",
    "source_signature",
    "idempotency_key",
    "extractor_version",
    "config_hash",
    "license",
    "quality",
    "word_count",
    "token_count",
    "char_count",
    "sentence_count",
    "reading_time_seconds",
    "flesch_reading_ease",
    "flesch_kincaid_grade",
    "gunning_fog",
    "smog_index",
    "automated_readability_index",
    "coleman_liau_index",
    "dale_chall_score",
    "text_standard",
    "difficulty",
    "topics",
    "entities",
    "keywords",
    "summary",
    "sections",
    "chunks",
    "links",
    "metadata",
    "provenance",
    "content",
    "schema_version",
    "kind",
)

# ============================================================================
#  SCHEMA VALIDATION
# ============================================================================

SCHEMA_VALIDATION_ENABLED = True
SCHEMA_VALIDATION_STRICT = False
SCHEMA_VALIDATION_MAX_ERRORS = 5

# ============================================================================
#  PROVENANCE
# ============================================================================

AGENT_PROVENANCE_INCLUDE_REQUEST_HEADERS = True
AGENT_PROVENANCE_INCLUDE_RESPONSE_HEADERS = True
AGENT_PROVENANCE_INCLUDE_IP_HASH = True
AGENT_PROVENANCE_INCLUDE_PROFILE = True
AGENT_PROVENANCE_INCLUDE_PROXY_HASH = True
AGENT_PROVENANCE_INCLUDE_HTTP_VERSION = True
AGENT_PROVENANCE_INCLUDE_TLS_FINGERPRINT = True
AGENT_PROVENANCE_INCLUDE_TIMING = True

# ============================================================================
#  EXTRACTION CACHE
# ============================================================================

CACHE_EXTRACTION = True
CACHE_HARD = False
CACHE_DB = ".cache/extraction.sqlite"
CACHE_MAX_ROWS = 500_000
CACHE_TTL_SECONDS = 604800
CACHE_VALIDATE_ETAG = True
CACHE_VALIDATE_LAST_MODIFIED = True

# ============================================================================
#  FAILURE CATEGORIES / QUARANTINE
# ============================================================================

AGENT_QUARANTINE_ENABLED = True
AGENT_QUARANTINE_LOW_QUALITY = True
AGENT_QUARANTINE_EMPTY_CONTENT = True
AGENT_QUARANTINE_LANGUAGE_MISMATCH = True
AGENT_QUARANTINE_SEMANTIC_DUP = True
AGENT_QUARANTINE_PII = False
AGENT_QUARANTINE_SCHEMA_INVALID = True
AGENT_QUARANTINE_EXTRACTION_ERROR = True
AGENT_QUARANTINE_JS_REQUIRED = True
AGENT_QUARANTINE_PDF_TRUNCATED = False
AGENT_QUARANTINE_BLOCKED_PERMANENT = False

QUARANTINE_CATEGORIES = (
    "empty",
    "low_quality",
    "language_mismatch",
    "duplicate_content",
    "schema_invalid",
    "extraction_error",
    "js_required",
    "pdf_truncated",
    "blocked_permanent",
    "empty_extraction",
)

JS_REQUIRED_MARKERS = (
    "__NEXT_DATA__",
    "__NUXT__",
    "window.__DATA__",
    "__INITIAL_STATE__",
    "id=\"__next\"",
    "id=\"app\"",
    "data-reactroot",
)

# ============================================================================
#  STORAGE PATHS
# ============================================================================

from folder_manager import FolderManager as _FM

STATE_FILE = str(_FM.STATE / "crawl.state.json")
QUEUE_FILE = str(_FM.STATE / "queue.txt")
JOURNAL_FILE = str(_FM.STATE / "queue.journal")
DONE_FILE = str(_FM.STATE / "done.txt")
ERRORS_FILE = str(_FM.STATE / "errors.txt")
BLOCKED_FILE = str(_FM.STATE / "blocked.txt")
RESUME_JOURNAL = str(_FM.STATE / "journal.ndjson")
PID_FILE = str(_FM.STATE / "crawl.pid")

DEDUP_DB = str(_FM.DB / "dedup.sqlite")
BLOOM_FILE = str(_FM.DB / "bloom.bin")
MOS_CACHE_DB = str(_FM.DB / "mos_cache.sqlite")
CACHE_DB = str(_FM.DB / "extraction.sqlite")

DOMAIN_RATE_FILE = str(_FM.CACHE / "domain_rates.json")
MOS_HOST_PREFS_FILE = str(_FM.CACHE / "mos_host_prefs.json")
MOS_BUDGET_FILE = str(_FM.CACHE / "mos_budget.json")
DEAD_LETTER_FILE = str(_FM.CACHE / "dead_letter.jsonl")

LOG_FILE = str(_FM.LOGS / "crawl.log")
OUTPUT_PATH = str(_FM.OUTPUT / "output.ndjson")

CACHE_DIR = str(_FM.CACHE)
COOKIE_CACHE_DIR = str(_FM.COOKIES)

AGENT_INDEX_DIR = str(_FM.AGENT)
AGENT_MANIFEST = str(_FM.OUTPUT / "manifest.json")
AGENT_SHARDS_DIR = str(_FM.SHARDS)
AGENT_EMBEDDINGS_FILE = str(_FM.AGENT / "embeddings.bin")
AGENT_ENTITIES_FILE = str(_FM.AGENT / "entities.jsonl")
AGENT_TOPICS_FILE = str(_FM.AGENT / "topics.jsonl")
AGENT_QUARANTINE_DIR = str(_FM.QUARANTINE)

# Backwards-compat aliases used by older code
CACHE_DIR_LEGACY = ".cache"
AGENT_DIR_LEGACY = ".agent"

# ============================================================================
#  AGENT MANIFEST
# ============================================================================

AGENT_MANIFEST_WRITE_INTERVAL = 60
AGENT_MANIFEST_INCLUDE_COUNTS = True
AGENT_MANIFEST_INCLUDE_SHARDS = True
AGENT_MANIFEST_INCLUDE_CONFIG_HASH = True
AGENT_MANIFEST_INCLUDE_SCHEMA_VERSION = True
AGENT_MANIFEST_INCLUDE_INDEX_MAP = True
AGENT_MANIFEST_INCLUDE_CATEGORY_COUNTS = True

# ============================================================================
#  AGENT SHARDING
# ============================================================================

AGENT_SHARD_ENABLED = True
AGENT_SHARD_SIZE_RECORDS = 50000
AGENT_SHARD_SIZE_BYTES = 256 * 1024 * 1024
AGENT_SHARD_COMPRESS = "none"
AGENT_SHARD_NAMING = "shard-{index:05d}.ndjson"

# ============================================================================
#  AGENT FILTERING
# ============================================================================

AGENT_FILTER_MIN_QUALITY = 0.0
AGENT_FILTER_MIN_TOKENS = 20
AGENT_FILTER_MAX_TOKENS = 5_000_000
AGENT_FILTER_ALLOWED_LANGUAGES = LANGUAGE_ALLOWLIST
AGENT_FILTER_BLOCKED_DOMAINS = []
AGENT_FILTER_BLOCKED_URL_PATTERNS = []
AGENT_FILTER_REQUIRE_HTML = False
AGENT_FILTER_REQUIRE_TITLE = False

# ============================================================================
#  SEEDS
# ============================================================================

SEEDS = [
    "https://en.wikipedia.org/wiki/Online_streamer",
]

SEED_FILE = None
SEED_URL_FILE = None
SEED_SITEMAP_URLS = []
SEED_RSS_FEEDS = []

# ============================================================================
#  BROWSER PROFILES
# ============================================================================

BROWSER_PROFILES = [
    {
        "impersonate": "chrome136",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
        "sec_ch_ua_mobile": "?0",
        "sec_ch_ua_platform": '"Windows"',
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept_encoding": "gzip, deflate, br, zstd",
        "sec_fetch_dest": "document",
        "sec_fetch_mode": "navigate",
        "sec_fetch_user": "?1",
        "upgrade_insecure": "1",
        "priority": "u=0, i",
        "family": "chrome",
    },
    {
        "impersonate": "chrome131",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Chromium";v="131", "Google Chrome";v="131", "Not.A/Brand";v="24"',
        "sec_ch_ua_mobile": "?0",
        "sec_ch_ua_platform": '"Windows"',
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept_encoding": "gzip, deflate, br, zstd",
        "sec_fetch_dest": "document",
        "sec_fetch_mode": "navigate",
        "sec_fetch_user": "?1",
        "upgrade_insecure": "1",
        "priority": "u=0, i",
        "family": "chrome",
    },
    {
        "impersonate": "chrome142",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        "sec_ch_ua_mobile": "?0",
        "sec_ch_ua_platform": '"Windows"',
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept_encoding": "gzip, deflate, br, zstd",
        "sec_fetch_dest": "document",
        "sec_fetch_mode": "navigate",
        "sec_fetch_user": "?1",
        "upgrade_insecure": "1",
        "priority": "u=0, i",
        "family": "chrome",
    },
    {
        "impersonate": "safari184",
        "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15",
        "sec_ch_ua": None,
        "sec_ch_ua_mobile": None,
        "sec_ch_ua_platform": None,
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept_encoding": "gzip, deflate, br",
        "sec_fetch_dest": "document",
        "sec_fetch_mode": "navigate",
        "sec_fetch_user": "?1",
        "upgrade_insecure": "1",
        "priority": None,
        "family": "safari",
    },
    {
        "impersonate": "safari184_ios",
        "ua": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Mobile/15E148 Safari/604.1",
        "sec_ch_ua": None,
        "sec_ch_ua_mobile": None,
        "sec_ch_ua_platform": None,
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept_encoding": "gzip, deflate, br",
        "sec_fetch_dest": "document",
        "sec_fetch_mode": "navigate",
        "sec_fetch_user": "?1",
        "upgrade_insecure": "1",
        "priority": None,
        "family": "safari",
    },
    {
        "impersonate": "firefox135",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
        "sec_ch_ua": None,
        "sec_ch_ua_mobile": None,
        "sec_ch_ua_platform": None,
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "accept_encoding": "gzip, deflate, br",
        "sec_fetch_dest": "document",
        "sec_fetch_mode": "navigate",
        "sec_fetch_user": "?1",
        "upgrade_insecure": "1",
        "priority": None,
        "family": "firefox",
    },
    {
        "impersonate": "tor145",
        "ua": "Mozilla/5.0 (Windows NT 10.0; rv:128.0) Gecko/20100101 Firefox/128.0",
        "sec_ch_ua": None,
        "sec_ch_ua_mobile": None,
        "sec_ch_ua_platform": None,
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "accept_encoding": "gzip, deflate, br",
        "sec_fetch_dest": "document",
        "sec_fetch_mode": "navigate",
        "sec_fetch_user": "?1",
        "upgrade_insecure": "1",
        "priority": None,
        "family": "firefox",
    },
    {
        "impersonate": "edge101",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36 Edg/101.0.1210.39",
        "sec_ch_ua": '"Microsoft Edge";v="101", "Chromium";v="101", "Not=A?Brand";v="99"',
        "sec_ch_ua_mobile": "?0",
        "sec_ch_ua_platform": '"Windows"',
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept_encoding": "gzip, deflate, br",
        "sec_fetch_dest": "document",
        "sec_fetch_mode": "navigate",
        "sec_fetch_user": "?1",
        "upgrade_insecure": "1",
        "priority": "u=0, i",
        "family": "chrome",
    },
]

HEADER_ORDER_CHROME = (
    "Host", "Connection", "Content-Length",
    "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform",
    "Upgrade-Insecure-Requests", "User-Agent", "Accept",
    "Sec-Fetch-Site", "Sec-Fetch-Mode", "Sec-Fetch-User", "Sec-Fetch-Dest",
    "Referer", "Accept-Encoding", "Accept-Language", "Cookie", "Priority",
)

HEADER_ORDER_FIREFOX = (
    "Host", "User-Agent", "Accept", "Accept-Language", "Accept-Encoding",
    "Connection", "Upgrade-Insecure-Requests",
    "Sec-Fetch-Dest", "Sec-Fetch-Mode", "Sec-Fetch-Site", "Sec-Fetch-User",
    "Priority", "Referer", "Cookie",
)

HEADER_ORDER_SAFARI = (
    "Host", "Accept", "Sec-Fetch-Site", "Connection", "Sec-Fetch-Mode",
    "Accept-Language", "Accept-Encoding", "User-Agent", "Sec-Fetch-Dest",
    "Referer", "Cookie",
)

LOCALES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "en-CA,en;q=0.9,fr-CA;q=0.7",
    "de-DE,de;q=0.9,en;q=0.7",
    "fr-FR,fr;q=0.9,en;q=0.7",
    "es-ES,es;q=0.9,en;q=0.7",
    "it-IT,it;q=0.9,en;q=0.7",
    "nl-NL,nl;q=0.9,en;q=0.7",
    "pl-PL,pl;q=0.9,en;q=0.6",
    "pt-BR,pt;q=0.9,en;q=0.7",
    "ja-JP,ja;q=0.9,en;q=0.7",
    "ko-KR,ko;q=0.9,en;q=0.7",
]

# ============================================================================
#  LOGGING
# ============================================================================

LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(processName)s %(message)s"
LOG_ROTATE_BYTES = 10 * 1024 * 1024
LOG_BACKUP_COUNT = 5
LOG_TO_FILE = True
LOG_TO_CONSOLE = True
LOG_INCLUDE_STACK = False

# ============================================================================
#  TELEMETRY
# ============================================================================

TELEMETRY_ENABLED = False
TELEMETRY_INTERVAL = 30
TELEMETRY_INCLUDE_RSS = True
TELEMETRY_INCLUDE_QUEUE_SIZE = True
TELEMETRY_INCLUDE_RATE = True
TELEMETRY_INCLUDE_BLOCKED_RATE = True
TELEMETRY_INCLUDE_DUP_RATE = True
TELEMETRY_INCLUDE_ERROR_RATE = True
TELEMETRY_INCLUDE_CATEGORY_COUNTS = True

# ============================================================================
#  AUDIT
# ============================================================================

AUDIT_ENABLED = True
AUDIT_REPORT_PATH = "audit_report.json"
AUDIT_TOP_DOMAINS = 20
AUDIT_SAMPLE_ROWS = 5
AUDIT_CHUNK_HISTOGRAM_BINS = 20
AUDIT_ENTITY_HISTOGRAM_BINS = 20
AUDIT_WORDCOUNT_HISTOGRAM_BINS = 30
AUDIT_FLESCH_HISTOGRAM_BINS = 20
AUDIT_INCLUDE_CATEGORY_BREAKDOWN = True
AUDIT_INCLUDE_LANGUAGE_HISTOGRAM = True
AUDIT_INCLUDE_DUPLICATE_RATE = True
AUDIT_INCLUDE_QUALITY_PERCENTILES = True

# ============================================================================
#  MOS — MIXTURE OF SERVICES
# ============================================================================

MOS_ENABLED = True
MOS_HEDGE_ENABLED = True
MOS_HEDGE_POLICIES = {"cloudflare_turnstile", "503_unavailable", "504_timeout"}
MOS_HEDGE_DELAY_MS = 800
MOS_STICKY_TTL = 86400
MOS_STICKY_SUCCESS_THRESHOLD = 3
MOS_STICKY_FAILURE_THRESHOLD = 3

MOS_DAILY_BUDGET = {
    "jina_reader": 1440,
    "firecrawl_keyless": 33,
    "replyfast_md": 500,
    "pagesnap": 30,
    "microlink": 25,
    "kiprio_readability": 500,
    "corsproxy_io": 86400,
    "corsfix": 86400,
    "wayback_cdx": 86400,
    "datamuse": 100000,
    "rss2json": 10000,
    "wikipedia_summary": None,
    "ddg_ia": None,
    "commoncrawl_cdx": None,
    "urlscan_search": None,
    "allorigins": None,
    "cors_lol": None,
    "killcors": None,
    "archive_today": None,
    "web2md": None,
    "parallel_search": None,
}
MOS_BUDGET_WARN_RATIO = 0.80
MOS_BUDGET_STOP_RATIO = 0.95
MOS_HOST_PREFS_FILE = ".cache/mos_host_prefs.json"
MOS_BUDGET_FILE = ".cache/mos_budget.json"
MOS_CACHE_DB = ".cache/mos_cache.sqlite"

CORS_RELAYS = ("corsproxy_io", "allorigins", "cors_lol", "corsfix", "killcors")
MD_RELAYS = ("jina_reader", "replyfast_md", "pagesnap", "web2md",
             "microlink", "kiprio_readability")

MOS_FIRST_HOSTS = (
    "quora.com", "trustpilot.com", "imdb.com", "yelp.com",
    "binance.com", "tripadvisor.com", "cell.com",
    "royalsocietypublishing.org", "nih.gov", "collinsdictionary.com",
    "thefreedictionary.com",
)

MOS_STACKEXCHANGE_POLICY = "se_api"

# ============================================================================
#  VERIFICATION LAYER
# ============================================================================

VERIFY_ENABLED = True
VERIFY_WAYBACK = True
VERIFY_COMMONCRAWL = True
VERIFY_URLSCAN = True
VERIFY_DOH = True
VERIFY_DOH_RESOLVERS = (
    "https://cloudflare-dns.com/dns-query",
    "https://dns.google/resolve",
    "https://dns.quad9.net/dns-query",
)
VERIFY_SAMPLE_RATIO = 0.10

# ============================================================================
#  ENRICHMENT LAYER
# ============================================================================

ENRICH_DDG = True
ENRICH_WIKIPEDIA = True
ENRICH_DATAMUSE = True
ENRICH_KIPRIO = True
ENRICH_MICROLINK = True

# ============================================================================
#  WAYBACK-FIRST
# ============================================================================

WAYBACK_FIRST_ENABLED = True
WAYBACK_FIRST_HOSTS = (
    "x.com", "twitter.com", "facebook.com", "instagram.com",
    "reuters.com", "nytimes.com", "wsj.com",
)

# ============================================================================
#  FREE PROXIES
# ============================================================================

FREE_PROXY_ENABLED = False
FREE_PROXY_SOURCES = (
    "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/all/data.json",
    "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies",
)
FREE_PROXY_VALIDATE_ENDPOINT = "https://httpbin.org/ip"
FREE_PROXY_VALIDATE_INTERVAL = 1800

# ============================================================================
#  API ROUTER
# ============================================================================

API_ROUTER_ENABLED = True
API_ROUTER_TIMEOUT = 15
API_ROUTER_MAX_ITEMS = 100

# ============================================================================
#  STACK EXCHANGE API
# ============================================================================

SE_API_ENABLED = True
SE_API_KEY = None
SE_API_MAX_ANSWERS = 20
SE_API_TIMEOUT = 15
SE_ROUTE_BEFORE_DIRECT = True
SE_ACCEPT_EMPTY_TITLE = False

# ============================================================================
#  BROWSER FALLBACK (disabled — no browsers)
# ============================================================================

BROWSER_FALLBACK_ENABLED = False
BROWSER_FALLBACK_ENGINE = "auto"
BROWSER_FALLBACK_HEADLESS = True
BROWSER_FALLBACK_TIMEOUT = 30
BROWSER_FALLBACK_WAIT_UNTIL = "domcontentloaded"
BROWSER_FALLBACK_MAX_CONCURRENT = 1
BROWSER_FALLBACK_HOSTS = ()