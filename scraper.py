import os
import re
import sys
import time
import json
import math
import uuid
import asyncio
import hashlib
import argparse
import gzip
import random
import struct
import sqlite3
import logging
import threading
import unicodedata
from collections import Counter, defaultdict, OrderedDict
from dataclasses import dataclass, field, asdict
from functools import lru_cache
from pathlib import Path
from urllib.parse import (
    urljoin, urlparse, urlencode, parse_qs, quote, unquote,
)

import orjson
import pymupdf
from selectolax.lexbor import LexborHTMLParser
from lxml import etree
from lxml_html_clean import Cleaner
import justext
import trafilatura
from trafilatura import bare_extraction, extract as trafilatura_extract
from htmldate import find_date
from dateparser import parse as dateparser_parse
from dateutil import parser as dateutil_parser
import textstat
import regex
import pyphen
import tld as _tld_mod
from courlan import clean_url, normalize_url, is_navigation_page
from defusedxml import ElementTree as SafeET
from babel import Locale
from tzlocal import get_localzone

from curl_cffi.requests import AsyncSession as _AsyncRequestsSession

from folder_manager import FolderManager, FolderError

from error_fast import (
    install_all as _error_fast_install,
    safe_asyncio_run,
    safe_async_session_close,
    fast_catch,
    ErrorFast,
    Kind as _EFKind,
    swallow as _ef_swallow,
)

_error_fast_install()

from config import (
    SEEDS, SEED_FILE, SEED_URL_FILE, SEED_SITEMAP_URLS, SEED_RSS_FEEDS,
    OCR_MIN_TEXT_LEN, OCR_DPI, OCR_LANG, OCR_TIMEOUT,
    MAX_LINKS_PER_PAGE,
    QUALITY_MIN_WORDS, QUALITY_MIN_FLESCH, QUALITY_MIN_SENTENCES,
    QUALITY_MAX_BOILERPLATE_RATIO, QUALITY_MIN_LANG_CONFIDENCE,
    CONTENT_MIN_CHARS, CONTENT_MAX_CHARS,
    TITLE_MAX_CHARS, INTRO_MAX_CHARS, SECTION_MAX_CHARS,
    LANGUAGE_ALLOWLIST, LANGUAGE_FILTER_ENABLED,
    LANGUAGE_DETECT_ORDER, LANGUAGE_NGRAM_ENABLED,
    LANGUAGE_NGRAM_MIN_CONFIDENCE, LANGUAGE_NGRAM_MIN_TEXT_LEN,
    LANGUAGE_RECORD_SOURCE, ENCODING_FALLBACK,
    BLOCKED_STATUS_CODES, BLOCKED_BODY_MARKERS,
    MAX_QUEUE_SIZE, MAX_DEPTH, MAX_WORKERS, OUTPUT_PATH,
    MAX_RETRIES_PER_REQUEST, RETRY_BACKOFF_BASE,
    DOMAIN_TOKEN_BUCKET_RATE, DOMAIN_TOKEN_BUCKET_BURST,
    AGENT_CHUNK_ENABLED, AGENT_CHUNK_SIZE_TOKENS,
    AGENT_CHUNK_OVERLAP_TOKENS, AGENT_CHUNK_MIN_TOKENS,
    AGENT_CHUNK_MAX_CHUNKS_PER_DOC, AGENT_CHUNK_INCLUDE_HEADING_CONTEXT,
    AGENT_CHUNK_INCLUDE_URL_CONTEXT,
    AGENT_TOKEN_COUNT_RATIO,
    AGENT_SUMMARY_ENABLED, AGENT_SUMMARY_MAX_TOKENS,
    AGENT_SUMMARY_MIN_TOKENS, AGENT_SUMMARY_TOP_SENTENCES,
    AGENT_ENTITY_EXTRACT_ENABLED, AGENT_ENTITY_MAX_PER_DOC,
    AGENT_ENTITY_MIN_LENGTH, AGENT_ENTITY_DEDUP,
    AGENT_ENTITY_CASE_INSENSITIVE_DEDUP,
    AGENT_TOPIC_EXTRACT_ENABLED, AGENT_TOPIC_MAX_PER_DOC,
    AGENT_TOPIC_MIN_SCORE, AGENT_TOPIC_NGRAM_MAX,
    AGENT_KEYWORD_EXTRACT_ENABLED, AGENT_KEYWORD_MAX_PER_DOC,
    AGENT_KEYWORD_MIN_LENGTH, AGENT_KEYWORD_LANGUAGES,
    AGENT_PII_REDACT_ENABLED, AGENT_PII_REDACT_EMAIL,
    AGENT_PII_REDACT_PHONE, AGENT_PII_REDACT_SSN,
    AGENT_PII_REDACT_CREDIT_CARD, AGENT_PII_REDACT_IP,
    AGENT_PII_REDACT_PLACEHOLDER,
    AGENT_RECORD_FIELDS, AGENT_SCHEMA_VERSION,
    AGENT_INCLUDE_PROVENANCE, AGENT_INCLUDE_QUALITY,
    AGENT_INCLUDE_EMBEDDING_READY,
    AGENT_INCLUDE_IDEMPOTENCY_KEY, AGENT_INCLUDE_EXTRACTOR_VERSION,
    AGENT_INCLUDE_CONFIG_HASH,
    EXTRACTOR_VERSION,
    NLP_COMPLEXITY_GATE_ENABLED, NLP_MIN_WORDS, NLP_MIN_SENTENCES,
    REGEX_INPUT_CAP, REGEX_URL_CAP, REGEX_WORD_CAP,
    EXTRACTION_SCORING_ENABLED, EXTRACTION_SCORE_LENGTH_WEIGHT,
    EXTRACTION_SCORE_BOILER_WEIGHT, EXTRACTION_SCORE_FLESCH_WEIGHT,
    EXTRACTION_SCORE_TITLE_WEIGHT, EXTRACTION_SCORE_SECTIONS_WEIGHT,
    EXTRACTION_SCORE_PUNCT_WEIGHT, EXTRACTION_SCORE_LENGTH_CAP,
    EXTRACTION_SCORE_SECTIONS_CAP, EXTRACTION_SCORE_FLESCH_BEST,
    EXTRACTION_SCORE_FLESCH_OK,
    ARTICLE_ROOT_SELECTORS, ARTICLE_ROOT_MIN_CHARS,
    PDF_MAX_PAGES, PDF_MAX_OCR_PAGES, PDF_TEXT_MODE,
    PDF_RECONSTRUCT_PARAGRAPHS, PDF_TRUNCATE_MARKER,
    ENTITY_FREQUENCY_FILTER_ENABLED, ENTITY_MIN_OCCURRENCES,
    ENTITY_REPORTING_VERBS, ENTITY_REPORTING_WINDOW,
    ENTITY_FIRSTNAME_DICT_ENABLED, ENTITY_FIRSTNAME_WEIGHT,
    ENTITY_NON_FIRSTNAME_WEIGHT, ENTITY_BOUNDARY_ENABLED,
    ENTITY_SECTION_AWARE, ENTITY_SKIP_TAGS,
    ENTITY_AUTHOR_BOOST, ENTITY_ORG_SUFFIXES, ENTITY_COREF_ENABLED,
    CHUNK_DEDUP_ENABLED, CHUNK_DEDUP_HAMMING, CHUNK_DEDUP_PREFER_LONGER,
    AGENT_CHUNK_OFFSET_AWARE,
    JS_REQUIRED_MARKERS,
    CACHE_DIR, CACHE_EXTRACTION, CACHE_HARD, CACHE_DB,
    CACHE_MAX_ROWS, CACHE_TTL_SECONDS,
    MOS_ENABLED, MOS_HEDGE_ENABLED, MOS_HEDGE_POLICIES,
    MOS_HEDGE_DELAY_MS, MOS_STICKY_TTL, MOS_STICKY_SUCCESS_THRESHOLD,
    MOS_STICKY_FAILURE_THRESHOLD,
    MOS_DAILY_BUDGET, MOS_BUDGET_WARN_RATIO, MOS_BUDGET_STOP_RATIO,
    MOS_HOST_PREFS_FILE, MOS_BUDGET_FILE, MOS_CACHE_DB,
    CORS_RELAYS, MD_RELAYS,
    VERIFY_ENABLED, VERIFY_WAYBACK, VERIFY_COMMONCRAWL,
    VERIFY_URLSCAN, VERIFY_DOH, VERIFY_DOH_RESOLVERS,
    VERIFY_SAMPLE_RATIO,
    ENRICH_DDG, ENRICH_WIKIPEDIA, ENRICH_DATAMUSE,
    ENRICH_KIPRIO, ENRICH_MICROLINK,
    WAYBACK_FIRST_HOSTS, WAYBACK_FIRST_ENABLED,
    FREE_PROXY_ENABLED, FREE_PROXY_SOURCES,
    FREE_PROXY_VALIDATE_ENDPOINT, FREE_PROXY_VALIDATE_INTERVAL,
    API_ROUTER_ENABLED, API_ROUTER_TIMEOUT, API_ROUTER_MAX_ITEMS,
    SE_API_ENABLED, SE_API_KEY, SE_API_MAX_ANSWERS, SE_API_TIMEOUT,
    SE_ROUTE_BEFORE_DIRECT, SE_ACCEPT_EMPTY_TITLE,
    MOS_FIRST_HOSTS,
    LOG_LEVEL,
)

_LOG = logging.getLogger("scraper")
_LOG.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))


def _log(msg, *args, level=logging.INFO):
    try:
        _LOG.log(level, msg, *args)
    except Exception:
        pass


# ============================================================================
#  PRELOADER
# ============================================================================

class Preloader:
    def __init__(self):
        self.results = OrderedDict()
        self.t_start = None
        self.done = False

    def _step(self, name, fn):
        t0 = time.monotonic()
        try:
            fn()
            elapsed = time.monotonic() - t0
            self.results[name] = {"ok": True, "elapsed": round(elapsed, 4)}
            _log("preload[%s] ok in %.3fs", name, elapsed)
        except Exception as e:
            elapsed = time.monotonic() - t0
            self.results[name] = {"ok": False, "elapsed": round(elapsed, 4),
                                   "error": repr(e)[:200]}
            _log("preload[%s] FAILED in %.3fs: %r", name, elapsed, e,
                 level=logging.WARNING)

    def load(self):
        if self.done:
            return self.results
        self.t_start = time.monotonic()
        _log("preloader starting")
        self._step("folder_manager", FolderManager.bootstrap)
        self._step("error_fast", _error_fast_install)
        self._step("regexes", self._warm_regexes)
        self._step("stopwords", self._warm_stopwords)
        self._step("tld", self._warm_tld)
        self._step("trafilatura", self._warm_trafilatura)
        self._step("justext", self._warm_justext)
        self._step("selectolax", self._warm_selectolax)
        self._step("htmldate", self._warm_htmldate)
        self._step("dateparser", self._warm_dateparser)
        self._step("textstat", self._warm_textstat)
        self._step("pymupdf", self._warm_pymupdf)
        self._step("babel", self._warm_babel)
        self._step("tzlocal", self._warm_tzlocal)
        self._step("pyphen", self._warm_pyphen)
        self._step("curl_cffi", self._warm_curl_cffi)
        self._step("entity_patterns", self._warm_entity_patterns)
        self._step("lang_stopword_map", self._warm_lang_map)
        self._step("api_router", self._warm_api_router)
        self._step("se_api", self._warm_se_api)
        self._step("config_hash", self._warm_config_hash)
        elapsed = time.monotonic() - self.t_start
        failed = [k for k, v in self.results.items() if not v.get("ok")]
        _log("preloader finished in %.3fs (failed=%d)", elapsed, len(failed))
        self.done = True
        return self.results

    def _warm_regexes(self):
        for rx in (_WS_RE, _CTRL_RE, _SENT_RE, _WORD_RE, _URL_RE, _CJK_RE,
                   _TITLE_TOKEN_RE):
            rx.search("warmup")

    def _warm_stopwords(self):
        for _lang, stopset in _STOPWORDS_BY_LANG.items():
            _ = len(stopset)

    def _warm_tld(self):
        for probe in ("example.com", "en.wikipedia.org", "co.uk",
                       "example.co.jp"):
            _tld_mod.get_tld(probe, fix_protocol=True, fail_silently=True)

    def _warm_trafilatura(self):
        html = ("<html><head><title>T</title></head><body><article><h1>H</h1>"
                "<p>" + ("warm content sentence. " * 60) + "</p></article>"
                "</body></html>")
        bare_extraction(html, url="https://example.com/",
                        include_comments=False, include_tables=True,
                        favor_recall=True, with_metadata=True)
        trafilatura_extract(html, url="https://example.com/",
                            favor_recall=True)

    def _warm_justext(self):
        html = ("<html><body><p>" + ("warm content sentence. " * 40)
                + "</p></body></html>").encode("utf-8")
        justext.justext(html, justext.get_stoplist("English"))

    def _warm_selectolax(self):
        tree = LexborHTMLParser("<html><body><p>warm</p></body></html>")
        _ = tree.css_first("p")
        _ = tree.css("p")

    def _warm_htmldate(self):
        find_date("<html><body><time datetime='2020-01-01'>x</time></body></html>",
                  original_date=True, extensive_search=False,
                  outputformat="%Y-%m-%d")

    def _warm_dateparser(self):
        try:
            dateparser_parse("2020-01-01", languages=["en"])
        except Exception:
            pass
        try:
            dateutil_parser.parse("2020-01-01")
        except Exception:
            pass

    def _warm_textstat(self):
        sample = "The quick brown fox jumps over the lazy dog. " * 20
        for fn in (textstat.lexicon_count, textstat.sentence_count,
                    textstat.syllable_count, textstat.flesch_reading_ease,
                    textstat.flesch_kincaid_grade, textstat.gunning_fog,
                    textstat.smog_index,
                    textstat.automated_readability_index,
                    textstat.coleman_liau_index,
                    textstat.dale_chall_readability_score,
                    textstat.difficult_words):
            try:
                fn(sample)
            except Exception:
                pass
        try:
            textstat.text_standard(sample, float_output=False)
        except Exception:
            pass

    def _warm_pymupdf(self):
        try:
            doc = pymupdf.open()
            page = doc.new_page()
            page.insert_text((72, 72), "warm")
            _ = doc.tobytes()
            doc.close()
        except Exception:
            pass

    def _warm_babel(self):
        try:
            Locale.parse("en")
            Locale.parse("de")
        except Exception:
            pass

    def _warm_tzlocal(self):
        try:
            get_localzone()
        except Exception:
            pass

    def _warm_pyphen(self):
        _get_pyphen()

    def _warm_curl_cffi(self):
        try:
            from curl_cffi.requests import Session
            s = Session(impersonate="chrome136", default_headers=False)
            s.close()
        except Exception:
            pass

    def _warm_entity_patterns(self):
        for pat in _ENTITY_PATTERNS.values():
            pat.search("warmup")

    def _warm_lang_map(self):
        _ = AGENT_KEYWORD_LANGUAGES

    def _warm_api_router(self):
        try:
            import api_router  # noqa: F401
        except ImportError:
            pass

    def _warm_se_api(self):
        try:
            import se_api  # noqa: F401
        except ImportError:
            pass

    def _warm_config_hash(self):
        _config_hash()

    def report(self):
        lines = []
        for name, r in self.results.items():
            status = "ok" if r.get("ok") else "FAIL"
            lines.append(f"  {name:20s} {status:5s} {r.get('elapsed', 0):>7.4f}s")
            if not r.get("ok"):
                lines.append(f"    error: {r.get('error')}")
        return "\n".join(lines)


_PRELOADER = Preloader()


def preload(force=False):
    if force or not _PRELOADER.done:
        return _PRELOADER.load()
    return _PRELOADER.results


# ============================================================================
#  MODULE CONSTANTS
# ============================================================================

_WS_RE = regex.compile(r"\s+")
_CTRL_RE = regex.compile(r"[\p{C}\p{Zl}\p{Zp}]+")
_SENT_RE = regex.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(])")
_WORD_RE = regex.compile(r"\p{L}{3,}")
_URL_RE = regex.compile(r"https?://[^\s<>\"']+")
_CJK_RE = regex.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")
_TITLE_TOKEN_RE = regex.compile(r"\b[\w\-']{3,}\b")

_SKIP_HEADINGS = frozenset((
    "references", "external links", "see also", "notes",
    "further reading", "bibliography", "sources", "citations",
    "footnotes", "navigation",
))

_ABBREV_GUARD = (
    "Mr.", "Mrs.", "Ms.", "Dr.", "Prof.", "Sr.", "Jr.", "St.",
    "vs.", "etc.", "eg.", "ie.", "Fig.", "No.", "Vol.",
)

_CLEANER = Cleaner(
    scripts=True, javascript=True, comments=True, style=True,
    links=False, meta=False, page_structure=False,
    embedded=False, frames=False, forms=False, safe_attrs_only=False,
)

_PII_PATTERNS = {
    "EMAIL": regex.compile(r"\b[\w.+\-]+@[\w\-]+\.[\w.\-]+\b"),
    "PHONE": regex.compile(r"\+?\d[\d\s().\-]{7,}\d"),
    "SSN": regex.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "CC": regex.compile(r"\b(?:\d[ \-]?){13,19}\b"),
    "IP": regex.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}

_ENTITY_PATTERNS = {
    "EMAIL": _PII_PATTERNS["EMAIL"],
    "URL": _URL_RE,
    "MONEY": regex.compile(r"(?:\$|€|£|¥)\s?\d[\d,.]*"),
    "PERCENT": regex.compile(r"\b\d+(?:\.\d+)?\s?%"),
    "DATE": regex.compile(r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b"),
    "YEAR": regex.compile(r"\b(?:19|20)\d{2}\b"),
    "PHONE": _PII_PATTERNS["PHONE"],
    "PERSON": regex.compile(r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,}){1,2}\b"),
    "ORG": regex.compile(
        r"\b(?:[A-Z][a-zA-Z]{1,}\s){1,4}"
        r"(?:Inc|Ltd|LLC|Corp|GmbH|Co|SA|AG|Foundation|Institute|University|"
        r"Ministry|Agency|Bureau|Council|Committee|Association|Organization|"
        r"Organisation|Group|Holdings)\b\.?"
    ),
}

_STOPWORDS_EN = frozenset("""
a about above after again against all am an and any are aren't as at be because
been before being below between both but by can't cannot could couldn't did
didn't do does doesn't doing don't down during each few for from further had
hadn't has hasn't have haven't having he he'd he'll he's her here here's hers
herself him himself his how how's i i'd i'll i'm i've if in into is isn't it
it's its itself let's me more most mustn't my myself no nor not of off on once
only or other ought our ours ourselves out over own same shan't she she'd
she'll she's should shouldn't so some such than that that's the their theirs
them themselves then there there's these they they'd they'll they're they've
this those through to too under until up very was wasn't we we'd we'll we're
we've were weren't what what's when when's where where's which while who who's
whom why why's with won't would wouldn't you you'd you'll you're you've your
yours yourself yourselves will just don should now
""".split())

_STOPWORDS_BY_LANG = {
    "en": _STOPWORDS_EN,
    "de": frozenset("der die das und oder aber ist sind war waren ein eine einen einem eines dem den mit von zu auf für über unter nach bei aus durch".split()),
    "fr": frozenset("le la les un une des et ou mais est sont était étaient avec de pour par sur dans sous entre vers chez sans".split()),
    "es": frozenset("el la los las un una unos unas y o pero es son era eran con de por para sobre bajo entre hacia sin".split()),
    "it": frozenset("il la i le un uno una e o ma è sono era erano con di per su sotto tra verso senza".split()),
    "pt": frozenset("o a os as um uma uns umas e ou mas é são era eram com de por para sobre sob entre até sem".split()),
    "nl": frozenset("de het een en of maar is zijn was waren met van voor op onder tussen naar zonder".split()),
    "ru": frozenset("и в во не что он на я с со как а то все она так его но да ты к у же вы за бы по только".split()),
    "zh": frozenset("的 了 和 是 就 都 而 及 与 着 或 一个 我们 他们 它们 这个 那个 什么 怎么 为什么".split()),
    "ja": frozenset("の に は を た が で て と し れ さ ある いる も する から な こと として い や れる など なっ ない この ため その あっ よう また もの という あり まで られ なる へ か だ これ によって により おり より による ず なり られる".split()),
}

_PYPHEN_DIC = None

MOS_TOTAL_TIMEOUT = 25.0
MOS_PER_SERVICE_TIMEOUT = 15.0
MOS_MIN_WORDS_ACCEPT = 30
MOS_FAST_ACCEPT_WORDS = 300


def _get_pyphen():
    global _PYPHEN_DIC
    if _PYPHEN_DIC is None:
        try:
            _PYPHEN_DIC = pyphen.Pyphen(lang="en_US")
        except Exception:
            _PYPHEN_DIC = False
    return _PYPHEN_DIC if _PYPHEN_DIC is not False else None


_PERSONAL_NAME_FIRST = frozenset("""
james john robert michael william david richard joseph thomas charles
christopher daniel matthew anthony donald mark paul steven andrew kenneth
george joshua kevin brian edward ronald timothy jason jeffrey ryan jacob
gary nicholas eric jonathan stephen larry justin scott brandon benjamin
samuel gregory frank alexander raymond patrick jack dennis jerry tyler
aaron jose adam henry nathan douglas zachary peter kyle ethan walter
mary patricia jennifer linda elizabeth barbara susan jessica sarah karen
nancy lisa margaret betty sandra ashley dorothy kimberly emily donna
michelle carol amanda melissa deborah stephanie rebecca laura sharon
cynthia kathleen amy angela shirley anna brenda pamela emma nicole helen
samantha katherine christine debra rachel carolyn janet catherine maria
heather diane ruth julie olivia joyce virginia victoria kelly lauren
christina joan evelyn judith megan andrea cheryl hannah jacqueline martha
mohammed muhammad ahmed ali omar hassan hussein fatima aisha layla
wei li zhang wang chen liu yang zhao huang zhou wu xu sun ma zhu hu guo
he gao lin luo zheng liang xie song tang han feng deng cao peng zeng
haruto yuto sota yuki hayato haru kaito riku takumi kenta daiki
min-jun seo-jun do-yun ji-ho ye-jun ha-eun seo-yeon ji-woo soo-ah min-seo
""".split())


# ============================================================================
#  UTILITIES
# ============================================================================

def _norm_ws(s):
    if not s:
        return ""
    return _WS_RE.sub(" ", _CTRL_RE.sub(" ", s)).strip()


def _attr(node, name, default=""):
    if node is None:
        return default
    try:
        v = node.attributes.get(name, default)
        return v if v is not None else default
    except Exception:
        return default


def _urljoin_safe(base, href):
    if not href:
        return ""
    try:
        return urljoin(base, href)
    except Exception:
        return href


def _sentence_split(text):
    if not text:
        return []
    text = _WS_RE.sub(" ", text)
    parts = _SENT_RE.split(text)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if out and out[-1].endswith(_ABBREV_GUARD):
            out[-1] = out[-1] + " " + p
        else:
            out.append(p)
    return out


def _token_count(text):
    if not text:
        return 0
    words = text.count(" ") + text.count("\n") + 1
    cjk = len(_CJK_RE.findall(text))
    return int(words * AGENT_TOKEN_COUNT_RATIO) + int(cjk / 1.5)


def _decode_body(body, headers):
    ct = ""
    try:
        ct = (headers or {}).get("content-type", "") or ""
    except Exception:
        pass
    m = regex.search(r"charset=([\w\-]+)", ct, regex.I)
    if m:
        try:
            return body.decode(m.group(1), "replace")
        except LookupError:
            pass
    return body.decode(ENCODING_FALLBACK, "replace")


def _safe_parse_xml(data):
    try:
        return SafeET.fromstring(data)
    except Exception:
        try:
            return etree.fromstring(data)
        except Exception:
            return None


def _tld_of(url):
    try:
        host = urlparse(url).netloc
        return _tld_mod.get_tld(host, fix_protocol=True, fail_silently=True) or ""
    except Exception:
        return ""


def _host_of(url):
    try:
        return urlparse(url).netloc
    except Exception:
        return ""


def _capped_findall(pattern, text, cap):
    if not text:
        return []
    if len(text) > cap:
        text = text[:cap]
    try:
        return pattern.findall(text)
    except Exception:
        return []


# ============================================================================
#  HASHING
# ============================================================================

def _content_hash(text):
    if not text:
        return ""
    return hashlib.blake2b(text.encode("utf-8", "ignore"), digest_size=16).hexdigest()


def _hash_token(tok):
    return int.from_bytes(
        hashlib.blake2b(tok.encode("utf-8", "ignore"), digest_size=8).digest(),
        "big",
    )


def _simhash64(tokens):
    if not tokens:
        return 0
    v = [0] * 64
    for tok in tokens:
        h = _hash_token(tok)
        for i in range(64):
            v[i] += 1 if (h >> i) & 1 else -1
    out = 0
    for i in range(64):
        if v[i] > 0:
            out |= 1 << i
    return out


def _simhash_from_text(text):
    if not text:
        return 0
    toks = [t.lower() for t in _capped_findall(_WORD_RE, text, REGEX_WORD_CAP)]
    return _simhash64(toks)


def _hamming(a, b):
    return (a ^ b).bit_count()


def _idempotency_key(url, profile_family=""):
    return hashlib.blake2b(
        f"{url}|{profile_family}|{EXTRACTOR_VERSION}".encode("utf-8", "ignore"),
        digest_size=16,
    ).hexdigest()


@lru_cache(maxsize=1)
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
#  QUALITY METRICS
# ============================================================================

_ZERO_QUALITY = {
    "word_count": 0, "sentence_count": 0, "syllable_count": 0,
    "char_count": 0, "reading_time_seconds": 0,
    "flesch_reading_ease": -1.0, "flesch_kincaid_grade": -1.0,
    "gunning_fog": -1.0, "smog_index": -1.0,
    "automated_readability_index": -1.0, "coleman_liau_index": -1.0,
    "dale_chall_score": -1.0, "text_standard": "",
    "difficulty": 0,
}


def _quality_metrics(text):
    zero = dict(_ZERO_QUALITY)
    if not text or len(text) < 80:
        return zero
    try:
        words = textstat.lexicon_count(text)
    except Exception:
        words = len(text.split())
    if words < QUALITY_MIN_WORDS:
        zero["word_count"] = words
        return zero

    def _safe(fn):
        try:
            return fn(text)
        except Exception:
            return -1.0

    try:
        sentences = textstat.sentence_count(text)
    except Exception:
        sentences = max(1, text.count("."))
    if sentences < QUALITY_MIN_SENTENCES:
        zero["word_count"] = words
        zero["sentence_count"] = sentences
        return zero
    try:
        syllables = textstat.syllable_count(text)
    except Exception:
        syllables = 0
    try:
        standard = textstat.text_standard(text, float_output=False)
    except Exception:
        standard = ""
    return {
        "word_count": words,
        "sentence_count": sentences,
        "syllable_count": syllables,
        "char_count": len(text),
        "reading_time_seconds": round(words / 200 * 60, 1),
        "flesch_reading_ease": _safe(textstat.flesch_reading_ease),
        "flesch_kincaid_grade": _safe(textstat.flesch_kincaid_grade),
        "gunning_fog": _safe(textstat.gunning_fog),
        "smog_index": _safe(textstat.smog_index),
        "automated_readability_index": _safe(textstat.automated_readability_index),
        "coleman_liau_index": _safe(textstat.coleman_liau_index),
        "dale_chall_score": _safe(textstat.dale_chall_readability_score),
        "text_standard": standard,
        "difficulty": _safe(textstat.difficult_words),
    }


def _should_run_nlp(text, quality):
    if not NLP_COMPLEXITY_GATE_ENABLED:
        return bool(text)
    if not text:
        return False
    if quality.get("word_count", 0) < NLP_MIN_WORDS:
        return False
    if quality.get("sentence_count", 0) < NLP_MIN_SENTENCES:
        return False
    return True


def _extraction_score(text, title, sections, boiler_ratio):
    if not EXTRACTION_SCORING_ENABLED or not text:
        return -1.0
    words = len(text.split())
    if words < 30:
        return -1.0
    score = 0.0
    score += min(words / EXTRACTION_SCORE_LENGTH_CAP, 1.0) * EXTRACTION_SCORE_LENGTH_WEIGHT
    score += (1.0 - min(boiler_ratio, 1.0)) * EXTRACTION_SCORE_BOILER_WEIGHT
    try:
        flesch = textstat.flesch_reading_ease(text)
        lo, hi = EXTRACTION_SCORE_FLESCH_BEST
        lo2, hi2 = EXTRACTION_SCORE_FLESCH_OK
        if lo <= flesch <= hi:
            score += EXTRACTION_SCORE_FLESCH_WEIGHT
        elif lo2 <= flesch <= hi2:
            score += EXTRACTION_SCORE_FLESCH_WEIGHT * 0.5
    except Exception:
        pass
    if title and title.lower() in text.lower():
        score += EXTRACTION_SCORE_TITLE_WEIGHT
    if sections:
        score += (min(len(sections) / EXTRACTION_SCORE_SECTIONS_CAP, 1.0)
                  * EXTRACTION_SCORE_SECTIONS_WEIGHT)
    if text.count(".") > 5:
        score += EXTRACTION_SCORE_PUNCT_WEIGHT
    return score


# ============================================================================
#  CHUNKING
# ============================================================================

def chunk_text(text, size=None, overlap=None, min_size=None):
    if not AGENT_CHUNK_ENABLED or not text:
        return []
    size = size or AGENT_CHUNK_SIZE_TOKENS
    overlap = overlap if overlap is not None else AGENT_CHUNK_OVERLAP_TOKENS
    min_size = min_size or AGENT_CHUNK_MIN_TOKENS
    sentences = _sentence_split(text)
    if not sentences:
        return []
    chunks = []
    cur, cur_len = [], 0
    for s in sentences:
        tok = _token_count(s)
        if cur_len + tok > size and cur:
            chunks.append(" ".join(cur))
            keep, kept = [], 0
            for s2 in reversed(cur):
                kept += _token_count(s2)
                if kept > overlap:
                    break
                keep.insert(0, s2)
            cur, cur_len = keep, kept
        cur.append(s)
        cur_len += tok
        if len(chunks) >= AGENT_CHUNK_MAX_CHUNKS_PER_DOC:
            break
    if cur and cur_len >= min_size:
        chunks.append(" ".join(cur))
    return chunks


def _dedup_chunks(chunks):
    if not CHUNK_DEDUP_ENABLED or len(chunks) < 3:
        return chunks
    sigs = [_simhash64(c.lower().split()) for c in chunks]
    keep = [True] * len(chunks)
    for i in range(len(chunks)):
        if not keep[i]:
            continue
        for j in range(i + 1, len(chunks)):
            if not keep[j]:
                continue
            if _hamming(sigs[i], sigs[j]) <= CHUNK_DEDUP_HAMMING:
                if CHUNK_DEDUP_PREFER_LONGER:
                    if len(chunks[i]) < len(chunks[j]):
                        keep[i] = False
                        break
                    else:
                        keep[j] = False
                else:
                    keep[j] = False
    return [c for c, k in zip(chunks, keep) if k]


def _attach_context(chunks, parent_url, parent_title, sections=None):
    if not chunks:
        return []
    if AGENT_CHUNK_OFFSET_AWARE and sections:
        chunks = _dedup_chunks(chunks)
    heading_map = []
    if sections:
        for sec in sections:
            heading_map.append(sec.get("heading", ""))
            for sub in sec.get("subsections", []) or []:
                heading_map.append(sub.get("heading", ""))
    total = len(chunks)
    out = []
    for i, c in enumerate(chunks):
        ctx = ""
        if AGENT_CHUNK_INCLUDE_HEADING_CONTEXT and heading_map:
            idx = min(int(i * len(heading_map) / max(total, 1)), len(heading_map) - 1)
            ctx = heading_map[idx]
        out.append({
            "index": i,
            "total": total,
            "text": c,
            "token_count": _token_count(c),
            "heading_context": ctx if ctx else None,
            "parent_url": parent_url if AGENT_CHUNK_INCLUDE_URL_CONTEXT else None,
            "parent_title": parent_title,
            "offset": None,
        })
    return out


# ============================================================================
#  NLP-LITE
# ============================================================================

def extract_keywords(text, max_k=None, language="en"):
    if not AGENT_KEYWORD_EXTRACT_ENABLED or not text:
        return []
    max_k = max_k or AGENT_KEYWORD_MAX_PER_DOC
    words = [w.lower() for w in _capped_findall(_WORD_RE, text, REGEX_WORD_CAP)]
    if not words:
        return []
    stop = _STOPWORDS_BY_LANG.get(language, _STOPWORDS_EN)
    words = [w for w in words if w not in stop and len(w) >= AGENT_KEYWORD_MIN_LENGTH]
    if not words:
        return []
    total = len(words)
    unigrams = Counter(words)
    scores = {w: c / total for w, c in unigrams.items()}
    for n in range(2, AGENT_TOPIC_NGRAM_MAX + 1):
        gram_counter = Counter(tuple(words[i:i + n]) for i in range(len(words) - n + 1))
        for gram, c in gram_counter.items():
            if c < 2:
                continue
            key = " ".join(gram)
            scores[key] = (c / total) * math.log(1 + c)
    ranked = sorted(scores.items(), key=lambda x: -x[1])[:max_k]
    return [{"term": k, "score": round(v, 6)} for k, v in ranked]


def extract_topics(text, max_topics=None, language="en"):
    if not AGENT_TOPIC_EXTRACT_ENABLED or not text:
        return []
    max_topics = max_topics or AGENT_TOPIC_MAX_PER_DOC
    kw = extract_keywords(text, max_k=max_topics * 3, language=language)
    out = []
    for item in kw:
        if " " in item["term"] and item["score"] >= AGENT_TOPIC_MIN_SCORE:
            out.append(item)
        if len(out) >= max_topics:
            break
    return out


def _entity_frequency(body, value):
    if not ENTITY_FREQUENCY_FILTER_ENABLED:
        return 1
    try:
        return body.count(value)
    except Exception:
        return 0


def _entity_near_reporting_verb(body, value):
    if not ENTITY_REPORTING_VERBS:
        return False
    lo = body.lower()
    vlo = value.lower()
    idx = 0
    while True:
        idx = lo.find(vlo, idx)
        if idx < 0:
            return False
        window = lo[max(0, idx - ENTITY_REPORTING_WINDOW):
                    idx + len(vlo) + ENTITY_REPORTING_WINDOW]
        for verb in ENTITY_REPORTING_VERBS:
            if verb in window:
                return True
        idx += len(vlo)


def extract_entities(text, max_n=None, body_for_freq=None):
    if not AGENT_ENTITY_EXTRACT_ENABLED or not text:
        return []
    max_n = max_n or AGENT_ENTITY_MAX_PER_DOC
    body = body_for_freq if body_for_freq is not None else text
    seen = set()
    out = []

    def _add(kind, value, weight=1.0):
        if len(value) < AGENT_ENTITY_MIN_LENGTH:
            return
        key = value.lower() if AGENT_ENTITY_CASE_INSENSITIVE_DEDUP else value
        if AGENT_ENTITY_DEDUP and key in seen:
            return
        seen.add(key)
        out.append({"type": kind, "value": value, "weight": round(weight, 3)})

    for kind, pat in _ENTITY_PATTERNS.items():
        for m in pat.finditer(text):
            val = m.group(0).strip()
            if kind == "PERSON":
                tokens = val.split()
                if not tokens:
                    continue
                first = tokens[0].lower()
                weight = (ENTITY_FIRSTNAME_WEIGHT if first in _PERSONAL_NAME_FIRST
                          else ENTITY_NON_FIRSTNAME_WEIGHT)
                if ENTITY_FREQUENCY_FILTER_ENABLED:
                    freq = _entity_frequency(body, val)
                    near = _entity_near_reporting_verb(body, val)
                    if not (freq >= ENTITY_MIN_OCCURRENCES or near):
                        continue
                if ENTITY_BOUNDARY_ENABLED:
                    start = max(0, m.start() - 1)
                    end = min(len(text), m.end() + 1)
                    if start > 0 and text[start].isalpha():
                        continue
                    if end < len(text) and text[end].isalpha():
                        continue
                _add(kind, val, weight)
            elif kind == "ORG":
                if not any(suffix in val for suffix in ENTITY_ORG_SUFFIXES):
                    continue
                _add(kind, val, 1.0)
            else:
                _add(kind, val, 1.0)
            if len(out) >= max_n:
                return out
    return out


def summarize(text, max_sentences=None):
    if not AGENT_SUMMARY_ENABLED or not text:
        return ""
    max_sentences = max_sentences or AGENT_SUMMARY_TOP_SENTENCES
    sents = _sentence_split(text)
    if len(sents) <= max_sentences:
        return " ".join(sents)
    freq = Counter(w.lower() for w in _capped_findall(_WORD_RE, text, REGEX_WORD_CAP))
    for w in list(freq):
        if w in _STOPWORDS_EN:
            del freq[w]
    if not freq:
        return " ".join(sents[:max_sentences])
    top = max(freq.values())
    scores = []
    for i, s in enumerate(sents):
        ws = _WORD_RE.findall(s.lower())
        if not ws:
            continue
        score = sum(freq.get(w, 0) for w in ws) / (top * len(ws) + 1)
        if i < 3:
            score *= 1.3
        if i == len(sents) - 1:
            score *= 0.85
        scores.append((score, i, s))
    if not scores:
        return " ".join(sents[:max_sentences])
    scores.sort(reverse=True)
    picked = sorted(scores[:max_sentences], key=lambda x: x[1])
    return " ".join(s for _, _, s in picked)


def redact_pii(text):
    if not AGENT_PII_REDACT_ENABLED or not text:
        return text
    out = text
    if AGENT_PII_REDACT_EMAIL:
        out = _PII_PATTERNS["EMAIL"].sub(AGENT_PII_REDACT_PLACEHOLDER, out)
    if AGENT_PII_REDACT_PHONE:
        out = _PII_PATTERNS["PHONE"].sub(AGENT_PII_REDACT_PLACEHOLDER, out)
    if AGENT_PII_REDACT_SSN:
        out = _PII_PATTERNS["SSN"].sub(AGENT_PII_REDACT_PLACEHOLDER, out)
    if AGENT_PII_REDACT_CREDIT_CARD:
        out = _PII_PATTERNS["CC"].sub(AGENT_PII_REDACT_PLACEHOLDER, out)
    if AGENT_PII_REDACT_IP:
        out = _PII_PATTERNS["IP"].sub(AGENT_PII_REDACT_PLACEHOLDER, out)
    return out


# ============================================================================
#  PARSER HELPERS
# ============================================================================

def _first_text(tree, selector):
    try:
        n = tree.css_first(selector)
    except Exception:
        n = None
    if n is None:
        return ""
    try:
        return _norm_ws(n.text(strip=True))
    except Exception:
        return ""


def _first_long_p(tree, min_len=60):
    try:
        for p in tree.css("p"):
            t = _norm_ws(p.text(strip=True))
            if len(t) >= min_len:
                return t
    except Exception:
        pass
    return ""


def _find_article_root(tree):
    for sel in ARTICLE_ROOT_SELECTORS:
        try:
            n = tree.css_first(sel)
        except Exception:
            n = None
        if n is None:
            continue
        try:
            txt = n.text(strip=True)
        except Exception:
            continue
        if txt and len(txt) >= ARTICLE_ROOT_MIN_CHARS:
            return n, sel
    return None, None


def _extract_nav(tree):
    primary, help_links, actions = [], [], []
    seen = set()
    for a in tree.css("nav a[href], header a[href], [role=navigation] a[href]"):
        href = _attr(a, "href").strip()
        text = _norm_ws(a.text(strip=True))
        if not href or not text:
            continue
        key = (text, href)
        if key in seen:
            continue
        seen.add(key)
        item = {"text": text, "url": href}
        parent = a.parent
        pid = ""
        depth = 0
        while parent is not None and depth < 6 and not pid:
            pid = _attr(parent, "id")
            parent = parent.parent
            depth += 1
        low = pid.lower()
        if "help" in low:
            help_links.append(item)
        elif "action" in low or "donate" in href.lower():
            actions.append(item)
        else:
            primary.append(item)
        if len(primary) + len(help_links) + len(actions) > 500:
            break
    return {"primary": primary, "help": help_links, "actions": actions}


def _extract_announcement(tree):
    for sel in (".mw-message-box", ".siteNotice", ".announcement",
                "div[role=alert]", "#centralNotice"):
        try:
            n = tree.css_first(sel)
        except Exception:
            n = None
        if n is None:
            continue
        a = None
        try:
            a = n.css_first("a[href]")
        except Exception:
            pass
        img = None
        try:
            img = n.css_first("img")
        except Exception:
            pass
        return {
            "text": _norm_ws(n.text(strip=True)),
            "url": _attr(a, "href") if a is not None else None,
            "image": _attr(img, "src") if img is not None else None,
        }
    return None


def _extract_toc(tree):
    out, seen = [], set()
    for a in tree.css("#toc a[href^='#'], .toc a[href^='#'], "
                      ".vector-toc a[href^='#'], [role=navigation] a[href^='#']"):
        href = _attr(a, "href")
        text = _norm_ws(a.text(strip=True))
        if not text or not href:
            continue
        key = (text, href)
        if key in seen:
            continue
        seen.add(key)
        out.append({"text": text, "anchor": href})
    return out


def _extract_article(tree, url, raw_html=None):
    heading = _first_text(tree, "h1") or _first_text(tree, ".firstHeading")
    tabs = []
    for a in tree.css(".vector-tabs a[href], #p-views a[href], "
                      "#p-namespaces a[href], [role=tab] a[href]"):
        href = _attr(a, "href").strip()
        text = _norm_ws(a.text(strip=True))
        if not href or not text:
            continue
        tabs.append({"text": text, "url": _urljoin_safe(url, href)})
    notice = ""
    for sel in (".mw-indicators", ".protection-icon", ".mbox-text", ".notice"):
        t = _first_text(tree, sel)
        if t:
            notice = t
            break
    lead_image = None
    for sel in ("figure img", "table.infobox img", "img.thumbimage",
                "article img", "img[src]"):
        try:
            img = tree.css_first(sel)
        except Exception:
            img = None
        if img is None:
            continue
        src = _attr(img, "src") or _attr(img, "data-src")
        if not src:
            continue
        lead_image = {
            "alt": _attr(img, "alt"),
            "url": _urljoin_safe(url, src),
            "image": _urljoin_safe(url, src),
        }
        break
    intro = _first_long_p(tree, 80)
    sections = _extract_sections(tree)
    refs = _extract_references(tree, url)
    related = None
    for a in tree.css("a[href]"):
        href = _attr(a, "href")
        if "commons.wikimedia" in href:
            related = {"text": _norm_ws(a.text(strip=True)), "url": href,
                       "image": None}
            break
    cats = []
    seen_cat = set()
    for a in tree.css("#catlinks a[href], .catlinks a[href], .categories a[href]"):
        href = _attr(a, "href")
        text = _norm_ws(a.text(strip=True))
        if not text or not href:
            continue
        key = (text, href)
        if key in seen_cat:
            continue
        seen_cat.add(key)
        cats.append({"text": text, "url": _urljoin_safe(url, href)})
    pub, mod = _extract_dates(raw_html or "", tree)
    try:
        tz_name = str(get_localzone())
    except Exception:
        tz_name = "UTC"
    return {
        "heading": heading,
        "tabs": tabs,
        "notice": notice,
        "lead_image": lead_image,
        "intro": intro,
        "sections": sections,
        "references": refs,
        "related_media": related,
        "categories": cats,
        "published_date": pub,
        "updated_date": mod,
        "timezone": tz_name,
    }


def _extract_sections(tree):
    sections = []
    current = None
    for el in tree.css("h2, h3, h4, p, ul, ol"):
        tag = el.tag
        if tag in ("h2", "h3", "h4"):
            text = _norm_ws(el.text(strip=True))
            if not text:
                continue
            low = text.lower().rstrip(":")
            if low in _SKIP_HEADINGS:
                if tag == "h2":
                    if current:
                        sections.append(current)
                    current = None
                continue
            if tag == "h2":
                if current:
                    sections.append(current)
                current = {"heading": text[:SECTION_MAX_CHARS],
                           "text": "", "subsections": []}
            else:
                if current is None:
                    current = {"heading": "", "text": "", "subsections": []}
                current["subsections"].append(
                    {"heading": text[:SECTION_MAX_CHARS], "text": ""}
                )
            continue
        if current is None:
            continue
        text = _norm_ws(el.text(strip=True))
        if not text:
            continue
        if current["subsections"]:
            sub = current["subsections"][-1]
            sub["text"] = (sub["text"] + " " + text).strip() if sub["text"] else text
        else:
            current["text"] = (current["text"] + " " + text).strip() if current["text"] else text
    if current:
        sections.append(current)
    return sections


def _extract_references(tree, url):
    refs = []
    seen = set()
    idx = 0
    for li in tree.css(".references li, ol.references li, cite, .reflist li, .csl-entry"):
        text = _norm_ws(li.text(strip=True))
        if not text or len(text) < 8:
            continue
        if text in seen:
            continue
        seen.add(text)
        idx += 1
        a = None
        try:
            a = li.css_first("a[href]")
        except Exception:
            pass
        ref = {"number": idx, "text": text}
        if a is not None:
            href = _attr(a, "href")
            if href:
                ref["url"] = _urljoin_safe(url, href)
        refs.append(ref)
    return refs


def _extract_metadata(tree, url):
    meta = {}
    for m in tree.css("meta"):
        name = _attr(m, "name") or _attr(m, "property")
        content = _attr(m, "content")
        if name and content:
            meta[name] = content
    lang = ""
    try:
        html_el = tree.css_first("html")
        if html_el is not None:
            lang = _attr(html_el, "lang")
    except Exception:
        pass
    out = {
        "language": lang or meta.get("og:locale") or None,
        "description": meta.get("description") or meta.get("og:description"),
        "site_name": meta.get("og:site_name"),
        "published": meta.get("article:published_time") or meta.get("datePublished"),
        "last_edited": (meta.get("article:modified_time")
                        or meta.get("og:updated_time")
                        or meta.get("dateModified")),
        "generator": meta.get("generator"),
        "license": meta.get("license") or meta.get("og:license"),
        "author": meta.get("author") or meta.get("article:author"),
    }
    return {k: v for k, v in out.items() if v}


def _extract_dates(html, tree):
    pub = None
    mod = None
    if html and len(html) > 200:
        try:
            pub = find_date(html, original_date=True, extensive_search=True,
                            outputformat="%Y-%m-%d")
        except Exception:
            pass
        if pub is None:
            try:
                mod = find_date(html, original_date=False, extensive_search=True,
                                outputformat="%Y-%m-%d")
            except Exception:
                pass
    if pub is None:
        for sel in ("meta[property='article:published_time']",
                    "meta[name='date']", "meta[name='pubdate']",
                    "time[datetime]"):
            try:
                n = tree.css_first(sel)
            except Exception:
                n = None
            if n is None:
                continue
            val = _attr(n, "content") or _attr(n, "datetime")
            if not val:
                continue
            try:
                dt = dateparser_parse(val, languages=["en"]) or dateutil_parser.parse(val)
                if dt:
                    pub = dt.date().isoformat()
                    break
            except Exception:
                continue
    return pub, mod


def _extract_footer(tree):
    out, seen = [], set()
    for a in tree.css("footer a[href], #footer a[href], .footer a[href], "
                      "[role=contentinfo] a[href]"):
        href = _attr(a, "href").strip()
        text = _norm_ws(a.text(strip=True))
        if not href or not text:
            continue
        key = (text, href)
        if key in seen:
            continue
        seen.add(key)
        out.append({"text": text, "url": href})
    return out


def _extract_links(tree, url):
    out, seen = [], set()
    for a in tree.css("a[href]"):
        href = _attr(a, "href").strip()
        if not href:
            continue
        low = href.lower()
        if low.startswith(("#", "javascript:", "mailto:", "tel:", "data:", "blob:")):
            continue
        absolute = _urljoin_safe(url, href)
        try:
            p = urlparse(absolute)
        except Exception:
            continue
        if p.scheme not in ("http", "https") or not p.netloc:
            continue
        key = absolute.split("#", 1)[0]
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
        if len(out) >= MAX_LINKS_PER_PAGE:
            break
    return out


def _extract_canonical(tree, base_url):
    try:
        n = tree.css_first('link[rel="canonical"]')
    except Exception:
        n = None
    if n is None:
        return None
    href = _attr(n, "href")
    return _urljoin_safe(base_url, href) if href else None


def _extract_jsonld(tree):
    out = []
    for script in tree.css('script[type="application/ld+json"]'):
        raw = ""
        try:
            raw = script.text(strip=False) or ""
        except Exception:
            continue
        if not raw.strip():
            continue
        try:
            data = orjson.loads(raw)
        except Exception:
            continue
        if isinstance(data, list):
            out.extend(x for x in data if isinstance(x, dict))
        elif isinstance(data, dict):
            if "@graph" in data and isinstance(data["@graph"], list):
                out.extend(data["@graph"])
            else:
                out.append(data)
    return out


def _extract_og(tree):
    out = {}
    for meta in tree.css("meta[property^='og:'], meta[name^='twitter:']"):
        key = _attr(meta, "property") or _attr(meta, "name")
        val = _attr(meta, "content")
        if key and val:
            out[key] = val
    return out


def _extract_rss_link(tree, base_url):
    for sel in ('link[rel="alternate"][type="application/rss+xml"]',
                'link[rel="alternate"][type="application/atom+xml"]'):
        try:
            n = tree.css_first(sel)
        except Exception:
            n = None
        if n is None:
            continue
        href = _attr(n, "href")
        if href:
            return _urljoin_safe(base_url, href)
    return None


# ============================================================================
#  TEXT EXTRACTORS
# ============================================================================

def _clean_html(html):
    try:
        return _CLEANER.clean_html(html)
    except Exception:
        return html


def _trafilatura_extract(html, url):
    try:
        doc = bare_extraction(
            html, url=url,
            include_comments=False, include_tables=True,
            include_links=True, include_images=True,
            include_formatting=True,
            favor_recall=True, with_metadata=True,
        )
        if doc is None:
            return None
        if hasattr(doc, "as_dict"):
            return doc.as_dict()
        return {k: getattr(doc, k, None) for k in
                ("title", "author", "url", "description", "sitename",
                 "date", "text", "language", "categories", "tags")}
    except Exception:
        return None


def _justext_extract(html_bytes, lang="English"):
    try:
        paras = justext.justext(html_bytes, justext.get_stoplist(lang))
        good = [p.text for p in paras if not p.is_boilerplate]
        bad = [p.text for p in paras if p.is_boilerplate]
        text = "\n\n".join(good)
        ratio = len(bad) / max(1, len(good) + len(bad))
        return text, ratio
    except Exception:
        return "", 1.0


def _selectolax_extract(html, url):
    try:
        tree = LexborHTMLParser(html)
    except Exception:
        return None, "", "", [], []
    title = _first_text(tree, "title") or _first_text(tree, "h1")
    intro = _first_long_p(tree)
    sections = _extract_sections(tree)
    links = _extract_links(tree, url)
    return tree, title, intro, sections, links


# ============================================================================
#  CONTENT HANDLERS
# ============================================================================

def _base_record(url, kind):
    now = time.time()
    return {
        "id": "",
        "url": url,
        "canonical_url": url,
        "domain": _host_of(url),
        "tld": _tld_of(url),
        "title": "",
        "language": None,
        "language_source": None,
        "published_date": None,
        "updated_date": None,
        "crawled_at": now,
        "content_hash": "",
        "simhash": 0,
        "source_signature": "",
        "idempotency_key": _idempotency_key(url),
        "extractor_version": EXTRACTOR_VERSION,
        "config_hash": _config_hash(),
        "license": None,
        "quality": dict(_ZERO_QUALITY),
        "word_count": 0,
        "token_count": 0,
        "char_count": 0,
        "sentence_count": 0,
        "reading_time_seconds": 0,
        "flesch_reading_ease": -1.0,
        "flesch_kincaid_grade": -1.0,
        "gunning_fog": -1.0,
        "smog_index": -1.0,
        "automated_readability_index": -1.0,
        "coleman_liau_index": -1.0,
        "dale_chall_score": -1.0,
        "text_standard": "",
        "difficulty": 0,
        "topics": [],
        "entities": [],
        "keywords": [],
        "summary": "",
        "sections": [],
        "chunks": [],
        "links": [],
        "metadata": {"source_type": kind},
        "provenance": {},
        "content": {
            "site_navigation": {"primary": [], "help": [], "actions": []},
            "announcement": None,
            "table_of_contents": [],
            "article": {
                "heading": "", "tabs": [], "notice": "", "lead_image": None,
                "intro": "", "sections": [], "references": [],
                "related_media": None, "categories": [],
                "published_date": None, "updated_date": None, "timezone": None,
            },
            "metadata": {"source_type": kind},
            "footer_links": [],
        },
        "schema_version": AGENT_SCHEMA_VERSION,
        "kind": kind,
    }


def _fill_record(record, text, title, sections, chunks, meta, article,
                 quality=None, headers=None):
    if len(title) > TITLE_MAX_CHARS:
        title = title[:TITLE_MAX_CHARS]
    record["title"] = title
    record["content"]["article"]["intro"] = (text or "")[:INTRO_MAX_CHARS]
    record["content"]["article"]["sections"] = sections or []
    record["sections"] = sections or []
    record["content"]["article"].update({
        k: v for k, v in (article or {}).items() if v is not None
    })
    record["metadata"] = {**(record.get("metadata") or {}), **(meta or {})}
    record["content"]["metadata"] = record["metadata"]
    q = quality if quality is not None else _quality_metrics(text or "")
    record["quality"] = q
    record["word_count"] = q.get("word_count", 0)
    record["sentence_count"] = q.get("sentence_count", 0)
    record["reading_time_seconds"] = q.get("reading_time_seconds", 0)
    record["flesch_reading_ease"] = q.get("flesch_reading_ease", -1.0)
    record["flesch_kincaid_grade"] = q.get("flesch_kincaid_grade", -1.0)
    record["gunning_fog"] = q.get("gunning_fog", -1.0)
    record["smog_index"] = q.get("smog_index", -1.0)
    record["automated_readability_index"] = q.get("automated_readability_index", -1.0)
    record["coleman_liau_index"] = q.get("coleman_liau_index", -1.0)
    record["dale_chall_score"] = q.get("dale_chall_score", -1.0)
    record["text_standard"] = q.get("text_standard", "")
    record["difficulty"] = q.get("difficulty", 0)
    record["token_count"] = _token_count(text or "")
    record["char_count"] = len(text or "")
    record["content_hash"] = _content_hash(text or "")
    record["id"] = record["content_hash"]
    record["simhash"] = _simhash_from_text(text or "")
    record["chunks"] = chunks or []
    return record


def _adaptive_extract_text(cleaned_html, raw_html, url, title, sections):
    scores = {}
    boiler = 0.5
    traf = _trafilatura_extract(raw_html, url)
    traf_text = ""
    traf_meta = {}
    if traf:
        traf_text = _norm_ws(traf.get("text") or "")
        traf_meta = {k: traf.get(k) for k in
                     ("author", "date", "sitename", "description", "url")}
    if traf_text:
        scores["trafilatura"] = round(
            _extraction_score(traf_text, title, sections, 0.3), 3
        )
    if len(traf_text.split()) >= MOS_FAST_ACCEPT_WORDS:
        return traf_text, 0.2, scores, traf_meta
    je_text, je_boiler = _justext_extract(
        cleaned_html.encode("utf-8", "ignore")
    )
    if je_text:
        scores["justext"] = round(
            _extraction_score(je_text, title, sections, je_boiler), 3
        )
    candidates = []
    if traf_text:
        candidates.append(("trafilatura", traf_text, 0.3))
    if je_text:
        candidates.append(("justext", je_text, je_boiler))
    if len(traf_text.split()) < 200:
        try:
            tree = LexborHTMLParser(cleaned_html)
            para_walk = "\n\n".join(
                _norm_ws(p.text(strip=True)) for p in tree.css("p")
            )
            if para_walk and len(para_walk) > 200:
                scores["selectolax_p"] = round(
                    _extraction_score(para_walk, title, sections, 0.5), 3
                )
                candidates.append(("selectolax_p", para_walk, 0.5))
        except Exception:
            pass
    if not candidates:
        return "", 1.0, scores, traf_meta
    candidates.sort(key=lambda x: scores.get(x[0], -1.0), reverse=True)
    best_name, best_text, boiler = candidates[0]
    return best_text, boiler, scores, traf_meta


def extract_html(html_str, url, headers=None):
    if not html_str:
        rec = _base_record(url, "html")
        rec["error"] = "empty_html"
        return rec, [], False
    cleaned = _clean_html(html_str)
    tree, title, intro, sections, links = _selectolax_extract(cleaned, url)
    if tree is None:
        rec = _base_record(url, "html")
        rec["error"] = "parse_failed"
        return rec, [], False
    meta = _extract_metadata(tree, url)
    og = _extract_og(tree)
    jsonld = _extract_jsonld(tree)
    meta["og"] = og
    meta["jsonld"] = jsonld
    article_root, root_sel = _find_article_root(tree)
    if root_sel:
        meta["article_selector"] = root_sel
    best_text, je_boiler, scores, traf_meta = _adaptive_extract_text(
        cleaned, html_str, url, title, sections
    )
    meta["extraction_scores"] = scores
    if traf_meta.get("author") and not meta.get("author"):
        meta["author"] = traf_meta["author"]
    if traf_meta.get("date") and not meta.get("published"):
        meta["published"] = traf_meta["date"]
    if traf_meta.get("sitename") and not meta.get("site_name"):
        meta["site_name"] = traf_meta["sitename"]
    article = _extract_article(tree, url, raw_html=html_str)
    if not article.get("intro") and intro:
        article["intro"] = intro
    if not article.get("sections"):
        article["sections"] = sections
    record = _base_record(url, "html")
    record["canonical_url"] = _extract_canonical(tree, url) or url
    record["license"] = meta.get("license")
    record["language"] = meta.get("language")
    record["language_source"] = "html_lang" if meta.get("language") else None
    record["published_date"] = article.get("published_date") or meta.get("published")
    record["updated_date"] = article.get("updated_date") or meta.get("last_edited")
    record["source_signature"] = _source_signature(headers)
    quality = _quality_metrics(best_text)
    chunks = _attach_context(chunk_text(best_text), url, title, sections)
    if _should_run_nlp(best_text, quality):
        record["topics"] = extract_topics(best_text)
        record["keywords"] = extract_keywords(best_text)
        record["entities"] = extract_entities(best_text)
        record["summary"] = summarize(best_text)
    record["content"]["site_navigation"] = _extract_nav(tree)
    record["content"]["announcement"] = _extract_announcement(tree)
    record["content"]["table_of_contents"] = _extract_toc(tree)
    record["content"]["footer_links"] = _extract_footer(tree)
    _fill_record(record, best_text, title, sections, chunks, meta, article,
                 quality, headers)
    record["content"]["article"] = {**record["content"]["article"], **article}
    record["links"] = links
    rss = _extract_rss_link(tree, url)
    if rss:
        record["metadata"]["rss_feed"] = rss
    return record, links, False


def extract_pdf(data, url, headers=None):
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as e:
        rec = _base_record(url, "pdf")
        rec["error"] = f"pdf_open: {e!r}"
        return rec, [], False
    parts = []
    pages = 0
    ocr_pages = 0
    truncated = False
    try:
        for page in doc:
            if pages >= PDF_MAX_PAGES:
                truncated = True
                break
            pages += 1
            try:
                if PDF_TEXT_MODE == "blocks":
                    blocks = page.get_text("blocks") or []
                    if isinstance(blocks, list):
                        text = "\n\n".join(
                            b[4] for b in blocks
                            if isinstance(b, (list, tuple)) and len(b) > 4
                        )
                    else:
                        text = str(blocks)
                else:
                    text = page.get_text() or ""
            except Exception:
                text = ""
            if len(text.strip()) < OCR_MIN_TEXT_LEN and ocr_pages < PDF_MAX_OCR_PAGES:
                try:
                    tp = page.get_textpage_ocr(
                        flags=3, language=OCR_LANG, dpi=OCR_DPI, full=True,
                    )
                    ocr = tp.extractText() or ""
                    ocr_pages += 1
                    if len(ocr.strip()) > len(text.strip()):
                        text = ocr
                except Exception:
                    pass
            if text:
                parts.append(text)
    finally:
        try:
            doc.close()
        except Exception:
            pass
    full = "\n\n".join(parts)
    if len(full) > CONTENT_MAX_CHARS:
        full = full[:CONTENT_MAX_CHARS]
    record = _base_record(url, "pdf")
    record["metadata"] = {
        "source_type": "application/pdf",
        "pages": pages,
        "ocr_pages": ocr_pages,
    }
    if truncated:
        record["metadata"]["pdf_truncated"] = True
    quality = _quality_metrics(full)
    sections = [{"heading": "Full Text", "text": full[:SECTION_MAX_CHARS]}] if full else []
    chunks = _attach_context(chunk_text(full), url, "", sections)
    _fill_record(record, full, "", sections, chunks, record["metadata"], {},
                 quality, headers)
    if _should_run_nlp(full, quality):
        record["topics"] = extract_topics(full)
        record["keywords"] = extract_keywords(full)
        record["entities"] = extract_entities(full)
        record["summary"] = summarize(full)
    record["links"] = []
    return record, [], False


def extract_json(data, url, headers=None):
    try:
        obj = orjson.loads(data)
    except Exception:
        try:
            text = data.decode("utf-8", "replace")
        except Exception:
            text = ""
        if text.strip():
            rec, links, blocked = extract_html(text, url, headers)
            if not rec.get("error"):
                return rec, links, blocked
        rec = _base_record(url, "json")
        rec["error"] = "invalid_json"
        return rec, [], False
    record = _base_record(url, "json")
    record["json"] = obj
    text = _norm_ws(orjson.dumps(obj).decode("utf-8", "ignore"))[:CONTENT_MAX_CHARS]
    _fill_record(record, text, "", [], [], record["metadata"], {}, None, headers)
    record["links"] = []
    return record, [], False


def extract_xml(data, url, headers=None):
    root = _safe_parse_xml(data)
    items = _extract_feed(root) if root is not None else []
    text_parts = []
    if root is not None:
        try:
            text_parts = [t for t in root.itertext() if t and t.strip()]
        except Exception:
            pass
    full = _norm_ws(" ".join(text_parts))[:CONTENT_MAX_CHARS]
    record = _base_record(url, "xml")
    record["feed_items"] = items
    record["metadata"] = {
        "source_type": "xml",
        "items": len(items),
    }
    sections = [{"heading": "Feed", "text": full[:SECTION_MAX_CHARS]}] if full else []
    _fill_record(record, full, "", sections, [], record["metadata"], {},
                 None, headers)
    record["links"] = []
    return record, [], False


def extract_text_plain(text, url, headers=None):
    t = _norm_ws(text)
    if len(t) > CONTENT_MAX_CHARS:
        t = t[:CONTENT_MAX_CHARS]
    record = _base_record(url, "text")
    sections = [{"heading": "Text", "text": t[:SECTION_MAX_CHARS]}] if t else []
    _fill_record(record, t, "", sections, [], record["metadata"], {}, None, headers)
    record["links"] = []
    return record, [], False


def _extract_feed(root):
    items = []
    if root is None:
        return items
    try:
        for item in root.iter():
            tag = item.tag.lower() if isinstance(item.tag, str) else ""
            if tag.endswith("item") or tag.endswith("entry"):
                title = link = summary = ""
                for child in item:
                    ctag = child.tag.lower() if isinstance(child.tag, str) else ""
                    if ctag.endswith("title"):
                        title = _norm_ws(child.text or "")
                    elif ctag.endswith("link"):
                        link = child.attrib.get("href") or (child.text or "").strip()
                    elif ctag.endswith("description") or ctag.endswith("summary"):
                        summary = _norm_ws(child.text or "")
                if link:
                    items.append({"title": title, "url": link,
                                  "summary": summary[:2000]})
    except Exception:
        pass
    return items


def _source_signature(headers):
    if not headers:
        return ""
    try:
        sig = {
            "server": headers.get("server"),
            "via": headers.get("via"),
            "x-powered-by": headers.get("x-powered-by"),
            "content-type": headers.get("content-type"),
            "content-length": headers.get("content-length"),
        }
        return hashlib.blake2b(orjson.dumps(sig), digest_size=8).hexdigest()
    except Exception:
        return ""


# ============================================================================
#  FETCH LAYER
# ============================================================================

@dataclass
class FetchResult:
    url: str
    status: int
    content_type: str
    body: bytes
    headers: dict
    http_version: str
    elapsed: float
    blocked: bool
    error: str | None = None
    service: str = "direct"


def _is_blocked(status, body):
    if status in BLOCKED_STATUS_CODES:
        return True
    if body:
        low = body[:3000].lower()
        for marker in BLOCKED_BODY_MARKERS:
            if marker in low:
                return True
    return False


def _detect_content_kind(content_type, body, url):
    ct = (content_type or "").lower()
    if "pdf" in ct or body[:5] == b"%PDF-":
        return "pdf"
    if "json" in ct:
        return "json"
    if "xml" in ct or "rss" in ct or "atom" in ct:
        return "xml"
    if "html" in ct or "xhtml" in ct:
        return "html"
    if "text/plain" in ct:
        return "text"
    if body[:1] in (b"{", b"["):
        return "json"
    if body[:1] == b"<":
        head = body[:512].lower()
        if b"<?xml" in head or b"<rss" in head or b"<feed" in head:
            return "xml"
        return "html"
    return "unknown"


def fetch_sync(session, url, referer=None):
    t0 = time.monotonic()
    try:
        r = session.get(url, referer=referer)
    except Exception as e:
        return FetchResult(
            url=url, status=0, content_type="", body=b"", headers={},
            http_version="", elapsed=time.monotonic() - t0,
            blocked=False, error=repr(e),
        )
    body = r.content or b""
    return FetchResult(
        url=url,
        status=r.status_code,
        content_type=(r.headers.get("content-type") or "").lower(),
        body=body,
        headers=dict(r.headers) if r.headers else {},
        http_version=getattr(r, "http_version", "HTTP/1.1"),
        elapsed=time.monotonic() - t0,
        blocked=_is_blocked(r.status_code, body),
    )


async def fetch_async(session, url, headers=None):
    t0 = time.monotonic()
    try:
        r = await session.get(url, headers=headers)
    except Exception as e:
        return FetchResult(
            url=url, status=0, content_type="", body=b"", headers={},
            http_version="", elapsed=time.monotonic() - t0,
            blocked=False, error=repr(e),
        )
    body = r.content or b""
    return FetchResult(
        url=url,
        status=r.status_code,
        content_type=(r.headers.get("content-type") or "").lower(),
        body=body,
        headers=dict(r.headers) if r.headers else {},
        http_version=getattr(r, "http_version", "HTTP/1.1"),
        elapsed=time.monotonic() - t0,
        blocked=_is_blocked(r.status_code, body),
    )


# ============================================================================
#  MOS — SERVICE REGISTRY
# ============================================================================

MOS_SERVICES = {
    "direct": {"kind": "http", "cost": 0, "latency_p50": 0.4,
                "reliability": 0.85, "quota_per_day": None},
    "jina_reader": {"kind": "http",
                     "url_tpl": "https://r.jina.ai/{url}",
                     "cost": 0, "latency_p50": 1.8,
                     "reliability": 0.95, "quota_per_day": 1440},
    "firecrawl_keyless": {"kind": "http",
                            "url_tpl": "https://api.firecrawl.dev/v2/scrape",
                            "method": "POST",
                            "body_tpl": '{"url":"{url}","formats":["markdown"]}',
                            "cost": 0, "latency_p50": 2.5,
                            "reliability": 0.92, "quota_per_day": 33},
    "replyfast_md": {"kind": "http",
                      "url_tpl": "https://md.replyfast.co.uk/api/convert?url={url}",
                      "cost": 0, "latency_p50": 0.6,
                      "reliability": 0.90, "quota_per_day": 500},
    "web2md": {"kind": "http",
                "url_tpl": "https://web2md.org/api?url={url}",
                "cost": 0, "latency_p50": 0.8,
                "reliability": 0.85, "quota_per_day": None},
    "microlink": {"kind": "http",
                   "url_tpl": "https://api.microlink.io/?url={url}",
                   "cost": 0, "latency_p50": 1.2,
                   "reliability": 0.90, "quota_per_day": 25},
    "kiprio_readability": {"kind": "http",
                             "url_tpl": "https://kiprio.com/api/readability?url={url}",
                             "cost": 0, "latency_p50": 1.4,
                             "reliability": 0.88, "quota_per_day": 500},
    "wayback_available": {"kind": "http",
                            "url_tpl": "https://archive.org/wayback/available?url={url}",
                            "cost": 0, "latency_p50": 0.6,
                            "reliability": 0.80, "quota_per_day": None},
    "wayback_cdx": {"kind": "http",
                     "url_tpl": "https://web.archive.org/cdx/search/cdx?url={url}&output=json&limit=5",
                     "cost": 0, "latency_p50": 0.9,
                     "reliability": 0.75, "quota_per_day": 86400},
    "commoncrawl_cdx": {"kind": "http",
                         "url_tpl": "https://index.commoncrawl.org/CC-MAIN-2026-17-index?url={url}&output=json&limit=5",
                         "cost": 0, "latency_p50": 1.1,
                         "reliability": 0.70, "quota_per_day": None},
    "archive_today": {"kind": "http",
                       "url_tpl": "https://archive.ph/newest/{url}",
                       "cost": 0, "latency_p50": 1.3,
                       "reliability": 0.65, "quota_per_day": None},
    "urlscan_search": {"kind": "http",
                        "url_tpl": "https://urlscan.io/api/v1/search/?q=domain:{host}",
                        "cost": 0, "latency_p50": 0.8,
                        "reliability": 0.85, "quota_per_day": None},
    "corsproxy_io": {"kind": "http",
                      "url_tpl": "https://corsproxy.io/?{url}",
                      "cost": 0, "latency_p50": 0.9,
                      "reliability": 0.80, "quota_per_day": 86400},
    "allorigins": {"kind": "http",
                    "url_tpl": "https://api.allorigins.win/raw?url={url}",
                    "cost": 0, "latency_p50": 1.0,
                    "reliability": 0.75, "quota_per_day": None},
    "cors_lol": {"kind": "http",
                  "url_tpl": "https://cors.lol/?{url}",
                  "cost": 0, "latency_p50": 1.0,
                  "reliability": 0.70, "quota_per_day": None},
    "corsfix": {"kind": "http",
                 "url_tpl": "https://corsfix.com/{url}",
                 "cost": 0, "latency_p50": 0.9,
                 "reliability": 0.80, "quota_per_day": 86400},
    "killcors": {"kind": "http",
                  "url_tpl": "https://killcors.com/{url}",
                  "cost": 0, "latency_p50": 1.0,
                  "reliability": 0.70, "quota_per_day": None},
    "ddg_ia": {"kind": "http",
                "url_tpl": "https://api.duckduckgo.com/?q={query}&format=json",
                "cost": 0, "latency_p50": 0.5,
                "reliability": 0.80, "quota_per_day": None},
    "wikipedia_summary": {"kind": "http",
                            "url_tpl": "https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
                            "cost": 0, "latency_p50": 0.4,
                            "reliability": 0.95, "quota_per_day": None},
    "datamuse": {"kind": "http",
                  "url_tpl": "https://api.datamuse.com/words?ml={term}&max=20",
                  "cost": 0, "latency_p50": 0.3,
                  "reliability": 0.95, "quota_per_day": 100000},
    "rss2json": {"kind": "http",
                  "url_tpl": "https://api.rss2json.com/v1/api.json?rss_url={feed}",
                  "cost": 0, "latency_p50": 0.8,
                  "reliability": 0.90, "quota_per_day": 10000},
}


MOS_POLICIES = {
    "js_required": [("jina_reader", 1.0), ("firecrawl_keyless", 0.95),
                     ("replyfast_md", 0.85), ("web2md", 0.7)],
    "empty_ssr_body": [("firecrawl_keyless", 1.0), ("jina_reader", 0.95),
                        ("replyfast_md", 0.8), ("web2md", 0.7)],
    "401_auth": [("wayback_available", 1.0), ("commoncrawl_cdx", 0.9),
                  ("urlscan_search", 0.6), ("archive_today", 0.5)],
    "403_waf": [("jina_reader", 1.0), ("corsproxy_io", 0.9),
                 ("allorigins", 0.85), ("corsfix", 0.8),
                 ("wayback_available", 0.7), ("commoncrawl_cdx", 0.5)],
    "403_geo": [("corsproxy_io", 1.0), ("allorigins", 0.9),
                 ("corsfix", 0.8), ("jina_reader", 0.7)],
    "429_rate": [("wayback_available", 1.0), ("jina_reader", 0.85),
                  ("corsproxy_io", 0.8), ("allorigins", 0.7)],
    "500_transient": [("direct", 1.0), ("corsproxy_io", 0.9),
                       ("jina_reader", 0.85), ("wayback_available", 0.7)],
    "500_database": [("wayback_available", 1.0), ("commoncrawl_cdx", 0.9),
                      ("archive_today", 0.7), ("jina_reader", 0.5)],
    "500_resource_exhaustion": [("corsproxy_io", 1.0), ("jina_reader", 0.9),
                                 ("wayback_available", 0.7)],
    "500_routing": [("corsproxy_io", 1.0), ("allorigins", 0.9),
                     ("jina_reader", 0.7)],
    "500_tls": [("jina_reader", 1.0), ("corsproxy_io", 0.9),
                 ("wayback_available", 0.8)],
    "500_protocol": [("jina_reader", 1.0), ("firecrawl_keyless", 0.95),
                      ("replyfast_md", 0.8)],
    "500_app_bug": [("wayback_available", 1.0), ("commoncrawl_cdx", 0.9),
                     ("archive_today", 0.7), ("urlscan_search", 0.6)],
    "500_cms": [("firecrawl_keyless", 1.0), ("jina_reader", 0.95),
                 ("wayback_available", 0.8)],
    "500_cache": [("direct", 1.0), ("corsproxy_io", 0.9),
                   ("jina_reader", 0.7)],
    "500_backend_timeout": [("jina_reader", 1.0), ("corsproxy_io", 0.9),
                             ("wayback_available", 0.7)],
    "500_middleware": [("firecrawl_keyless", 1.0), ("jina_reader", 0.9),
                        ("replyfast_md", 0.8)],
    "502_bad_gateway": [("corsproxy_io", 1.0), ("jina_reader", 0.95),
                         ("wayback_available", 0.85), ("commoncrawl_cdx", 0.6)],
    "503_unavailable": [("wayback_available", 1.0), ("corsproxy_io", 0.9),
                         ("jina_reader", 0.85), ("archive_today", 0.6)],
    "504_timeout": [("jina_reader", 1.0), ("corsproxy_io", 0.9),
                     ("firecrawl_keyless", 0.8)],
    "cloudflare_turnstile": [("firecrawl_keyless", 1.0),
                              ("jina_reader", 0.85),
                              ("wayback_available", 0.5)],
    "cloudflare_interstitial": [("corsproxy_io", 1.0), ("jina_reader", 0.95),
                                 ("allorigins", 0.85), ("corsfix", 0.8)],
    "bot_wall_js": [("jina_reader", 1.0), ("firecrawl_keyless", 0.95),
                     ("replyfast_md", 0.85)],
    "bot_wall_captcha": [("firecrawl_keyless", 1.0), ("jina_reader", 0.8)],
}


# ============================================================================
#  MOS — CLASSIFIER
# ============================================================================

def _has_js_markers(body):
    if not body:
        return False
    sample = body[:32768]
    for m in JS_REQUIRED_MARKERS:
        if m.encode("utf-8", "ignore") in sample:
            return True
    return False


def _looks_empty(body):
    if not body:
        return True
    low = body[:16384].lower()
    for tag in (b"<p", b"<article", b"<h1", b"<main", b"<section"):
        if tag in low:
            return False
    return True


def _classify_500(body, headers):
    if any(m in body for m in (b"sql", b"mysql", b"postgres", b"database error",
                                b"connection refused", b"deadlock")):
        return "500_database"
    if any(m in body for m in (b"out of memory", b"memory exhausted",
                                b"too many open files", b"cpu limit",
                                b"disk full")):
        return "500_resource_exhaustion"
    if any(m in body for m in (b"bad gateway", b"upstream", b"no route",
                                b"host not found")):
        return "500_routing"
    if any(m in body for m in (b"ssl", b"tls", b"certificate")):
        return "500_tls"
    if any(m in body for m in (b"http/2", b"protocol error", b"chunked")):
        return "500_protocol"
    if any(m in body for m in (b"wordpress", b"drupal", b"joomla", b"wp-",
                                b"template")):
        return "500_cms"
    if any(m in body for m in (b"redis", b"memcached", b"cache")):
        return "500_cache"
    if any(m in body for m in (b"middleware", b"csrf", b"session")):
        return "500_middleware"
    return "500_transient"


def classify_error(result):
    err = getattr(result, "error", None)
    if err:
        low = str(err).lower()
        if "ssl" in low or "tls" in low or "certificate" in low:
            return "500_tls"
        if "timeout" in low or "timed out" in low:
            return "504_timeout"
        if "connection" in low or "reset" in low or "refused" in low:
            return "500_routing"
        if "json" in low and "decode" in low:
            return "js_required"
        return "500_transient"
    status = result.status
    body = (result.body or b"")[:4096].lower()
    headers = {k.lower(): v for k, v in (result.headers or {}).items()}
    if status == 202:
        return "bot_wall_js"
    if status == 401:
        return "401_auth"
    if status == 403:
        if b"cf-chl" in body or b"cloudflare" in body:
            return "cloudflare_interstitial"
        if b"turnstile" in body:
            return "cloudflare_turnstile"
        if b"recaptcha" in body or b"h-captcha" in body:
            return "bot_wall_captcha"
        return "403_waf"
    if status == 429:
        return "429_rate"
    if status == 502:
        return "502_bad_gateway"
    if status == 503:
        return "503_unavailable"
    if status == 504:
        return "504_timeout"
    if status >= 500:
        return _classify_500(body, headers)
    if status == 200:
        if _has_js_markers(result.body or b""):
            return "js_required"
        if _looks_empty(result.body or b""):
            return "empty_ssr_body"
    return None


# ============================================================================
#  MOS — CACHE LAYER
# ============================================================================

class BudgetTracker:
    def __init__(self, path=None):
        self.path = path or MOS_BUDGET_FILE
        self.data = {}
        self._load()

    def _load(self):
        try:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            if os.path.exists(self.path):
                with open(self.path, "rb") as f:
                    self.data = orjson.loads(f.read())
        except Exception:
            self.data = {}

    def _today(self):
        return time.strftime("%Y-%m-%d", time.gmtime())

    def used(self, service):
        d = self.data.get(service) or {}
        if d.get("day") != self._today():
            return 0
        return d.get("count", 0)

    def record(self, service):
        day = self._today()
        d = self.data.get(service) or {}
        if d.get("day") != day:
            d = {"day": day, "count": 0}
        d["count"] = d.get("count", 0) + 1
        self.data[service] = d

    def is_exhausted(self, service):
        quota = MOS_DAILY_BUDGET.get(service)
        if quota is None:
            return False
        return self.used(service) >= quota * MOS_BUDGET_STOP_RATIO

    def weight_factor(self, service):
        quota = MOS_DAILY_BUDGET.get(service)
        if quota is None:
            return 1.0
        used = self.used(service)
        ratio = used / quota if quota else 0.0
        if ratio >= MOS_BUDGET_STOP_RATIO:
            return 0.0
        if ratio >= MOS_BUDGET_WARN_RATIO:
            return 0.5
        return 1.0

    def save(self):
        try:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "wb") as f:
                f.write(orjson.dumps(self.data))
            os.replace(tmp, self.path)
        except Exception:
            pass


class HostPreferenceCache:
    def __init__(self, path=None):
        self.path = path or MOS_HOST_PREFS_FILE
        self.data = {}
        self._load()

    def _load(self):
        try:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            if os.path.exists(self.path):
                with open(self.path, "rb") as f:
                    self.data = orjson.loads(f.read())
        except Exception:
            self.data = {}

    def _key(self, host, service):
        return f"{host}::{service}"

    def record_success(self, host, service):
        k = self._key(host, service)
        entry = self.data.get(k) or {"success": 0, "fail": 0, "ts": 0}
        entry["success"] = entry.get("success", 0) + 1
        entry["fail"] = 0
        entry["ts"] = time.time()
        self.data[k] = entry

    def record_failure(self, host, service):
        k = self._key(host, service)
        entry = self.data.get(k) or {"success": 0, "fail": 0, "ts": 0}
        entry["fail"] = entry.get("fail", 0) + 1
        entry["ts"] = time.time()
        self.data[k] = entry

    def preference(self, host, service):
        k = self._key(host, service)
        entry = self.data.get(k)
        if not entry:
            return 1.0
        age = time.time() - entry.get("ts", 0)
        if age > MOS_STICKY_TTL:
            return 1.0
        if entry.get("success", 0) >= MOS_STICKY_SUCCESS_THRESHOLD:
            return 1.5
        if entry.get("fail", 0) >= MOS_STICKY_FAILURE_THRESHOLD:
            return 0.3
        return 1.0

    def save(self):
        try:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "wb") as f:
                f.write(orjson.dumps(self.data))
            os.replace(tmp, self.path)
        except Exception:
            pass


class MOSResponseCache:
    def __init__(self, path=None):
        self.path = path or MOS_CACHE_DB
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, timeout=30,
                                     check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS mos_responses ("
            "url_hash TEXT, service TEXT, status INT, content_type TEXT, "
            "body BLOB, headers TEXT, ts REAL, "
            "PRIMARY KEY (url_hash, service))"
        )
        self.conn.commit()

    def get(self, url, service):
        try:
            url_hash = hashlib.blake2b(url.encode(), digest_size=16).hexdigest()
            cur = self.conn.cursor()
            cur.execute(
                "SELECT status, content_type, body, headers, ts "
                "FROM mos_responses WHERE url_hash = ? AND service = ? LIMIT 1",
                (url_hash, service),
            )
            row = cur.fetchone()
            if not row:
                return None
            if time.time() - row[4] > CACHE_TTL_SECONDS:
                return None
            return FetchResult(
                url=url, status=row[0], content_type=row[1], body=row[2],
                headers=orjson.loads(row[3]) if row[3] else {},
                http_version="", elapsed=0.0, blocked=False, service=service,
            )
        except Exception:
            return None

    def put(self, url, service, result):
        try:
            url_hash = hashlib.blake2b(url.encode(), digest_size=16).hexdigest()
            self.conn.execute(
                "INSERT OR REPLACE INTO mos_responses "
                "(url_hash, service, status, content_type, body, headers, ts) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (url_hash, service, result.status, result.content_type,
                 result.body, orjson.dumps(result.headers), time.time()),
            )
            self.conn.commit()
        except Exception:
            pass

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass


# ============================================================================
#  MOS — DISPATCHER
# ============================================================================

class MOSState:
    def __init__(self):
        self.budget = BudgetTracker()
        self.host_prefs = HostPreferenceCache()
        self.cache = MOSResponseCache()

    def close(self):
        try:
            self.budget.save()
            self.host_prefs.save()
            self.cache.close()
        except Exception:
            pass


def _score_services(policy, url, budget, host_prefs):
    host = _host_of(url)
    scored = []
    for name, weight in policy:
        svc = MOS_SERVICES.get(name)
        if not svc:
            continue
        if budget.is_exhausted(name):
            continue
        wf = budget.weight_factor(name)
        if wf <= 0.0:
            continue
        reliability = svc["reliability"]
        latency = svc["latency_p50"]
        stickiness = host_prefs.preference(host, name)
        score = weight * reliability * wf * stickiness / (1.0 + latency)
        scored.append((score, name, svc))
    scored.sort(reverse=True)
    return [s[1] for s in scored]


async def _fetch_via_relay(session, url, relay_name, timeout=15):
    svc = MOS_SERVICES.get(relay_name)
    if not svc:
        return None
    tpl = svc.get("url_tpl")
    if not tpl:
        return None
    try:
        if "{query}" in tpl:
            target = tpl.format(query=quote(url))
        else:
            target = tpl.format(url=url, host=_host_of(url))
    except Exception:
        return None
    method = svc.get("method", "GET")
    try:
        if method == "POST":
            body_tpl = svc.get("body_tpl", "")
            body = body_tpl.format(url=url) if "{url}" in body_tpl else "{}"
            r = await session.post(
                target,
                data=body.encode("utf-8", "ignore"),
                headers={"Content-Type": "application/json"},
                timeout=timeout,
            )
        else:
            r = await session.get(target, timeout=timeout)
    except asyncio.CancelledError:
        return FetchResult(
            url=url, status=0, content_type="", body=b"", headers={},
            http_version="", elapsed=0.0, blocked=False,
            error="cancelled", service=relay_name,
        )
    except Exception as e:
        return FetchResult(
            url=url, status=0, content_type="", body=b"", headers={},
            http_version="", elapsed=0.0, blocked=False,
            error=repr(e)[:200], service=relay_name,
        )
    body = r.content or b""
    return FetchResult(
        url=url,
        status=r.status_code,
        content_type=(r.headers.get("content-type") or "").lower(),
        body=body,
        headers=dict(r.headers) if r.headers else {},
        http_version=getattr(r, "http_version", "HTTP/1.1"),
        elapsed=0.0,
        blocked=False,
        service=relay_name,
    )


def _is_valid_result(result):
    if result is None:
        return False
    if isinstance(result, BaseException):
        return False
    if result.status == 0:
        return False
    if result.status >= 400:
        return False
    if not result.body:
        return False
    return True


async def _one_service(state, url, service_name, session,
                        timeout=MOS_PER_SERVICE_TIMEOUT):
    cached = state.cache.get(url, service_name)
    if cached and _is_valid_result(cached):
        return cached
    r = await _fetch_via_relay(session, url, service_name, timeout=timeout)
    if r and _is_valid_result(r):
        state.budget.record(service_name)
        state.cache.put(url, service_name, r)
        state.host_prefs.record_success(_host_of(url), service_name)
    else:
        state.host_prefs.record_failure(_host_of(url), service_name)
    return r


async def mos_fetch(url, policy_key, state, impersonate="chrome136"):
    if not MOS_ENABLED or not policy_key:
        return None
    policy = MOS_POLICIES.get(policy_key)
    if not policy:
        return None
    candidates = _score_services(policy, url, state.budget, state.host_prefs)
    if not candidates:
        return None
    deadline = time.monotonic() + MOS_TOTAL_TIMEOUT
    try:
        async with _AsyncRequestsSession(impersonate=impersonate,
                                          max_clients=4,
                                          default_headers=False) as session:
            if (len(candidates) >= 2 and MOS_HEDGE_ENABLED
                    and policy_key in MOS_HEDGE_POLICIES):
                tasks = [
                    asyncio.create_task(
                        _one_service(state, url, name, session,
                                      timeout=MOS_PER_SERVICE_TIMEOUT)
                    )
                    for name in candidates[:2]
                ]
                hedge_delay = MOS_HEDGE_DELAY_MS / 1000.0
                done, pending = await asyncio.wait(
                    tasks, timeout=hedge_delay,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for t in done:
                    try:
                        r = t.result()
                        if _is_valid_result(r):
                            for p in pending:
                                p.cancel()
                            return r
                    except (asyncio.CancelledError, Exception):
                        pass
                if pending:
                    remaining = max(0.5, deadline - time.monotonic())
                    try:
                        done2, _ = await asyncio.wait(
                            pending, timeout=remaining,
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                        for t in done2:
                            try:
                                r = t.result()
                                if _is_valid_result(r):
                                    return r
                            except (asyncio.CancelledError, Exception):
                                continue
                    except asyncio.CancelledError:
                        pass
            for name in candidates:
                if time.monotonic() >= deadline:
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0.5:
                    break
                try:
                    r = await _one_service(
                        state, url, name, session,
                        timeout=min(MOS_PER_SERVICE_TIMEOUT, remaining),
                    )
                    if _is_valid_result(r):
                        return r
                except asyncio.CancelledError:
                    break
                except Exception:
                    continue
    except asyncio.CancelledError:
        return None
    except Exception as e:
        _log("mos_fetch failed: %r", e, level=logging.DEBUG)
        return None
    return None


# ============================================================================
#  VERIFICATION / ENRICHMENT
# ============================================================================

async def _http_get(session, url, headers=None, timeout=15):
    try:
        return await session.get(url, headers=headers, timeout=timeout)
    except Exception:
        return None


async def verify_url(state, url, impersonate="chrome136"):
    if not VERIFY_ENABLED:
        return {}
    report = {"sources": {}, "verdict": "unknown"}
    host = _host_of(url)
    try:
        async with _AsyncRequestsSession(impersonate=impersonate,
                                          max_clients=4,
                                          default_headers=False) as s:
            if VERIFY_WAYBACK:
                try:
                    r = await _http_get(
                        s,
                        f"https://archive.org/wayback/available?url={quote(url, safe='')}",
                    )
                    if r and r.content:
                        report["sources"]["wayback"] = orjson.loads(r.content)
                except Exception:
                    pass
            if VERIFY_COMMONCRAWL:
                try:
                    r = await _http_get(
                        s,
                        f"https://index.commoncrawl.org/CC-MAIN-2026-17-index"
                        f"?url={quote(url, safe='')}&output=json&limit=1",
                    )
                    if r and r.content:
                        report["sources"]["commoncrawl"] = (
                            r.content or b""
                        ).decode("utf-8", "ignore").splitlines()
                except Exception:
                    pass
            if VERIFY_URLSCAN:
                try:
                    r = await _http_get(
                        s, f"https://urlscan.io/api/v1/search/?q=domain:{host}"
                    )
                    if r and r.content:
                        report["sources"]["urlscan"] = orjson.loads(r.content)
                except Exception:
                    pass
            if VERIFY_DOH:
                for resolver in VERIFY_DOH_RESOLVERS:
                    try:
                        if "cloudflare" in resolver:
                            r = await _http_get(
                                s, f"{resolver}?name={host}&type=A",
                                headers={"accept": "application/dns-json"},
                            )
                        elif "google" in resolver:
                            r = await _http_get(s, f"{resolver}?name={host}&type=A")
                        else:
                            r = await _http_get(
                                s, f"{resolver}?name={host}&type=A",
                                headers={"accept": "application/dns-json"},
                            )
                        if r and r.content:
                            report["sources"].setdefault("doh", {})[resolver] = (
                                orjson.loads(r.content)
                            )
                    except Exception:
                        continue
    except Exception:
        pass
    if report["sources"].get("wayback") or report["sources"].get("commoncrawl"):
        report["verdict"] = "archived"
    return report


async def enrich_record(state, record, impersonate="chrome136"):
    url = record.get("url", "")
    quality = record.get("quality", {}) or {}
    wc = quality.get("word_count", 0)
    try:
        async with _AsyncRequestsSession(impersonate=impersonate,
                                          max_clients=4,
                                          default_headers=False) as s:
            if ENRICH_WIKIPEDIA and "wikipedia.org" in url:
                try:
                    title = urlparse(url).path.rsplit("/", 1)[-1]
                    r = await _http_get(
                        s,
                        f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title)}",
                    )
                    if r and r.content:
                        data = orjson.loads(r.content)
                        extract = data.get("extract") or ""
                        if extract and len(record.get("content", {}).get("article", {}).get("intro", "")) < 100:
                            record["content"]["article"]["intro"] = extract
                            record.setdefault("metadata", {})["wikipedia_summary"] = extract
                except Exception:
                    pass
            if ENRICH_DDG and wc and wc < 200:
                try:
                    q = record.get("title") or url
                    r = await _http_get(
                        s, f"https://api.duckduckgo.com/?q={quote(q)}&format=json&no_redirect=1",
                    )
                    if r and r.content:
                        data = orjson.loads(r.content)
                        abstract = data.get("AbstractText") or ""
                        if abstract:
                            record.setdefault("metadata", {})["ddg_abstract"] = abstract
                except Exception:
                    pass
            if ENRICH_DATAMUSE and wc and wc < 300:
                kws = record.get("keywords") or []
                expanded = []
                for kw in kws[:5]:
                    term = kw.get("term")
                    if not term or " " in term:
                        continue
                    try:
                        r = await _http_get(
                            s, f"https://api.datamuse.com/words?ml={quote(term)}&max=5",
                        )
                        if r and r.content:
                            items = orjson.loads(r.content)
                            expanded.extend(
                                {"term": x.get("word", ""), "score": x.get("score", 0)}
                                for x in items if isinstance(x, dict)
                            )
                    except Exception:
                        continue
                if expanded:
                    record["keywords"] = (kws + expanded)[:AGENT_KEYWORD_MAX_PER_DOC]
            if ENRICH_KIPRIO and wc and wc < 300:
                try:
                    r = await _http_get(
                        s, f"https://kiprio.com/api/readability?url={quote(url, safe='')}",
                    )
                    if r and r.content:
                        data = orjson.loads(r.content)
                        body = data.get("body") or ""
                        if body and len(body) > len(record.get("content", {}).get("article", {}).get("intro", "")):
                            record["metadata"] = {
                                **record.get("metadata", {}),
                                "kiprio_body": body[:20000],
                            }
                except Exception:
                    pass
            if ENRICH_MICROLINK and wc and wc < 300:
                try:
                    r = await _http_get(
                        s, f"https://api.microlink.io/?url={quote(url, safe='')}"
                    )
                    if r and r.content:
                        data = orjson.loads(r.content)
                        d = data.get("data") or {}
                        meta = record.setdefault("metadata", {})
                        if d.get("title") and not record.get("title"):
                            record["title"] = d["title"]
                        if d.get("publisher") and not meta.get("site_name"):
                            meta["site_name"] = d["publisher"]
                        if d.get("lang") and not record.get("language"):
                            record["language"] = d["lang"]
                except Exception:
                    pass
    except Exception:
        pass
    return record


# ============================================================================
#  PAGINATION
# ============================================================================

def _first_list(obj, keys, max_depth=6):
    if max_depth <= 0:
        return None
    if isinstance(obj, dict):
        for k in keys:
            if k in obj and isinstance(obj[k], list):
                return obj[k]
        for v in obj.values():
            r = _first_list(v, keys, max_depth - 1)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj[:5]:
            r = _first_list(v, keys, max_depth - 1)
            if r:
                return r
    return None


def _first_str(obj, keys, max_depth=6):
    if max_depth <= 0:
        return None
    if isinstance(obj, dict):
        for k in keys:
            if k in obj and isinstance(obj[k], str):
                return obj[k]
        for v in obj.values():
            r = _first_str(v, keys, max_depth - 1)
            if r:
                return r
    return None


def _parse_link_header(value):
    if not value:
        return None
    for part in value.split(","):
        if 'rel="next"' in part or "rel=next" in part:
            m = regex.search(r"<([^>]+)>", part)
            if m:
                return m.group(1)
    return None


# ============================================================================
#  ROUTER
# ============================================================================

def _extract_fetch_result(fr):
    url = fr.url
    kind = _detect_content_kind(fr.content_type, fr.body, url)
    if kind == "pdf":
        rec, links, blocked = extract_pdf(fr.body, url, fr.headers)
        return rec, links, blocked, False
    if kind == "json":
        rec, links, blocked = extract_json(fr.body, url, fr.headers)
        return rec, links, blocked, False
    if kind == "xml":
        rec, links, blocked = extract_xml(fr.body, url, fr.headers)
        return rec, links, blocked, False
    if kind == "text":
        text = _decode_body(fr.body, fr.headers)
        rec, links, blocked = extract_text_plain(text, url, fr.headers)
        return rec, links, blocked, False
    try:
        text = _decode_body(fr.body, fr.headers)
    except Exception as e:
        return {"url": url, "error": f"decode: {e!r}"}, [], False, False
    rec, links, blocked = extract_html(text, url, fr.headers)
    wc = rec.get("word_count", 0) or (rec.get("quality") or {}).get("word_count", 0)
    escalate = (wc < MOS_MIN_WORDS_ACCEPT) and not rec.get("error")
    return rec, links, blocked, escalate


def _try_api_router(url):
    if not API_ROUTER_ENABLED:
        return None
    try:
        from api_router import route_sync, has_route
    except ImportError:
        return None
    try:
        if not has_route(url):
            return None
    except Exception:
        return None
    try:
        rec = route_sync(url)
    except Exception:
        return None
    if rec is None:
        return None
    if isinstance(rec, dict) and "error" in rec and len(rec) <= 2:
        return None
    wc = rec.get("word_count", 0) or 0
    if wc < MOS_MIN_WORDS_ACCEPT and not rec.get("error"):
        return None
    return rec


def scrape_url(url, session, mos_state=None):
    api_rec = _try_api_router(url)
    if api_rec is not None:
        return api_rec, [], False

    if WAYBACK_FIRST_ENABLED and mos_state:
        host = _host_of(url)
        for h in WAYBACK_FIRST_HOSTS:
            if h in host:
                try:
                    r = safe_asyncio_run(mos_fetch(url, "403_waf", mos_state))
                    if r and _is_valid_result(r):
                        rec, links, _, _ = _extract_fetch_result(r)
                        return rec, links, False
                except Exception:
                    pass
                break

    if mos_state and MOS_ENABLED:
        host = _host_of(url)
        for h in MOS_FIRST_HOSTS:
            if h in host:
                try:
                    r = safe_asyncio_run(mos_fetch(url, "403_waf", mos_state))
                    if r and _is_valid_result(r):
                        rec, links, _, _ = _extract_fetch_result(r)
                        return rec, links, False
                except Exception:
                    pass
                break

    fr = fetch_sync(session, url)

    if fr.error:
        policy = classify_error(fr)
        if policy and mos_state and MOS_ENABLED:
            try:
                r = safe_asyncio_run(mos_fetch(url, policy, mos_state))
                if r and _is_valid_result(r):
                    rec, links, _, _ = _extract_fetch_result(r)
                    return rec, links, False
            except Exception:
                pass
        return {"url": url, "error": fr.error}, [], False

    if _is_valid_result(fr) and not fr.blocked:
        rec, links, blocked, escalate = _extract_fetch_result(fr)
        if escalate and mos_state and MOS_ENABLED:
            try:
                r = safe_asyncio_run(mos_fetch(url, "js_required", mos_state))
                if r and _is_valid_result(r):
                    rec2, links2, _, _ = _extract_fetch_result(r)
                    wc1 = rec.get("word_count", 0) or 0
                    wc2 = rec2.get("word_count", 0) or 0
                    if wc2 > wc1:
                        return rec2, links2, False
            except Exception:
                pass
        return rec, links, False

    policy = classify_error(fr)
    if policy and mos_state and MOS_ENABLED:
        try:
            r = safe_asyncio_run(mos_fetch(url, policy, mos_state))
            if r and _is_valid_result(r):
                rec, links, _, _ = _extract_fetch_result(r)
                return rec, links, False
        except Exception:
            pass

    if fr.blocked:
        return {"url": url, "error": f"blocked {fr.status}"}, [], True
    return {"url": url, "error": f"status {fr.status}"}, [], False


# ============================================================================
#  CLI + MAIN
# ============================================================================

def parse_args(argv=None):
    p = argparse.ArgumentParser(prog="scraper",
                                 description="universal fetch/extract/chunk")
    p.add_argument("--link", action="append", default=[],
                   help="seed URL (repeatable)")
    p.add_argument("--api", type=str, default=None, help="API endpoint")
    p.add_argument("--pagination",
                   choices=["auto", "cursor", "page", "next", "link", "none"],
                   default="auto")
    p.add_argument("--params", type=str, default="{}")
    p.add_argument("--max-pages", type=int, default=1000)
    p.add_argument("--sitemap", type=str, default=None)
    p.add_argument("--inf", action="store_true")
    p.add_argument("--fast", action="store_true")
    p.add_argument("--antiblock", action="store_true")
    p.add_argument("--depth", type=int, default=MAX_DEPTH)
    p.add_argument("--workers", type=int, default=MAX_WORKERS)
    p.add_argument("--queue-cap", type=int, default=MAX_QUEUE_SIZE)
    p.add_argument("--out", type=str, default=OUTPUT_PATH)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--enrich", action="store_true")
    p.add_argument("--clean",
                   choices=["all", "state", "db", "cache", "logs", "agent",
                            "output", "shards", "quarantine", "cookies",
                            "tmp", "legacy"],
                   default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--preload-only", action="store_true")
    p.add_argument("--no-preload", action="store_true")
    return p.parse_args(argv)


def _resolve_seeds(args):
    seeds = list(args.link) if args.link else list(SEEDS)
    if args.sitemap:
        from spoof import SpoofedSession
        s = SpoofedSession(_host_of(args.sitemap), fast=True)
        try:
            r = s.get(args.sitemap)
            if r.status_code == 200:
                body = r.content or b""
                if args.sitemap.endswith(".gz"):
                    try:
                        body = gzip.decompress(body)
                    except Exception:
                        pass
                root = _safe_parse_xml(body)
                if root is not None:
                    for el in root.iter():
                        tag = el.tag.lower() if isinstance(el.tag, str) else ""
                        if tag.endswith("loc"):
                            v = (el.text or "").strip()
                            if v:
                                seeds.append(v)
        finally:
            s.close()
    return seeds


def main(argv=None):
    try:
        import multiprocessing as mp
        mp.set_start_method("spawn", force=True)
    except Exception:
        pass

    args = parse_args(argv)

    if args.clean:
        from folder_manager import FolderManager as _FM
        if args.clean == "legacy":
            result = _FM.migrate_legacy(dry_run=args.dry_run)
            print(f"[scraper] migrated legacy: {result}")
        else:
            result = _FM.clear_tier(args.clean, dry_run=args.dry_run)
            print(f"[scraper] cleaned tier: {result}")
        if args.dry_run:
            return

    if not args.no_preload:
        print("[scraper] preloading...")
        results = preload()
        failed = [k for k, v in results.items() if not v.get("ok")]
        print(f"[scraper] preload done. failed={len(failed)}")
        if failed:
            for name in failed:
                print(f"  [FAIL] {name}: {results[name].get('error')}")

    if args.preload_only:
        print()
        print(_PRELOADER.report())
        print()
        print(FolderManager.summarize())
        return

    if args.api:
        try:
            params = orjson.loads(args.params) if args.params else {}
        except Exception:
            params = {}

        async def _run_api():
            async with _AsyncRequestsSession(impersonate="chrome136",
                                              max_clients=8,
                                              default_headers=False) as s:
                r = await s.get(args.api, params=params)
                return r.content if r else None

        content = safe_asyncio_run(_run_api())
        out_path = args.out
        with open(out_path, "wb") as f:
            if content:
                f.write(content)
        print(f"[scraper] api mode wrote {out_path}")
        return

    if not FolderManager.acquire_run_lock():
        print("[scraper] another crawler is running; refusing to start")
        return

    seeds = _resolve_seeds(args)
    options = {
        "inf": args.inf,
        "fast": args.fast,
        "antiblock": args.antiblock,
        "max_depth": args.depth,
        "workers": args.workers,
        "queue_cap": args.queue_cap,
        "out": args.out,
    }
    print(f"[scraper] seeds={len(seeds)} workers={options['workers']} "
          f"depth={options['max_depth']} queue_cap={options['queue_cap']} "
          f"fast={args.fast} inf={args.inf} antiblock={args.antiblock}")

    mos_state = MOSState()
    try:
        from crawler import run as _crawl_run
        _crawl_run(seeds, options)
    finally:
        try:
            mos_state.close()
        except Exception:
            pass
        try:
            FolderManager.release_run_lock()
            swept = FolderManager.sweep_tmp(max_age_hours=12.0)
            if swept:
                print(f"[scraper] swept {swept} stale tmp files")
        except Exception:
            pass
        print()
        print(FolderManager.summarize())


if __name__ == "__main__":
    main()