import time
import random
import hashlib
import threading
from urllib.parse import urlparse

from curl_cffi import Curl, CurlOpt, CurlHttpVersion
from curl_cffi.requests import Session

from config import (
    BROWSER_PROFILES,
    HEADER_ORDER_CHROME, HEADER_ORDER_FIREFOX, HEADER_ORDER_SAFARI,
    LOCALES,
    JITTER_RANGE, FAST_JITTER_RANGE, REQUEST_TIMEOUT,
    TLS_GREASE, TLS_PERMUTE_EXTENSIONS, TLS_RECORD_SIZE_LIMIT,
    TLS_CERT_COMPRESSION, TLS_ENABLE_ALPS, TLS_ENABLE_TICKET,
    TLS_PSK_ENABLED,
    HTTP2_STREAM_WEIGHT, HTTP2_NO_PRIORITY,
    AKAMAI_SETTINGS_CHROME, AKAMAI_SETTINGS_FIREFOX, AKAMAI_SETTINGS_SAFARI,
    AKAMAI_WINDOW_CHROME, AKAMAI_WINDOW_FIREFOX, AKAMAI_WINDOW_SAFARI,
    AKAMAI_STREAMS_CHROME, AKAMAI_STREAMS_FIREFOX,
    PROXY_LIST,
    HTTP3_ENABLED,
    SOD_WORKER_POOL_SIZE, SOD_WORKER_RECYCLE_SECONDS, SOD_STICKY_DOMAIN,
)


def _profile_is_chrome(name):
    return "chrome" in name or "edge" in name


def _profile_is_firefox(name):
    return "firefox" in name or "tor" in name


def _profile_is_safari(name):
    return "safari" in name


def _family_of(impersonate):
    if _profile_is_chrome(impersonate):
        return "chrome"
    if _profile_is_firefox(impersonate):
        return "firefox"
    if _profile_is_safari(impersonate):
        return "safari"
    return "chrome"


def _header_order_for(impersonate):
    fam = _family_of(impersonate)
    if fam == "chrome":
        return HEADER_ORDER_CHROME
    if fam == "firefox":
        return HEADER_ORDER_FIREFOX
    if fam == "safari":
        return HEADER_ORDER_SAFARI
    return HEADER_ORDER_CHROME


def _pseudo_order_for(impersonate):
    fam = _family_of(impersonate)
    if fam == "chrome":
        return "m,a,s,p"
    if fam == "firefox":
        return "m,p,a,s"
    if fam == "safari":
        return "m,s,a,p"
    return "m,a,s,p"


def _sec_fetch_site(referer, host):
    if not referer:
        return "none"
    try:
        r_host = urlparse(referer).netloc
    except Exception:
        return "none"
    if r_host == host:
        return "same-origin"
    a = r_host.split(":")[0].split(".")
    b = host.split(":")[0].split(".")
    if len(a) >= 2 and len(b) >= 2 and a[-2:] == b[-2:]:
        return "same-site"
    return "cross-site"


def _build_akamai_string(impersonate):
    fam = _family_of(impersonate)
    if fam == "chrome":
        settings = AKAMAI_SETTINGS_CHROME
        window = AKAMAI_WINDOW_CHROME
        streams = AKAMAI_STREAMS_CHROME
        pseudo = "m,a,s,p"
    elif fam == "firefox":
        settings = AKAMAI_SETTINGS_FIREFOX
        window = AKAMAI_WINDOW_FIREFOX
        streams = AKAMAI_STREAMS_FIREFOX
        pseudo = "m,p,a,s"
    elif fam == "safari":
        settings = AKAMAI_SETTINGS_SAFARI
        window = AKAMAI_WINDOW_SAFARI
        streams = "0"
        pseudo = "m,s,a,p"
    else:
        settings = AKAMAI_SETTINGS_CHROME
        window = AKAMAI_WINDOW_CHROME
        streams = AKAMAI_STREAMS_CHROME
        pseudo = "m,a,s,p"
    return f"{settings}|{window}|{streams}|{pseudo}"


def _extra_fp_for(impersonate):
    """Only include keys that curl_cffi's ExtraFingerprints actually accepts.
    tls_enable_alps, tls_enable_ticket, tls_record_size_limit are NOT accepted
    here — they are set via CurlOpt in _apply_curl_options.
    """
    fp = {
        "tls_grease": TLS_GREASE,
        "tls_permute_extensions": TLS_PERMUTE_EXTENSIONS,
        "tls_cert_compression": TLS_CERT_COMPRESSION,
    }
    if _profile_is_chrome(impersonate):
        fp["http2_stream_weight"] = HTTP2_STREAM_WEIGHT
        fp["http2_no_priority"] = HTTP2_NO_PRIORITY
    return fp


def _apply_curl_options(curl, impersonate, header_order):
    fam = _family_of(impersonate)

    if fam == "chrome":
        pseudo = "m,a,s,p"
        settings = AKAMAI_SETTINGS_CHROME
        window = AKAMAI_WINDOW_CHROME
        streams = AKAMAI_STREAMS_CHROME
    elif fam == "firefox":
        pseudo = "m,p,a,s"
        settings = AKAMAI_SETTINGS_FIREFOX
        window = AKAMAI_WINDOW_FIREFOX
        streams = AKAMAI_STREAMS_FIREFOX
    elif fam == "safari":
        pseudo = "m,s,a,p"
        settings = AKAMAI_SETTINGS_SAFARI
        window = AKAMAI_WINDOW_SAFARI
        streams = ""
    else:
        pseudo = "m,a,s,p"
        settings = AKAMAI_SETTINGS_CHROME
        window = AKAMAI_WINDOW_CHROME
        streams = AKAMAI_STREAMS_CHROME

    try:
        curl.setopt(CurlOpt.HTTP2_PSEUDO_HEADERS_ORDER, pseudo)
    except Exception:
        pass

    if header_order:
        try:
            curl.setopt(CurlOpt.HTTPHEADER_ORDER, ",".join(header_order))
        except Exception:
            pass

    try:
        curl.setopt(CurlOpt.HTTP2_SETTINGS, settings)
    except Exception:
        pass

    try:
        curl.setopt(CurlOpt.HTTP2_WINDOW_UPDATE, int(window))
    except Exception:
        pass

    if streams:
        try:
            curl.setopt(CurlOpt.HTTP2_STREAMS, streams)
        except Exception:
            pass


def _enforce_consistency(profile, header_order):
    fam = profile.get("family") or _family_of(profile["impersonate"])
    if fam == "chrome":
        if profile.get("sec_ch_ua") is None:
            raise ValueError("chrome profile missing sec-ch-ua")
        if "sec-ch-ua" not in header_order:
            raise ValueError("chrome header_order missing sec-ch-ua")
    return True


class SODWorker:
    __slots__ = ("worker_id", "profile", "session", "locale", "proxy",
                 "impersonate", "header_order", "akamai", "extra_fp",
                 "created_at", "requests_served", "_nonce", "_last_url",
                 "_last_ts", "ua", "sec_ch_ua", "sec_ch_ua_mobile",
                 "sec_ch_ua_platform", "accept", "accept_encoding",
                 "priority", "_lock")

    def __init__(self, worker_id, profile_override=None, proxy=None):
        self.worker_id = worker_id
        self.profile = profile_override or random.choice(BROWSER_PROFILES)
        self.impersonate = self.profile["impersonate"]
        self.ua = self.profile["ua"]
        self.sec_ch_ua = self.profile.get("sec_ch_ua")
        self.sec_ch_ua_mobile = self.profile.get("sec_ch_ua_mobile")
        self.sec_ch_ua_platform = self.profile.get("sec_ch_ua_platform")
        self.accept = self.profile.get("accept")
        self.accept_encoding = self.profile.get("accept_encoding")
        self.priority = self.profile.get("priority")
        self.locale = random.choice(LOCALES)
        self.header_order = _header_order_for(self.impersonate)
        self.extra_fp = _extra_fp_for(self.impersonate)
        self.akamai = _build_akamai_string(self.impersonate)
        self.proxy = proxy if proxy else (random.choice(PROXY_LIST)
                                           if PROXY_LIST else None)
        self.created_at = time.monotonic()
        self.requests_served = 0
        self._nonce = hashlib.blake2b(
            f"{worker_id}{time.time()}{random.random()}".encode(),
            digest_size=8,
        ).hexdigest()
        self._last_url = None
        self._last_ts = 0.0
        self._lock = threading.Lock()
        _enforce_consistency(self.profile, self.header_order)
        self.session = self._build_session()

    def _build_session(self):
        kwargs = {
            "impersonate": self.impersonate,
            "default_headers": False,
            "extra_fp": self.extra_fp,
            "akamai": self.akamai,
        }
        if self.proxy:
            kwargs["proxies"] = {"http": self.proxy, "https": self.proxy}
        if HTTP3_ENABLED:
            kwargs["http_version"] = CurlHttpVersion.V3ONLY
        try:
            sess = Session(**kwargs)
        except TypeError:
            self.impersonate = "chrome136"
            self.header_order = _header_order_for(self.impersonate)
            self.extra_fp = _extra_fp_for(self.impersonate)
            self.akamai = _build_akamai_string(self.impersonate)
            kwargs = {
                "impersonate": self.impersonate,
                "default_headers": False,
                "extra_fp": self.extra_fp,
                "akamai": self.akamai,
            }
            if self.proxy:
                kwargs["proxies"] = {"http": self.proxy, "https": self.proxy}
            sess = Session(**kwargs)
        try:
            curl = sess.curl
            if curl is not None:
                _apply_curl_options(curl, self.impersonate, self.header_order)
        except Exception:
            pass
        return sess

    def _jitter(self, fast=False):
        if fast:
            return
        target = random.uniform(*JITTER_RANGE)
        elapsed = time.monotonic() - self._last_ts
        if elapsed < target:
            time.sleep(target - elapsed)

    def _referer(self, url, explicit):
        if explicit:
            return explicit
        if self._last_url and self._last_url != url:
            return self._last_url
        return None

    def _build_headers(self, url, referer):
        headers = {}
        headers["User-Agent"] = self.ua
        if self.sec_ch_ua:
            headers["sec-ch-ua"] = self.sec_ch_ua
        if self.sec_ch_ua_mobile:
            headers["sec-ch-ua-mobile"] = self.sec_ch_ua_mobile
        if self.sec_ch_ua_platform:
            headers["sec-ch-ua-platform"] = self.sec_ch_ua_platform
        headers["Accept"] = self.accept or (
            "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        )
        headers["Accept-Language"] = self.locale
        headers["Accept-Encoding"] = self.accept_encoding or "gzip, deflate, br"
        headers["Upgrade-Insecure-Requests"] = "1"
        headers["Sec-Fetch-Dest"] = "document"
        headers["Sec-Fetch-Mode"] = "navigate"
        headers["Sec-Fetch-Site"] = _sec_fetch_site(referer, _host_of(url))
        headers["Sec-Fetch-User"] = "?1"
        headers["Cache-Control"] = "max-age=0"
        headers["Connection"] = "keep-alive"
        headers["DNT"] = "1"
        if self.priority:
            headers["Priority"] = self.priority
        if referer:
            headers["Referer"] = referer
        headers["X-Nonce"] = self._nonce
        ordered = {}
        for key in self.header_order:
            if key in headers:
                ordered[key] = headers.pop(key)
        for key, value in headers.items():
            ordered[key] = value
        return ordered

    def get(self, url, referer=None, fast=False, **kwargs):
        with self._lock:
            self._jitter(fast=fast)
            ref = self._referer(url, referer)
            headers = self._build_headers(url, ref)
            r = self.session.get(
                url,
                headers=headers,
                timeout=kwargs.pop("timeout", REQUEST_TIMEOUT),
                allow_redirects=kwargs.pop("allow_redirects", True),
                **kwargs,
            )
            self._last_url = url
            self._last_ts = time.monotonic()
            self.requests_served += 1
            return r

    def post(self, url, referer=None, data=None, json=None, fast=False, **kwargs):
        with self._lock:
            self._jitter(fast=fast)
            ref = self._referer(url, referer)
            headers = self._build_headers(url, ref)
            r = self.session.post(
                url,
                headers=headers,
                data=data,
                json=json,
                timeout=kwargs.pop("timeout", REQUEST_TIMEOUT),
                allow_redirects=kwargs.pop("allow_redirects", True),
                **kwargs,
            )
            self._last_url = url
            self._last_ts = time.monotonic()
            self.requests_served += 1
            return r

    def should_recycle(self):
        return time.monotonic() - self.created_at > SOD_WORKER_RECYCLE_SECONDS

    def close(self):
        try:
            self.session.close()
        except Exception:
            pass


def _host_of(url):
    try:
        return urlparse(url).netloc
    except Exception:
        return ""


class SODPool:
    def __init__(self, size=None):
        size = size or SOD_WORKER_POOL_SIZE
        self.size = max(1, size)
        self.workers = [SODWorker(i) for i in range(self.size)]
        self._sticky = {}
        self._lock = threading.Lock()

    def acquire(self, domain=None):
        with self._lock:
            if SOD_STICKY_DOMAIN and domain and domain in self._sticky:
                w = self._sticky[domain]
                if not w.should_recycle():
                    return w
                try:
                    w.close()
                except Exception:
                    pass
            candidates = [w for w in self.workers if not w.should_recycle()]
            if not candidates:
                for w in self.workers:
                    try:
                        w.close()
                    except Exception:
                        pass
                self.workers = [SODWorker(i) for i in range(self.size)]
                candidates = self.workers
            w = random.choice(candidates)
            if SOD_STICKY_DOMAIN and domain:
                self._sticky[domain] = w
            return w

    def close(self):
        for w in self.workers:
            try:
                w.close()
            except Exception:
                pass
        self.workers = []


class SpoofedSession:
    def __init__(self, domain, fast=False, profile_override=None, proxy=None):
        self.domain = domain
        self.fast = fast
        self.worker = SODWorker(0, profile_override=profile_override, proxy=proxy)
        self.session = self.worker.session
        self.impersonate = self.worker.impersonate
        self.profile = self.worker.profile
        self.locale = self.worker.locale
        self.header_order = self.worker.header_order
        self.extra_fp = self.worker.extra_fp
        self.akamai = self.worker.akamai
        self.proxy = self.worker.proxy
        self.ua = self.worker.ua
        self.sec_ch_ua = self.worker.sec_ch_ua
        self.priority = self.worker.priority

    @property
    def _last_url(self):
        return self.worker._last_url

    @_last_url.setter
    def _last_url(self, value):
        self.worker._last_url = value

    @property
    def _last_ts(self):
        return self.worker._last_ts

    @_last_ts.setter
    def _last_ts(self, value):
        self.worker._last_ts = value

    def _jitter(self):
        self.worker._jitter(fast=self.fast)

    def _referer(self, url, explicit):
        return self.worker._referer(url, explicit)

    def _build_headers(self, url, referer):
        return self.worker._build_headers(url, referer)

    def get(self, url, referer=None, **kwargs):
        return self.worker.get(url, referer=referer, fast=self.fast, **kwargs)

    def post(self, url, referer=None, data=None, json=None, **kwargs):
        return self.worker.post(url, referer=referer, data=data,
                                 json=json, fast=self.fast, **kwargs)

    def rotate_fingerprint(self):
        old = self.impersonate
        try:
            self.session.close()
        except Exception:
            pass
        self.worker = SODWorker(0)
        self.session = self.worker.session
        self.impersonate = self.worker.impersonate
        self.profile = self.worker.profile
        self.locale = self.worker.locale
        self.header_order = self.worker.header_order
        self.extra_fp = self.worker.extra_fp
        self.akamai = self.worker.akamai
        self.proxy = self.worker.proxy
        self.ua = self.worker.ua
        self.sec_ch_ua = self.worker.sec_ch_ua
        self.priority = self.worker.priority
        return old, self.impersonate

    def rotate_proxy(self):
        if not PROXY_LIST:
            return None
        old = self.proxy
        self.proxy = random.choice(PROXY_LIST)
        try:
            self.session.close()
        except Exception:
            pass
        self.worker.proxy = self.proxy
        self.session = self.worker._build_session()
        self.worker.session = self.session
        return old, self.proxy

    def close(self):
        try:
            self.worker.close()
        except Exception:
            pass