import os
import re
import sys
import gc
import time
import json
import html
import statistics
import tracemalloc
import threading
from pathlib import Path
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field, asdict
from typing import Callable

import psutil

from folder_manager import FolderManager

try:
    import orjson
except ImportError:
    orjson = None

try:
    from selectolax.lexbor import LexborHTMLParser
except ImportError:
    LexborHTMLParser = None

try:
    from lxml import etree
    from lxml.html import fromstring as lxml_fromstring
except ImportError:
    lxml = None
    lxml_fromstring = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    import trafilatura
    from trafilatura import bare_extraction
except ImportError:
    trafilatura = None
    bare_extraction = None

try:
    import justext
except ImportError:
    justext = None

from scraper import (
    extract_html, chunk_text, extract_keywords, extract_entities,
    summarize, _quality_metrics, _simhash_from_text,
    _clean_html, _trafilatura_extract, _justext_extract,
    _selectolax_extract, _sentence_split,
)

_PROC = psutil.Process(os.getpid())


# ============================================================================
#  OUTPUT
# ============================================================================

class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"


def _c(text, color):
    if os.name == "nt" and not os.environ.get("WT_SESSION"):
        return text
    return f"{color}{text}{C.RESET}"


def _banner(title):
    print()
    print("=" * 100)
    print(f"  {title}")
    print("=" * 100)


def _section(title):
    print()
    print("-" * 100)
    print(f"  {title}")
    print("-" * 100)


def _row(label, value, unit=""):
    label_pad = f"{label:<40s}"
    if isinstance(value, float):
        if unit == "ms":
            s = f"{value:>10.3f} ms"
        elif unit == "s":
            s = f"{value:>10.3f} s"
        elif unit == "MB":
            s = f"{value:>10.3f} MB"
        elif unit == "KB":
            s = f"{value:>10.3f} KB"
        elif unit == "/s":
            s = f"{value:>10,.0f} /s"
        else:
            s = f"{value:>10.3f}"
    else:
        s = f"{value:>10}"
        if unit:
            s += f" {unit}"
    print(f"  {label_pad} {s}")


# ============================================================================
#  RESULT MODEL
# ============================================================================

@dataclass
class BenchResult:
    name: str
    category: str
    iterations: int
    total_ms: float
    median_ms: float
    mean_ms: float
    min_ms: float
    max_ms: float
    p95_ms: float
    rss_mb_before: float
    rss_mb_after: float
    rss_mb_delta: float
    throughput_per_s: float = 0.0
    notes: str = ""
    extra: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


def _rss_mb():
    try:
        return _PROC.memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0


def bench(name, category, fn, iterations=5, warmup=2, notes="", extra=None):
    """Run fn() `warmup` times, then `iterations` times, capture timings."""
    for _ in range(warmup):
        try:
            fn()
        except Exception as e:
            return BenchResult(
                name=name, category=category, iterations=0,
                total_ms=0.0, median_ms=0.0, mean_ms=0.0,
                min_ms=0.0, max_ms=0.0, p95_ms=0.0,
                rss_mb_before=_rss_mb(), rss_mb_after=_rss_mb(),
                rss_mb_delta=0.0,
                notes=f"error: {e!r}", extra=extra or {},
            )

    gc.collect()
    rss_before = _rss_mb()
    times = []
    for _ in range(iterations):
        t0 = time.perf_counter_ns()
        try:
            fn()
        except Exception as e:
            return BenchResult(
                name=name, category=category, iterations=0,
                total_ms=0.0, median_ms=0.0, mean_ms=0.0,
                min_ms=0.0, max_ms=0.0, p95_ms=0.0,
                rss_mb_before=rss_before, rss_mb_after=_rss_mb(),
                rss_mb_delta=0.0,
                notes=f"error: {e!r}", extra=extra or {},
            )
        times.append((time.perf_counter_ns() - t0) / 1e6)
    rss_after = _rss_mb()

    total = sum(times)
    median = statistics.median(times)
    mean = statistics.mean(times)
    mn = min(times)
    mx = max(times)
    sorted_times = sorted(times)
    p95 = sorted_times[int(len(sorted_times) * 0.95)] if sorted_times else 0.0

    throughput = (1000.0 / median) if median > 0 else 0.0

    return BenchResult(
        name=name, category=category, iterations=iterations,
        total_ms=round(total, 3),
        median_ms=round(median, 3),
        mean_ms=round(mean, 3),
        min_ms=round(mn, 3),
        max_ms=round(mx, 3),
        p95_ms=round(p95, 3),
        rss_mb_before=round(rss_before, 2),
        rss_mb_after=round(rss_after, 2),
        rss_mb_delta=round(rss_after - rss_before, 2),
        throughput_per_s=round(throughput, 2),
        notes=notes,
        extra=extra or {},
    )


# ============================================================================
#  FIXTURES
# ============================================================================

def make_article_html(target_bytes):
    """Synthesize a realistic article page of approximately target_bytes."""
    paragraphs = []
    i = 0
    while sum(len(p) for p in paragraphs) < target_bytes * 0.7:
        paragraphs.append(
            f"<p>Paragraph {i} introduces a topic with enough content to be "
            f"meaningful for extraction. It contains multiple sentences. "
            f"This text exists to simulate a real article body. "
            f"Numbers like {i * 100} and {i * 7} appear for realism.</p>"
        )
        i += 1
    body = "\n".join(paragraphs)
    head = """<!DOCTYPE html>
<html lang="en"><head>
<title>Benchmark Test Article</title>
<meta name="description" content="A synthetic article for benchmarking">
<meta property="og:title" content="Benchmark Test Article">
<meta property="og:type" content="article">
<link rel="canonical" href="https://example.com/article">
</head><body>
<nav><a href="/">Home</a> <a href="/about">About</a> <a href="/contact">Contact</a></nav>
<main><article>
<h1>Benchmark Test Article</h1>
"""
    tail = """
</article></main>
<footer><a href="/privacy">Privacy</a> <a href="/terms">Terms</a></footer>
</body></html>"""
    # Pad with a script and style to make cleaning non-trivial
    pad = "<!--" + ("x" * max(0, target_bytes - len(head) - len(body) - len(tail) - 100)) + "-->"
    return head + body + pad + tail


def make_list_html(target_bytes):
    items = []
    i = 0
    while sum(len(x) for x in items) < target_bytes * 0.8:
        items.append(f'<li><a href="/item/{i}">Item {i} title here</a> - brief desc</li>')
        i += 1
    return (
        '<!DOCTYPE html><html><head><title>List Page</title></head>'
        '<body><h1>List</h1><ul>' + "".join(items) + "</ul></body></html>"
    )


FIXTURES = OrderedDict()
for size_kb, label in [(1, "1KB"), (10, "10KB"), (100, "100KB"), (1024, "1MB")]:
    FIXTURES[f"article_{label}"] = make_article_html(size_kb * 1024)
    FIXTURES[f"list_{label}"] = make_list_html(size_kb * 1024)


# ============================================================================
#  BASELINES
# ============================================================================

def baseline_regex_extract(html_text):
    """Naive regex strip — the fastest possible baseline."""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html_text,
                    flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text,
                    flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def baseline_stdlib_htmlparser(html_text):
    """stdlib html.parser — no external deps."""
    from html.parser import HTMLParser

    class Collector(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts = []
            self.skip = 0

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style"):
                self.skip += 1

        def handle_endtag(self, tag):
            if tag in ("script", "style"):
                self.skip = max(0, self.skip - 1)

        def handle_data(self, data):
            if not self.skip:
                self.parts.append(data)

    c = Collector()
    c.feed(html_text)
    return re.sub(r"\s+", " ", " ".join(c.parts)).strip()


def baseline_bs4(html_text):
    if BeautifulSoup is None:
        return None
    soup = BeautifulSoup(html_text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def baseline_lxml(html_text):
    if lxml_fromstring is None:
        return None
    tree = lxml_fromstring(html_text)
    for bad in tree.xpath("//script|//style|//nav|//footer"):
        bad.getparent().remove(bad)
    return " ".join(tree.itertext())


def baseline_selectolax(html_text):
    if LexborHTMLParser is None:
        return None
    tree = LexborHTMLParser(html_text)
    for bad in tree.css("script, style, nav, footer"):
        try:
            bad.decompose()
        except Exception:
            pass
    return tree.text(strip=True) or ""


def baseline_trafilatura(html_text, url="https://example.com/article"):
    if bare_extraction is None:
        return None
    doc = bare_extraction(html_text, url=url,
                           include_comments=False, include_tables=True,
                           favor_recall=True, with_metadata=True)
    if doc is None:
        return None
    if hasattr(doc, "text"):
        return doc.text or ""
    return (doc.get("text") if isinstance(doc, dict) else "") or ""


def baseline_justext(html_text):
    if justext is None:
        return None
    paras = justext.justext(html_text.encode("utf-8", "ignore"),
                             justext.get_stoplist("English"))
    good = [p.text for p in paras if not p.is_boilerplate]
    return "\n\n".join(good)


def our_full_pipeline(html_text, url="https://example.com/article"):
    rec, links, blocked = extract_html(html_text, url)
    return rec


# ============================================================================
#  BENCHMARK SUITES
# ============================================================================

def run_parser_baselines() -> list:
    """Compare raw parsing/extraction speed across libraries."""
    results = []
    for fixture_name, html_text in FIXTURES.items():
        size_kb = len(html_text) / 1024
        if size_kb > 200:
            # skip 1MB for the slower baselines to keep runtime sane
            continue
        rows = [
            ("regex_strip", lambda h=html_text: baseline_regex_extract(h)),
            ("stdlib_htmlparser", lambda h=html_text: baseline_stdlib_htmlparser(h)),
            ("bs4", lambda h=html_text: baseline_bs4(h)),
            ("lxml", lambda h=html_text: baseline_lxml(h)),
            ("selectolax", lambda h=html_text: baseline_selectolax(h)),
            ("trafilatura_only", lambda h=html_text: baseline_trafilatura(h)),
            ("justext_only", lambda h=html_text: baseline_justext(h)),
            ("our_pipeline", lambda h=html_text: our_full_pipeline(h)),
        ]
        for label, fn in rows:
            if fn is None:
                continue
            r = bench(label, "parser_baselines", fn, iterations=3, warmup=1,
                       extra={"fixture": fixture_name, "size_kb": round(size_kb, 1)})
            results.append(r)
    return results


def run_extraction_stages() -> list:
    """Time each stage of our extraction pipeline separately."""
    results = []
    for fixture_name, html_text in FIXTURES.items():
        size_kb = len(html_text) / 1024

        def _clean(h=html_text):
            return _clean_html(h)

        def _parse(h=html_text):
            return _selectolax_extract(_clean_html(h), "https://example.com/")

        def _traf(h=html_text):
            return _trafilatura_extract(h, "https://example.com/")

        def _je(h=html_text):
            return _justext_extract(h.encode("utf-8", "ignore"))

        def _full(h=html_text):
            return extract_html(h, "https://example.com/")

        stages = [
            ("clean_html", _clean),
            ("selectolax_parse", _parse),
            ("trafilatura_extract", _traf),
            ("justext_extract", _je),
            ("full_extract_html", _full),
        ]
        for label, fn in stages:
            r = bench(label, "extraction_stages", fn, iterations=3, warmup=1,
                       extra={"fixture": fixture_name, "size_kb": round(size_kb, 1)})
            results.append(r)
    return results


def run_nlp_stages() -> list:
    """Time chunking, keywords, entities, summary, quality."""
    results = []

    samples = {
        "short_500w": "The quick brown fox jumps over the lazy dog. " * 50,
        "medium_5k": "Artificial intelligence and machine learning are transforming industries. " * 500,
        "long_50k": "Streaming services deliver media over the internet. " * 4000,
    }

    for sample_name, text in samples.items():
        words = len(text.split())
        stages = [
            ("sentence_split", lambda t=text: _sentence_split(t)),
            ("chunk_text_512", lambda t=text: chunk_text(t)),
            ("keywords", lambda t=text: extract_keywords(t)),
            ("entities", lambda t=text: extract_entities(t)),
            ("summary", lambda t=text: summarize(t)),
            ("quality_metrics", lambda t=text: _quality_metrics(t)),
            ("simhash", lambda t=text: _simhash_from_text(t)),
        ]
        for label, fn in stages:
            r = bench(label, "nlp_stages", fn, iterations=5, warmup=1,
                       extra={"sample": sample_name, "words": words})
            results.append(r)
    return results


def run_simhash_scaling() -> list:
    """SimHash throughput at different token counts."""
    results = []
    for n in (1000, 10000, 100000):
        tokens = [f"token-{i}" for i in range(n)]

        def _run(t=tokens):
            return _simhash_from_text(" ".join(t))

        r = bench(f"simhash_{n}_tokens", "simhash_scaling", _run,
                   iterations=3, warmup=1,
                   extra={"tokens": n})
        r.throughput_per_s = round(n / (r.median_ms / 1000.0), 2) if r.median_ms else 0.0
        results.append(r)
    return results


def run_memory_stability(iterations=200) -> list:
    """Measure memory growth over N full pipeline runs."""
    results = []
    html_text = make_article_html(50 * 1024)

    gc.collect()
    tracemalloc.start()
    rss_before = _rss_mb()
    snap_before = tracemalloc.take_snapshot()

    for i in range(iterations):
        extract_html(html_text, f"https://example.com/{i}")

    snap_after = tracemalloc.take_snapshot()
    rss_after = _rss_mb()
    tracemalloc.stop()

    top_stats = snap_after.compare_to(snap_before, "lineno")
    top_3 = [str(s) for s in top_stats[:3]]

    r = BenchResult(
        name=f"full_pipeline_x{iterations}",
        category="memory_stability",
        iterations=iterations,
        total_ms=0.0, median_ms=0.0, mean_ms=0.0, min_ms=0.0, max_ms=0.0, p95_ms=0.0,
        rss_mb_before=round(rss_before, 2),
        rss_mb_after=round(rss_after, 2),
        rss_mb_delta=round(rss_after - rss_before, 2),
        notes=f"{iterations} iterations on 50KB fixture",
        extra={"top_allocations": top_3},
    )
    results.append(r)

    # Also measure peak of a single big run
    gc.collect()
    tracemalloc.start()
    big = make_article_html(1024 * 1024)
    t0 = time.perf_counter()
    extract_html(big, "https://example.com/big")
    dt = time.perf_counter() - t0
    cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    results.append(BenchResult(
        name="single_1MB_extraction",
        category="memory_stability",
        iterations=1,
        total_ms=round(dt * 1000, 3),
        median_ms=round(dt * 1000, 3),
        mean_ms=round(dt * 1000, 3),
        min_ms=round(dt * 1000, 3),
        max_ms=round(dt * 1000, 3),
        p95_ms=round(dt * 1000, 3),
        rss_mb_before=round(rss_before, 2),
        rss_mb_after=round(_rss_mb(), 2),
        rss_mb_delta=round(_rss_mb() - rss_before, 2),
        notes="peak traced = %.2f MB" % (peak / 1024 / 1024),
        extra={"peak_traced_mb": round(peak / 1024 / 1024, 3)},
    ))

    return results


def run_live_urls() -> list:
    """Live fetch + extract on a small curated set."""
    from spoof import SpoofedSession
    from scraper import MOSState, scrape_url

    urls = [
        ("static_small", "https://example.com/"),
        ("httpbin_html", "https://httpbin.org/html"),
        ("httpbin_json", "https://httpbin.org/json"),
        ("python_org", "https://www.python.org/"),
        ("wikipedia_medium", "https://en.wikipedia.org/wiki/HTTP"),
        ("rust_docs", "https://doc.rust-lang.org/book/"),
        ("se_question", "https://stackoverflow.com/questions/4260280"),
        ("hn_frontpage", "https://news.ycombinator.com/"),
        ("fowler_article", "https://martinfowler.com/articles/microservices.html"),
        ("arch_wiki", "https://wiki.archlinux.org/title/Pacman"),
    ]

    results = []
    for label, url in urls:
        session = None
        mos_state = None
        try:
            session = SpoofedSession(urlparse_host(url), fast=True)
            mos_state = MOSState()
            t0 = time.perf_counter()
            result = scrape_url(url, session, mos_state)
            dt = (time.perf_counter() - t0) * 1000
            if isinstance(result, tuple):
                if len(result) == 4:
                    rec, links, blocked, escalate = result
                else:
                    rec, links, blocked = result[:3]
                    escalate = False
            else:
                rec = result
                links = []
                blocked = False
                escalate = False

            kind = rec.get("kind", "?")
            words = rec.get("word_count", 0) or 0
            err = rec.get("error") if isinstance(rec, dict) else None

            if err:
                status = "error"
            elif blocked:
                status = "blocked"
            elif words < 30:
                status = "empty"
            else:
                status = "ok"

            results.append(BenchResult(
                name=label, category="live_urls", iterations=1,
                total_ms=round(dt, 3), median_ms=round(dt, 3),
                mean_ms=round(dt, 3), min_ms=round(dt, 3),
                max_ms=round(dt, 3), p95_ms=round(dt, 3),
                rss_mb_before=0.0, rss_mb_after=0.0, rss_mb_delta=0.0,
                notes=f"{status} kind={kind} words={words}",
                extra={"url": url, "status": status, "kind": kind,
                       "word_count": words, "links": len(links),
                       "escalate": escalate},
            ))
        except Exception as e:
            results.append(BenchResult(
                name=label, category="live_urls", iterations=1,
                total_ms=0.0, median_ms=0.0, mean_ms=0.0,
                min_ms=0.0, max_ms=0.0, p95_ms=0.0,
                rss_mb_before=0.0, rss_mb_after=0.0, rss_mb_delta=0.0,
                notes=f"exception: {type(e).__name__}: {e}",
                extra={"url": url, "status": "exception"},
            ))
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
    return results


def urlparse_host(url):
    from urllib.parse import urlparse
    return urlparse(url).netloc


# ============================================================================
#  REPORTING
# ============================================================================

def print_parser_baselines(results):
    _section("Parser baselines (lower is better)")
    by_fixture = defaultdict(list)
    for r in results:
        by_fixture[r.extra.get("fixture")].append(r)
    for fixture in sorted(by_fixture):
        size_kb = by_fixture[fixture][0].extra.get("size_kb", 0)
        print(f"\n  Fixture: {fixture} ({size_kb} KB)")
        rows = sorted(by_fixture[fixture], key=lambda x: x.median_ms)
        for r in rows:
            speed = f"{r.median_ms:>8.3f} ms"
            print(f"    {r.name:<24s} {speed}")


def print_extraction_stages(results):
    _section("Extraction stages (our pipeline)")
    by_fixture = defaultdict(list)
    for r in results:
        by_fixture[r.extra.get("fixture")].append(r)
    for fixture in sorted(by_fixture):
        size_kb = by_fixture[fixture][0].extra.get("size_kb", 0)
        print(f"\n  Fixture: {fixture} ({size_kb} KB)")
        for r in sorted(by_fixture[fixture], key=lambda x: -x.median_ms):
            print(f"    {r.name:<24s} {r.median_ms:>8.3f} ms")


def print_nlp_stages(results):
    _section("NLP stages")
    by_sample = defaultdict(list)
    for r in results:
        by_sample[r.extra.get("sample")].append(r)
    for sample in sorted(by_sample):
        words = by_sample[sample][0].extra.get("words", 0)
        print(f"\n  Sample: {sample} ({words} words)")
        for r in sorted(by_sample[sample], key=lambda x: -x.median_ms):
            print(f"    {r.name:<24s} {r.median_ms:>8.3f} ms  ({r.throughput_per_s:,.0f}/s)")


def print_simhash_scaling(results):
    _section("SimHash scaling")
    for r in results:
        n = r.extra.get("tokens", 0)
        print(f"    {n:>7d} tokens  {r.median_ms:>8.3f} ms  {r.throughput_per_s:>12,.0f} tok/s")


def print_memory_stability(results):
    _section("Memory stability")
    for r in results:
        print(f"    {r.name}")
        print(f"      RSS before: {r.rss_mb_before:>8.2f} MB")
        print(f"      RSS after:  {r.rss_mb_after:>8.2f} MB")
        print(f"      Delta:      {r.rss_mb_delta:>+8.2f} MB")
        if r.extra.get("peak_traced_mb") is not None:
            print(f"      Peak traced: {r.extra['peak_traced_mb']:>7.2f} MB")
        if r.notes:
            print(f"      Notes: {r.notes}")


def print_live_urls(results):
    _section("Live URL benchmarks")
    for r in results:
        status = r.extra.get("status", "?")
        color = {
            "ok": C.GREEN, "empty": C.YELLOW, "blocked": C.RED,
            "error": C.RED, "exception": C.RED,
        }.get(status, C.RESET)
        tag = _c(f"[{status.upper():9s}]", color)
        url = r.extra.get("url", "")
        print(f"    {tag} {r.name:<20s} {r.median_ms:>8.1f} ms  "
              f"kind={r.extra.get('kind', '?'):<12s} "
              f"words={r.extra.get('word_count', 0):>6d}  {url}")


def write_json_report(results, path):
    payload = {
        "generated_at": time.time(),
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "cpu_count": os.cpu_count(),
        "results": [r.to_dict() for r in results],
    }
    try:
        data = json.dumps(payload, indent=2, default=str).encode("utf-8")
    except Exception:
        return None
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(data)
    return path


# ============================================================================
#  MAIN
# ============================================================================

def main():
    import argparse

    p = argparse.ArgumentParser(prog="benchmark",
                                 description="NEXUS crawler benchmark suite")
    p.add_argument("--parser-baselines", action="store_true",
                    help="run parser comparison")
    p.add_argument("--extraction-stages", action="store_true",
                    help="run per-stage extraction timing")
    p.add_argument("--nlp-stages", action="store_true",
                    help="run NLP stage timings")
    p.add_argument("--simhash", action="store_true",
                    help="run SimHash scaling test")
    p.add_argument("--memory", action="store_true",
                    help="run memory stability test")
    p.add_argument("--live", action="store_true",
                    help="run live URL benchmarks")
    p.add_argument("--all", action="store_true",
                    help="run everything")
    p.add_argument("--out", type=str,
                    default=".data/output/benchmark.json",
                    help="JSON output path")
    args = p.parse_args()

    run_parser = args.parser_baselines or args.all
    run_extract = args.extraction_stages or args.all
    run_nlp = args.nlp_stages or args.all
    run_simhash = args.simhash or args.all
    run_mem = args.memory or args.all
    run_live = args.live or args.all

    if not any([run_parser, run_extract, run_nlp, run_simhash, run_mem, run_live]):
        # default: run everything except live
        run_parser = run_extract = run_nlp = run_simhash = run_mem = True

    FolderManager.bootstrap()

    _banner("NEXUS BENCHMARK SUITE")
    print(f"  python:   {sys.version.split()[0]}")
    print(f"  platform: {sys.platform}")
    print(f"  cpu:      {os.cpu_count()} cores")
    print(f"  rss:      {_rss_mb():.1f} MB")
    print()
    print(f"  warmup:   2 iterations")
    print(f"  timing:   3-5 iterations per benchmark")
    print(f"  fixtures: {len(FIXTURES)} synthetic HTML documents")

    all_results = []
    t_start = time.time()

    if run_parser:
        print()
        print(_c("  Running parser baselines...", C.DIM))
        res = run_parser_baselines()
        print_parser_baselines(res)
        all_results.extend(res)

    if run_extract:
        print()
        print(_c("  Running extraction stage timings...", C.DIM))
        res = run_extraction_stages()
        print_extraction_stages(res)
        all_results.extend(res)

    if run_nlp:
        print()
        print(_c("  Running NLP stage timings...", C.DIM))
        res = run_nlp_stages()
        print_nlp_stages(res)
        all_results.extend(res)

    if run_simhash:
        print()
        print(_c("  Running SimHash scaling...", C.DIM))
        res = run_simhash_scaling()
        print_simhash_scaling(res)
        all_results.extend(res)

    if run_mem:
        print()
        print(_c("  Running memory stability...", C.DIM))
        res = run_memory_stability(iterations=200)
        print_memory_stability(res)
        all_results.extend(res)

    if run_live:
        print()
        print(_c("  Running live URL benchmarks...", C.DIM))
        res = run_live_urls()
        print_live_urls(res)
        all_results.extend(res)

    elapsed = time.time() - t_start

    _banner("SUMMARY")
    print(f"  benchmarks: {len(all_results)}")
    print(f"  elapsed:    {elapsed:.1f}s")
    print(f"  final rss:  {_rss_mb():.1f} MB")

    by_cat = defaultdict(list)
    for r in all_results:
        by_cat[r.category].append(r)

    for cat in sorted(by_cat):
        items = by_cat[cat]
        print(f"  {cat:24s} {len(items):>4d} benchmarks")

    out = write_json_report(all_results, args.out)
    if out:
        print()
        print(f"  report: {Path(out).resolve()} ({Path(out).stat().st_size} bytes)")


if __name__ == "__main__":
    main()