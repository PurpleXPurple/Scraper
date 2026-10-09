=== BEGIN: LICENSE ===

MIT License

SPDX-License-Identifier: MIT

Copyright (c) 2026 NEXUS Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

**Notice on third-party components:** This project bundles or imports third-party libraries under their own licenses. See `NOTICE` for the full inventory. At least one dependency (`pymupdf`, AGPL-3.0) is incompatible with redistribution of this project under MIT without modification. Consumers who redistribute NEXUS as-is must satisfy AGPL-3.0 obligations or replace the offending dependency. See `COMPATIBILITY.md`.

=== END: LICENSE ===

---

=== BEGIN: NOTICE ===

NEXUS
Copyright (c) 2026 NEXUS Contributors

This product includes software developed by third parties. The following
components are imported, bundled, or required at runtime. Licenses are
reproduced or referenced per the upstream project.

================================================================================
CRITICAL — COPYLEFT DEPENDENCIES (READ BEFORE REDISTRIBUTING)
================================================================================

pymupdf — AGPL-3.0-or-later
  Upstream: https://github.com/pymupdf/PyMuPDF
  Used in: scraper.py (PDF extraction, OCR fallback)
  Impact: AGPL-3.0 §13 requires that users interacting with the software
  over a network be offered the Corresponding Source. If NEXUS is
  redistributed under MIT, this obligation is not satisfied. Remedy:
  replace pymupdf with a permissive PDF extractor, or relicense NEXUS to
  AGPL-3.0.

pyphen — GPL-2.0-or-later OR LGPL-2.1-or-later OR MPL-1.1
  Upstream: https://github.com/Kozea/Pyphen
  Used in: scraper.py (hyphenation)
  Impact: Safe if LGPL or MPL option is elected. Unsafe if GPL option is
  elected, because GPL-2.0 is incompatible with MIT for combined work.
  Downstream consumers must elect LGPL-2.1-or-later or MPL-1.1.

================================================================================
PERMISSIVE DEPENDENCIES
================================================================================

Apache-2.0:
  trafilatura, courlan, htmldate, nltk, regex

BSD-2-Clause or BSD-3-Clause:
  lxml, lxml-html-clean, justext, dateparser, babel, psutil, python-dateutil,
  pytz, six

MIT:
  curl-cffi, selectolax, orjson, textstat, tld, tzlocal, pyphen (LGPL/MPL
  option), cloudpickle, click, colorama, tqdm

ISC:
  certifi

PSF-2.0:
  defusedxml

Python Software Foundation License:
  Python standard library components

================================================================================
EXTERNAL SERVICES CONTACTED AT RUNTIME (NOT BUNDLED)
================================================================================

The following services are contacted over the network when NEXUS runs. No
source code from these services is bundled. Contact is governed by each
service's own terms of service and privacy policy.

  Stack Exchange API (api.stackexchange.com) — CC BY-SA 4.0 content
  Wayback Machine (archive.org) — Wayback ToS
  Common Crawl (index.commoncrawl.org) — Common Crawl ToS
  APIs.guru (api.apis.guru) — CC0-1.0 data
  Certificate Transparency (crt.sh) — public data
  Google Public DNS (dns.google) — Google ToS
  Cloudflare DNS (cloudflare-dns.com) — Cloudflare ToS
  Quad9 DNS (dns.quad9.net) — Quad9 ToS
  hstspreload.org — public data
  ip-api.com — free tier ToS
  urlscan.io — urlscan ToS
  DuckDuckGo Instant Answer (api.duckduckgo.com) — DDG ToS
  Datamuse (api.datamuse.com) — Datamuse ToS
  Wikipedia REST API — CC BY-SA 4.0
  r.jina.ai — Jina Reader ToS
  api.firecrawl.dev — Firecrawl ToS
  md.replyfast.co.uk — ReplyFast ToS
  web2md.org — Web2MD ToS
  api.microlink.io — Microlink ToS
  kiprio.com — Kiprio ToS
  corsproxy.io, api.allorigins.win, cors.lol, corsfix.com, killcors.com —
    per-service ToS
  RapidAPI (api.rapidapi.com) — RapidAPI ToS
  archive.ph — archive.today ToS
  dns.google / RDAP (rdap.org) — public registry data

The operator is solely responsible for compliance with each service's terms.

================================================================================
CONTENT LICENSE NOTES
================================================================================

Content extracted by NEXUS from third-party websites is not licensed by
this project. Extracted content carries the license of its source. Wikipedia
content is CC BY-SA 4.0. Stack Exchange content is CC BY-SA 4.0 (or 3.0 for
older posts). Other sources carry their own licenses. The operator is
responsible for compliance with each source's license before using
extracted content in training corpora or redistribution.

=== END: NOTICE ===

---

=== BEGIN: TERMS_OF_USE.md ===

# Terms of Use — NEXUS

**Version 1.0.0** · Effective 2026-01-01 · SPDX: MIT

> **Plain-language summary (non-binding):** NEXUS is a free, open-source
> crawler. You may use it, modify it, and share it. You are responsible for
> how you use it. Do not use it to break the law, harm people, or violate
> other sites' rules. The authors are not liable for anything you do with it.
> The summary is not the legal terms; the sections below are.

## 1. Acceptance

By downloading, installing, or using NEXUS (the "Software"), you accept
these Terms of Use. If you do not accept them, do not use the Software.

## 2. Eligibility

You must be at least 16 years of age, or the age of digital consent in your
jurisdiction, whichever is higher, to use the Software. If you use the
Software on behalf of an organization, you represent that you have authority
to bind that organization to these Terms.

## 3. License Grant

The Software is licensed under the MIT License. Subject to your compliance
with these Terms, you are granted a worldwide, non-exclusive, royalty-free
license to use, copy, modify, merge, publish, distribute, sublicense, and
sell copies of the Software, subject to the conditions of the MIT License.

## 4. Permitted Use

You may use NEXUS to:

- Crawl websites you own or have authorization to crawl.
- Crawl publicly accessible content in compliance with applicable law and
  the target site's terms of service, robots.txt, and rate limits.
- Generate datasets for personal, academic, or commercial use, provided you
  comply with the source content's license terms.
- Modify, extend, and redistribute the Software under the MIT License.

## 5. Prohibited Conduct

You must not use NEXUS to:

- Violate any applicable law, including the Computer Fraud and Abuse Act
  (18 U.S.C. § 1030), the Digital Millennium Copyright Act, the EU Digital
  Services Act, or any analogous law in your jurisdiction.
- Crawl content behind authentication walls you are not authorized to access.
- Bypass paywalls, CAPTCHAs, or access controls you are not authorized to
  bypass.
- Collect, process, or distribute personal data in violation of GDPR, UK
  GDPR, CCPA/CPRA, or any other applicable privacy law.
- Collect, generate, or distribute child sexual abuse material (CSAM). This
  prohibition is absolute and non-negotiable.
- Harass, stalk, dox, or harm any individual.
- Generate content intended to defraud, impersonate, or deceive.
- Distribute malware, conduct unauthorized penetration testing, or engage in
  denial-of-service attacks.
- Violate the terms of service of any site you crawl.

## 6. Intellectual Property

The Software is owned by NEXUS Contributors and licensed under MIT. The
"NEXUS" name and logo are unregistered trademarks of NEXUS Contributors. You
may not use the name "NEXUS" to endorse or promote products derived from
the Software without prior written permission. See `TRADEMARK.md`.

Content extracted by the Software from third-party sites is owned by its
respective rights holders and is not licensed by this project.

## 7. User Content

NEXUS does not host user content. It runs locally on your machine and writes
output to your local filesystem. You are solely responsible for the content
you crawl and the datasets you generate.

## 8. Feedback

If you submit feedback, bug reports, or feature requests, you grant NEXUS
Contributors a non-exclusive, royalty-free, perpetual license to use that
feedback without restriction.

## 9. Disclaimers

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT. THE AUTHORS MAKE NO
WARRANTY THAT THE SOFTWARE WILL NOT VIOLATE ANY THIRD-PARTY TERMS OF SERVICE,
THAT CRAWLED CONTENT WILL BE LAWFUL TO USE, OR THAT THE SOFTWARE WILL BE
ERROR-FREE.

## 10. Limitation of Liability

IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES, OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR
OTHERWISE, ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE
USE OR OTHER DEALINGS IN THE SOFTWARE.

## 11. Indemnification

You agree to indemnify and hold harmless NEXUS Contributors from any claim
arising out of your use of the Software, including claims by third parties
whose sites you crawl, claims by data subjects whose personal data you
process, and claims by rights holders whose content you extract.

## 12. Termination

These Terms terminate automatically if you breach them. The MIT License
grant survives termination for copies you have already distributed in
compliance with the License.

## 13. Governing Law

These Terms are governed by the laws of the State of Delaware, USA, without
regard to its conflict-of-laws principles. For EU users, mandatory consumer
protection rights of your country of residence apply.

## 14. Dispute Resolution

Disputes arising under these Terms shall be resolved by binding arbitration
in Wilmington, Delaware, under the rules of the American Arbitration
Association. EU users retain the right to bring claims before their local
courts. Nothing in this section waives any non-waivable statutory right.

## 15. Changes

NEXUS Contributors may update these Terms. Material changes will be
announced in the repository's `CHANGELOG.md` and will take effect 30 days
after publication. Continued use after the effective date constitutes
acceptance.

## 16. Contact

Issues: https://github.com/<your-org>/nexus-crawler/issues
Security: see `SECURITY.md`

=== END: TERMS_OF_USE.md ===

---

=== BEGIN: TERMS_OF_SERVICE.md ===

# Terms of Service — NEXUS

**Status: NOT APPLICABLE to the distributed software.**

NEXUS is distributed as a local, self-hosted software package. It is not
offered as a hosted service by the maintainers. There is no account system,
no subscription, no service level, and no data stored on maintainer servers.

If you (or a third party) host NEXUS as a service — for example, as a managed
crawling API — the template below applies to that hosted instance. Maintainers
of the distributed software are not responsible for third-party hosted
instances.

---

## Template for hosted NEXUS instances (applies only if you offer NEXUS-as-a-Service)

**Version 1.0.0** · Effective 2026-01-01

### 1. Account Terms

You must provide accurate registration information. You are responsible for
the security of your credentials. You must be 16+ or have guardian consent.

### 2. Subscription and Billing

Fees, billing cycle, and payment terms are stated at the point of sale.
Subscriptions auto-renew unless cancelled. Cancellation is effective at the
end of the current billing period. Refunds are governed by the applicable
consumer protection law of your jurisdiction.

### 3. Service Description

The hosted service provides managed access to the NEXUS crawler. Crawl
targets, rate limits, and output formats are described in the service plan.

### 4. Acceptable Use

The Acceptable Use terms in `TERMS_OF_USE.md` §5 apply to the hosted service.
Additional restrictions may apply based on the hosting provider's acceptable
use policy.

### 5. Data Handling

Data submitted to the hosted service is processed per `PRIVACY_POLICY.md`.
Extracted content is stored per your account's retention settings. You may
export or delete your data at any time via the account dashboard.

### 6. Suspension and Termination

We may suspend or terminate accounts that violate these Terms, that present
a security risk, or that generate excessive resource consumption. Notice
will be provided where practicable.

### 7. Service Levels

Uptime targets, if any, are stated in the plan. Scheduled maintenance will
be announced in advance. No SLA is implied unless explicitly agreed in
writing.

### 8. Refunds

Refunds are provided for prepaid periods not consumed due to service failure
attributable to the operator. Statutory refund rights are not waived.

### 9. API Terms

API keys are personal. Rate limits apply per key. Reverse-engineering the
API surface is permitted for interoperability but not for abuse.

### 10. Third-Party Services

The hosted service contacts third-party services (see `NOTICE`). The
operator is not responsible for those services' availability or terms.

### 11. Export Compliance

You may not use the hosted service in violation of OFAC sanctions or EAR
export controls. See `EXPORT.md`.

### 12. Governing Law and Arbitration

Delaware, USA. Arbitration in Wilmington, Delaware. EU consumers retain
rights before local courts. Class action waiver applies to the extent
permitted by law.

### 13. Entire Agreement

These Terms, together with `TERMS_OF_USE.md`, `PRIVACY_POLICY.md`, and the
MIT License, constitute the entire agreement.

=== END: TERMS_OF_SERVICE.md ===

---

=== BEGIN: PRIVACY_POLICY.md ===

# Privacy Policy — NEXUS

**Version 1.0.0** · Effective 2026-01-01

> **Plain-language summary (non-binding):** NEXUS runs on your machine. It
> does not send your data to the maintainers. It does send requests to
> third-party services to do its job. If you crawl sites with personal data,
> you are the data controller and you must comply with privacy law.

## 1. Data Controller

For personal data processed during your use of NEXUS, **you are the data
controller**. NEXUS Contributors do not receive, store, or process any data
generated by your use of the Software.

## 2. Data Categories Processed Locally

When you run NEXUS, it processes:

- **URLs** you provide as seeds or discover during crawling.
- **HTTP response bodies** returned by sites you crawl.
- **HTTP headers** including cookies, ETags, and Last-Modified values.
- **Extracted text, metadata, entities, keywords, and chunks** derived from
  crawled content.
- **PII** present in crawled content (emails, phone numbers, SSNs, credit
  cards, IP addresses) — optionally redacted if `AGENT_PII_REDACT_ENABLED`
  is set to True.
- **Operational data** — logs, rate-limit state, dedup hashes, and cache
  entries.

All of the above are stored on **your local filesystem** under `.data/`. None
of it is transmitted to NEXUS Contributors.

## 3. Third-Party Services Contacted

NEXUS contacts the following external services at runtime. Each service
receives at minimum the request URL and your IP address. See `NOTICE` for the
full list and each service's privacy policy.

- Stack Exchange API — receives the question ID and your IP.
- Wayback Machine, Common Crawl, archive.today — receive the target URL.
- crt.sh, DNS resolvers (Google, Cloudflare, Quad9), RDAP, hstspreload.org —
  receive the target domain.
- urlscan.io, RapidAPI — receive the target domain or URL.
- Jina Reader, Firecrawl, ReplyFast, Web2MD, Microlink, kiprio, CORS relays
  — receive the target URL as a proxy fetch.
- DuckDuckGo IA, Datamuse, Wikipedia REST — receive query terms.

**You** are responsible for determining whether contacting these services
from your jurisdiction is lawful, and for disclosing this in your own privacy
notice if you operate NEXUS on behalf of an organization.

## 4. Legal Basis (GDPR / UK GDPR)

If you process personal data using NEXUS, you must establish a legal basis
under GDPR Article 6. For crawling publicly available content, the most
common bases are:

- **Legitimate interests** (Art. 6(1)(f)) — for research, journalism, or
  security purposes, subject to a balancing test.
- **Consent** (Art. 6(1)(a)) — where the data subject has consented.
- **Legal obligation** (Art. 6(1)(c)) — where processing is required by law.

Special category data (Art. 9) — health, biometric, political, religious,
sexual orientation — requires an Art. 9 condition. NEXUS does not provide
one. Do not crawl such data unless you have a lawful basis.

## 5. Data Subject Rights

If you crawl content containing personal data, data subjects may contact
**you** (not NEXUS Contributors) to exercise rights of access, rectification,
erasure, restriction, portability, and objection. You must respond within
the statutory period (30 days under GDPR; 45 days under CCPA/CPRA). You
should maintain a documented process for handling such requests.

## 6. Retention

NEXUS retains crawled data on your local filesystem until you delete it.
Default retention is indefinite. To comply with GDPR Art. 5(1)(e), configure
retention limits and periodically purge. Use `FolderManager.rotate_shards()`
and `FolderManager.rotate_logs()`.

## 7. International Transfers

If you transfer personal data extracted by NEXUS outside the EEA/UK, you
must ensure a valid transfer mechanism (Standard Contractual Clauses,
Adequacy Decision, or Art. 49 derogation). NEXUS itself does not transfer
data — you do.

## 8. Security

NEXUS implements reasonable technical measures: atomic file writes,
cross-process locking, optional PII redaction, and no remote telemetry. See
`SECURITY.md` for disclosure of vulnerabilities. You are responsible for
securing the machine on which NEXUS runs and any datasets you extract.

## 9. Cookies and Tracking

NEXUS does not set cookies on user devices. When crawling, NEXUS may receive
cookies from target sites and stores them under `.data/cookies/` for session
continuity. See `COOKIES.md`.

## 10. Children's Privacy

NEXUS is not directed at children under 16. Do not use NEXUS to crawl content
directed at children without complying with COPPA (US), GDPR Art. 8 (EU), or
equivalent. Do not crawl sites that primarily host children's data.

## 11. AI Training Data

If you use NEXUS output to train machine learning models, you are a provider
of an AI system under the EU AI Act (Regulation (EU) 2024/1689). You must
comply with transparency, data governance, and (where applicable) conformity
assessment obligations. See `AI_DISCLOSURE.md`.

## 12. Changes

Material changes will be announced in `CHANGELOG.md` and take effect 30 days
after publication.

## 13. Contact

Data protection inquiries: https://github.com/<your-org>/nexus-crawler/issues
For EU users, a Data Protection Officer is not currently appointed because
NEXUS Contributors do not process personal data. If you deploy NEXUS in a
manner requiring a DPO under GDPR Art. 37, you must appoint one.

=== END: PRIVACY_POLICY.md ===

---

=== BEGIN: TERMS_OF_NEXUS.md ===

# Terms of NEXUS

**Version 1.0.0** · Effective 2026-01-01 · SPDX: MIT

## 1. Project Identity

NEXUS (also referred to as "the Scraper," "the Crawler") is a universal
cross-domain web crawler designed for AI dataset generation. Its source is
maintained at https://github.com/<your-org>/nexus-crawler. It is distributed
free of charge under the MIT License.

## 2. Ownership and Attribution

Copyright (c) 2026 NEXUS Contributors, including work by AboSmrh and
PurpleXPurple as recorded in `CHANGELOG.md`. Contributions are governed by
`CONTRIBUTING.md`. Attribution of upstream dependencies is in `NOTICE`.

## 3. License Summary

You may use, modify, distribute, and sublicense NEXUS under MIT terms,
subject to the third-party license obligations documented in `NOTICE` and
`COMPATIBILITY.md`. The `pymupdf` AGPL-3.0 dependency is a material
compatibility issue; see `COMPATIBILITY.md`.

## 4. User Obligations

By using NEXUS you agree to:

- Comply with all applicable laws, including CFAA, DMCA, GDPR, CCPA, DSA,
  and equivalents.
- Respect robots.txt and published crawl-delay directives where present.
- Respect target site rate limits. NEXUS's token bucket enforces a per-domain
  floor, but you must not raise it to abusive levels.
- Not use NEXUS to bypass authentication, paywalls, or access controls.
- Not use NEXUS to process special-category personal data without a lawful
  basis.
- Not use NEXUS to generate CSAM, to stalk, or to harass.
- Comply with the terms of service of every site you crawl.
- Comply with the terms of service of every third-party service NEXUS
  contacts (see `NOTICE`).

## 5. Project-Specific Restrictions

In addition to §5 of `TERMS_OF_USE.md`:

- Do not remove, obscure, or alter the attribution notices in `NOTICE` or
  in source headers.
- Do not redistribute NEXUS under a different license unless you replace
  every copyleft dependency (see `COMPATIBILITY.md`).
- Do not claim endorsement by the NEXUS project for derivative works.
- Do not use the NEXUS name or logo in a way that suggests official status
  without written permission (see `TRADEMARK.md`).

## 6. Contribution Terms

Contributions are accepted under the Developer Certificate of Origin (DCO).
By submitting a pull request, you certify that you have the right to submit
the contribution and that it is licensed under MIT. See `CLA.md`.

## 7. Trademark and Branding

"NEXUS" is an unregistered trademark. Usage guidelines are in `TRADEMARK.md`.

## 8. Warranty and Support

No warranty. No support obligation. Community support is provided on a
best-effort basis via GitHub Issues. Commercial support is not offered.

## 9. Project-Specific Disclaimers

- **Legal risk of crawling.** Crawling may expose you to claims of breach of
  contract (target site ToS), trespass to chattels, CFAA violations, or
  copyright infringement. NEXUS Contributors are not liable for these.
- **Content risk.** Crawled content may contain material you do not wish to
  process. NEXUS does not filter content categories.
- **AI training risk.** Training a model on crawled data may expose you to
  copyright, privacy, and AI Act compliance obligations. NEXUS Contributors
  are not liable for these.
- **Dependency risk.** Third-party services may change, block, throttle, or
  shut down at any time. NEXUS Contributors make no uptime promise.
- **License contamination risk.** If you redistribute NEXUS, you must address
  the `pymupdf` AGPL-3.0 issue yourself.

## 10. Versioning and Amendment

Semantic versioning applies. Breaking changes to the software are announced
in `CHANGELOG.md`. Legal documents are versioned per `VERSIONS.md`.

## 11. Contact

Issues: https://github.com/<your-org>/nexus-crawler/issues
Security: security@<your-domain> (replace before publishing)

=== END: TERMS_OF_NEXUS.md ===

---

=== BEGIN: CLA.md ===

# Contributor Agreement — NEXUS

NEXUS uses the **Developer Certificate of Origin (DCO)**, not a CLA. This is
the lighter-weight option, appropriate for a permissively-licensed project.
A CLA would only be warranted if NEXUS Contributors intended to relicense
the project in the future (for example, to a source-available license after
a `pymupdf`-driven relicense). If that possibility matters, switch to a
CLA — the Apache Individual CLA template is the standard choice.

## Developer Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I have the
    right to submit it under the open source license indicated in the file;
    or

(b) The contribution is based upon previous work that, to the best of my
    knowledge, is covered under an appropriate open source license and I
    have the right under that license to submit that work with
    modifications, whether created in whole or in part by me, under the same
    open source license (unless I am permitted to submit under a different
    license), as indicated in the file; or

(c) The contribution was provided directly to me by some other person who
    certified (a), (b) or (c) and I have not modified it.

(d) I understand and agree that this project and the contribution are public
    and that a record of the contribution (including all personal
    information I submit with it, including my sign-off) is maintained
    indefinitely and may be redistributed consistent with this project or
    the open source license(s) involved.

## How to sign off

Add a `Signed-off-by:` line to every commit message:

```
Signed-off-by: Your Name <your.email@example.com>
```

Use `git commit -s` to add this automatically.

=== END: CLA.md ===

---

=== BEGIN: DPA.md ===

# Data Processing Agreement — Template

This DPA applies when a **controller** (the NEXUS operator's customer, or
the operator itself when processing on behalf of a customer) engages a
**processor** to run NEXUS on its behalf. If you run NEXUS for yourself on
your own machine, this DPA does not apply — you are the sole controller and
processor.

**Where NEXUS is used as a managed service, the following terms apply.**

## 1. Definitions

Terms used in this DPA have the meanings given in Article 4 of the GDPR.

## 2. Scope and Purpose

The processor processes personal data only on documented instructions from
the controller, only for the purposes of operating NEXUS to crawl sites
specified by the controller, and only for the duration of the service.

## 3. Categories of Data Subjects and Personal Data

- **Data subjects:** individuals whose personal data appears on crawled pages.
- **Categories of personal data:** names, emails, phone numbers, addresses,
  IP addresses, and any other personal data present in crawled content.
- **Special categories:** the controller must not instruct the processor to
  crawl special-category data unless the controller has established an
  Article 9 condition.

## 4. Processor Obligations

The processor shall:

- Process personal data only on documented instructions.
- Ensure that persons authorized to process data are bound by
  confidentiality.
- Implement appropriate technical and organizational measures (Art. 32).
- Not engage sub-processors without prior written authorization. Current
  sub-processors are listed in `SUB_PROCESSORS.md`.
- Assist the controller in responding to data subject requests.
- Assist the controller with DPIAs and prior consultations.
- Delete or return personal data at the end of the provision of services.
- Make available all information necessary to demonstrate compliance.
- Not transfer personal data outside the EEA/UK without a valid transfer
  mechanism.

## 5. Sub-processors

See `SUB_PROCESSORS.md`. The controller authorizes the listed sub-processors.
The processor will give 30 days' notice before adding or replacing a
sub-processor.

## 6. Security

The processor shall implement: encryption at rest and in transit, access
control, audit logging, and (where applicable) pseudonymization. NEXUS's
built-in PII redaction may be enabled as an additional safeguard but does
not replace technical and organizational measures.

## 7. Breach Notification

The processor shall notify the controller without undue delay (and no later
than 48 hours) after becoming aware of a personal data breach.

## 8. International Transfers

Transfers outside the EEA/UK rely on Standard Contractual Clauses
(Commission Implementing Decision (EU) 2021/914). The controller and
processor agree to the SCCs by reference, with the optional clauses
appropriate to the relationship.

## 9. Term and Termination

This DPA is coterminous with the main service agreement. On termination the
processor shall delete or return all personal data, at the controller's
choice, unless EU or Member State law requires storage.

## 10. Liability

Each party's liability under this DPA is subject to the limitations in the
main service agreement, except where prohibited by law.

## 11. Governing Law

The law of the controller's establishment, or as specified in the main
agreement.

=== END: DPA.md ===

---

=== BEGIN: SUB_PROCESSORS.md ===

# Sub-processors — NEXUS

When NEXUS is operated as a managed service, the following third parties
process personal data as sub-processors. Each is contacted at runtime per
`PRIVACY_POLICY.md` §3.

| Sub-processor | Purpose | Location | Safeguard |
|---|---|---|---|
| Stack Exchange Inc. | Stack Exchange API | USA | SCCs |
| Internet Archive | Wayback Machine | USA | SCCs |
| Common Crawl Foundation | CDX index | USA | SCCs |
| APIs.guru | OpenAPI directory | USA | SCCs |
| crt.sh (Sectigo) | Certificate Transparency | USA | SCCs |
| Google LLC | Public DNS, search enrichment | USA | SCCs |
| Cloudflare Inc. | DNS, CORS relay | USA | SCCs |
| Quad9 Foundation | DNS | Switzerland | Adequacy |
| hstspreload.org | HSTS preload | Global | Public data |
| ip-api.com | IP geolocation | Hungary | Adequacy |
| urlscan.io | Domain search | Germany | Adequacy |
| DuckDuckGo Inc. | Instant Answer API | USA | SCCs |
| Datamuse | Semantic word API | USA | SCCs |
| Wikimedia Foundation | Wikipedia REST API | USA | SCCs |
| Jina AI | Jina Reader relay | Germany | Adequacy |
| Firecrawl | Firecrawl relay | USA | SCCs |
| ReplyFast | Markdown relay | UK | Adequacy |
| Web2MD | Markdown relay | Unknown | Contract required |
| Microlink | Metadata relay | Netherlands | Adequacy |
| Kiprio | Readability relay | Unknown | Contract required |
| Corsproxy.io, AllOrigins, cors.lol, Corsfix, KillCors | CORS relays | Various | Contract required per relay |
| RapidAPI | Marketplace search | USA | SCCs |
| archive.today | Archive relay | Unknown | Contract required |

**Operators of hosted NEXUS instances must verify each sub-processor's
current location, privacy policy, and transfer mechanism before publishing
this list. The list above is a starting point, not a legal artifact.**

=== END: SUB_PROCESSORS.md ===

---

=== BEGIN: COOKIES.md ===

# Cookie Policy — NEXUS

## 1. Cookies NEXUS Sets

NEXUS does **not** set cookies on user devices. It is not a web application
and does not run a browser interface.

## 2. Cookies NEXUS Receives and Stores

When crawling target sites, NEXUS receives `Set-Cookie` headers from those
sites. NEXUS stores them under `.data/cookies/<domain>/` for session
continuity, per `COOKIE_PERSISTENCE = True` in `config.py`. These cookies
are not transmitted to any third party by NEXUS. They are used only to
maintain session state with the origin site.

## 3. Cookie Retention

Stored cookies persist until removed by the operator or until the cookie's
own expiry. Use `FolderManager.clear_tier("cookies")` to purge.

## 4. Cookies NEXUS Sends

NEXUS may send received cookies back to the origin site on subsequent
requests to that domain. This is standard session behavior.

## 5. Third-Party Cookies

NEXUS does not embed third-party tracking cookies in any interface. Third-
party services contacted by NEXUS (see `NOTICE`) may set cookies on their
own servers; those are governed by each service's cookie policy.

## 6. Browser Interface

NEXUS has no browser interface and therefore no cookie banner.

## 7. User Responsibility

If you operate NEXUS as a service with a web interface, you must implement a
GDPR/ePrivacy-compliant cookie banner and consent mechanism. The NEXUS
software provides none.

=== END: COOKIES.md ===

---

=== BEGIN: SECURITY.md ===

# Security Policy — NEXUS

## Supported Versions

| Version | Supported |
|---|---|
| 4.x | ✅ |
| 3.x | ⚠️ Critical fixes only |
| 2.x | ❌ |
| 1.x | ❌ |

## Reporting a Vulnerability

Email: security@<your-domain> (replace before publishing)
Or open a private security advisory on GitHub.

Do **not** open public issues for security vulnerabilities.

## What to Include

- Description of the vulnerability.
- Steps to reproduce.
- Affected version(s).
- Impact assessment.
- Suggested fix (if you have one).
- Whether you intend to publish a write-up and on what timeline.

## Response Timeline

- Acknowledgement: within 3 business days.
- Initial assessment: within 7 business days.
- Fix or mitigation: within 30 days for high-severity, best effort for
  lower-severity.
- Public disclosure: coordinated with the reporter, typically 90 days after
  the fix ships.

## Scope

In scope:
- Remote code execution via crafted crawled content.
- Authentication bypass (not applicable — NEXUS has no auth).
- SQL injection in cache or dedup stores.
- Path traversal in file writes.
- Dependency vulnerabilities in pinned versions.

Out of scope:
- The fact that NEXUS crawls sites (that's the point).
- Rate limiting on target sites (operator's responsibility).
- Detection by anti-bot systems (expected behavior).
- Vulnerabilities in third-party services NEXUS contacts.

## Safe Harbor

Good-faith security research on NEXUS is authorized. Do not test against
third-party sites using NEXUS without authorization. Do not exfiltrate
crawled personal data as part of research. Follow coordinated disclosure.

## security.txt

Place at `https://<your-domain>/.well-known/security.txt`:

```
Contact: mailto:security@<your-domain>
Expires: 2027-12-31T23:59:59.000Z
Preferred-Languages: en
Canonical: https://<your-domain>/.well-known/security.txt
Policy: https://<your-domain>/SECURITY.md
```

=== END: SECURITY.md ===

---

=== BEGIN: TRADEMARK.md ===

# Trademark Policy — NEXUS

"NEXUS" is an unregistered trademark of NEXUS Contributors. This policy
explains permitted and prohibited uses. It is not a license to use the mark
in commerce in a way that suggests endorsement.

## Permitted Uses (No Permission Required)

- Referring to NEXUS in factual, descriptive statements: "this project uses
  NEXUS," "compatible with NEXUS," "a fork of NEXUS."
- Academic or journalistic references.
- Personal, non-commercial use of the name in discussion.

## Uses Requiring Permission

- Using "NEXUS" in your product name, company name, or domain name in a
  way that suggests official status.
- Using "NEXUS" on merchandise.
- Using the NEXUS logo.
- Claiming that your product is "official" or "endorsed by" NEXUS.

## Forks

Forks must be renamed. A fork may state in its documentation: "This is a
fork of NEXUS." It must not be called "NEXUS" or "NEXUS <something>". Choose
a distinct name.

## Logo

The logo is not licensed under MIT. It is reserved. Do not use it without
written permission.

## Reporting Misuse

Report trademark misuse to https://github.com/<your-org>/nexus-crawler/issues.

=== END: TRADEMARK.md ===

---

=== BEGIN: HEADERS.md ===

# Source File Headers

Add the following header to every source file in the NEXUS repository. The
SPDX short-form identifier is machine-readable and required for SBOM
generation.

## Python (.py)

```python
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 NEXUS Contributors
```

For files that import `pymupdf` (AGPL-3.0), add a second line noting the
mixed-license status:

```python
# SPDX-License-Identifier: MIT
# SPDX-License-Identifier: AGPL-3.0-or-later  # via pymupdf dependency
# Copyright (c) 2026 NEXUS Contributors
```

## Markdown (.md)

```html
<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 NEXUS Contributors -->
```

## JSON / YAML / TOML

JSON has no comment syntax. Use a `"license"` field where the schema permits.
YAML:

```yaml
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 NEXUS Contributors
```

## scripts (.ps1, .sh)

```powershell
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 NEXUS Contributors
```

```bash
#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 NEXUS Contributors
```

## Scope

Add headers to: `api_router.py`, `benchmark.py`, `config.py`, `crawler.py`,
`debug.py`, `error_fast.py`, `folder_manager.py`, `scraper.py`, `se_api.py`,
`spoof.py`. Do not add to `libraries.txt`, `expectederrors.txt`, or generated
output.

=== END: HEADERS.md ===

---

=== BEGIN: SBOM.md ===

# Software Bill of Materials — NEXUS v4.0.0

Generated 2026-01-01. Format: SPDX 2.3 (human-readable summary). For a
machine-readable SBOM, generate with `syft` or `cyclonedx-py` from
`libraries.txt`.

## Direct Dependencies

| Package | Version | License | Use |
|---|---|---|---|
| babel | 2.18.0 | BSD-3-Clause | locale parsing |
| certifi | 2026.7.22 | MPL-2.0 | CA bundle |
| cffi | 2.1.1 | MIT | C interop |
| charset-normalizer | 3.5.1 | MIT | encoding detection |
| click | 8.5.0 | BSD-3-Clause | CLI |
| cloudpickle | 3.1.2 | BSD-3-Clause | multiprocessing |
| colorama | 0.4.6 | BSD-3-Clause | terminal colors |
| courlan | 1.4.0 | Apache-2.0 | URL cleaning |
| curl-cffi | 0.16.3 | MIT | TLS impersonation |
| dateparser | 1.4.3 | BSD-3-Clause | date parsing |
| defusedxml | 0.7.1 | PSF-2.0 | safe XML |
| htmldate | 1.10.0 | Apache-2.0 | date extraction |
| joblib | 1.6.0 | BSD-3-Clause | parallel batch |
| justext | 3.0.2 | BSD-2-Clause | boilerplate removal |
| lxml | 6.1.3 | BSD-3-Clause | XML/HTML tree |
| lxml-html-clean | 0.4.5 | BSD-3-Clause | HTML sanitize |
| nltk | 3.10.3 | Apache-2.0 | stopwords |
| orjson | 3.12.0 | MIT OR Apache-2.0 | fast JSON |
| pip | 26.2.1 | MIT | package manager |
| pycparser | 3.0 | BSD-3-Clause | cffi dep |
| pymupdf | 1.28.2 | **AGPL-3.0-or-later** | PDF+OCR |
| pyphen | 0.18.1 | **GPL-2.0+ OR LGPL-2.1+ OR MPL-1.1** | hyphenation |
| python-dateutil | 2.9.0.post0 | BSD-3-Clause OR Apache-2.0 | date parsing |
| pytz | 2026.3.post1 | MIT | timezone |
| regex | 2026.9.10 | Apache-2.0 | Unicode regex |
| selectolax | 0.4.11 | MIT | HTML parser |
| setuptools | 84.0.0 | MIT | build tooling |
| six | 1.17.0 | MIT | py2/3 compat |
| textstat | 0.7.13 | MIT | readability |
| tld | 0.13.2 | MPL-1.1 OR GPL-2.0 OR LGPL-2.1 | TLD extract |
| tqdm | 4.70.1 | MIT OR MPL-2.0 | progress bars |
| trafilatura | 2.2.0 | Apache-2.0 | article extraction |
| tzdata | 2026.3 | Apache-2.0 | tz database |
| tzlocal | 5.4.4 | MIT | local tz |
| urllib3 | 2.7.0 | MIT | HTTP |

Plus `psutil` (BSD-3-Clause), required by README but not in `libraries.txt`.

## Transitive Dependencies

Not enumerated here. Generate a full SBOM with `pip-audit` or `cyclonedx-py`.
Known risk: transitive dependencies of `nltk`, `trafilatura`, and `curl-cffi`
may pull additional licenses.

## Critical Findings

1. **pymupdf (AGPL-3.0)** — incompatible with MIT redistribution of the
   combined work. See `COMPATIBILITY.md`.
2. **pyphen (tri-license)** — safe under LGPL-2.1+ or MPL-1.1; unsafe under
   GPL-2.0+. Downstream consumers must elect a non-GPL option.
3. **tld (tri-license)** — same tri-license pattern. Elect MPL-1.1 or LGPL.
4. **certifi (MPL-2.0)** — permissive, file-level copyleft only. No issue.

=== END: SBOM.md ===

---

=== BEGIN: COMPATIBILITY.md ===

# Dependency License Compatibility — NEXUS (MIT)

## Analysis

NEXUS is distributed under **MIT**. MIT is a permissive license compatible
with most permissive licenses and, in some configurations, with weak
copyleft licenses. It is **not** compatible with strong copyleft (GPL, AGPL)
for combined works in a way that allows MIT redistribution.

## Compatibility Matrix

| Dependency License | Compatible with MIT redistribution? |
|---|---|
| MIT, BSD-2, BSD-3, ISC, PSF, Apache-2.0 | ✅ Yes |
| MPL-2.0, MPL-1.1, LGPL-2.1+, LGPL-3.0 | ✅ Yes, file-level or library-level copyleft only |
| GPL-2.0+, GPL-3.0+ | ❌ No, if linked into the same work |
| AGPL-3.0+ | ❌ No, network copyleft, viral over network use |
| SSPL, BUSL | ❌ No |

## Findings

### Critical — pymupdf (AGPL-3.0-or-later)

`scraper.py` imports `pymupdf` at module level (`import pymupdf`). Under
AGPL-3.0 §13, if NEXUS is used over a network (or, arguably, if the combined
work is distributed), the operator must offer Corresponding Source under
AGPL. This contradicts MIT redistribution.

**Remedies, in order of preference:**

1. **Replace pymupdf with a permissive alternative.**
   - `pypdf` — BSD-3-Clause. Pure Python, no OCR.
   - `pdfminer.six` — MIT. Pure Python, text extraction.
   - `pikepdf` — MPL-2.0. Wrapper around QPDF.
   OCR fallback would need `pytesseract` (Apache-2.0) plus the `tesseract`
   binary (Apache-2.0) as a separate process.

2. **Relicense NEXUS to AGPL-3.0.** Legal, honest, but more restrictive
   than the README currently claims.

3. **Move pymupdf to an optional extra.** Keep `import pymupdf` lazy, behind
   a feature flag, documented as an optional install with its own license.
   This is the "mere aggregation" argument, but it is legally fragile — a
   court could still hold the combined work is a single derivative. Do not
   rely on this without counsel.

### Watch — pyphen (GPL-2.0+ OR LGPL-2.1+ OR MPL-1.1)

Tri-licensed. Under the GPL-2.0 option, MIT redistribution is incompatible.
Under LGPL-2.1+ or MPL-1.1, it is compatible. Downstream consumers must
elect a non-GPL option. Document this in `NOTICE`.

### Watch — tld (MPL-1.1 OR GPL-2.0 OR LGPL-2.1)

Same tri-license pattern. MPL-1.1 or LGPL-2.1 is fine.

### No Issue

All other direct dependencies are permissive (MIT, BSD, ISC, Apache-2.0,
PSF) or weak-copyleft with a non-GPL election option (MPL-2.0, LGPL-3.0).

## Recommendation

**Before the next release:** replace `pymupdf` with `pypdf` or `pdfminer.six`
and `pytesseract` for OCR. This is the only path that preserves the MIT
claim in the README.

**If you keep `pymupdf`:** relicense to AGPL-3.0 and update the README badge,
`LICENSE`, and `NOTICE`. The current MIT + pymupdf combination is a
compliance failure waiting to be discovered by a downstream consumer.

## Detection Script

```bash
pip install pip-licenses
pip-licenses --with-urls --format=markdown > LICENSES_THIRD_PARTY.md
# Review for GPL, AGPL, SSPL, BUSL, and copyleft entries.
```

=== END: COMPATIBILITY.md ===

---

=== BEGIN: AI_DISCLOSURE.md ===

# AI-Specific Disclosure — NEXUS

NEXUS generates corpora intended for AI training. If you use NEXUS output
to train, fine-tune, or evaluate a machine learning model, you become a
provider or deployer of an AI system under the **EU AI Act** (Regulation
(EU) 2024/1689) and may be subject to equivalent obligations elsewhere.

This document does not provide legal advice. It identifies the disclosure
surface you must address.

## 1. Training Data Provenance

NEXUS does not curate training data. It extracts it from the open web. You
are responsible for documenting the provenance of every record used in
training. The NEXUS record schema supports this:

- `url`, `canonical_url`, `domain`, `tld` — source identification.
- `crawled_at`, `published_date`, `updated_date` — temporal provenance.
- `content_hash`, `simhash`, `source_signature` — integrity provenance.
- `license` — source license, when extractable.
- `extractor_version`, `config_hash` — reproducibility.

**You must retain these fields in any training dataset.** Removing them
destroys your ability to answer provenance questions from regulators or
rights holders.

## 2. Copyright and Training Data

Crawled content is owned by its rights holders. Whether training on crawled
content is fair use (US), permitted under TDM exceptions (EU DSM Directive
Art. 4), or an infringement is jurisdiction- and fact-specific. NEXUS
provides no legal cover. Consult counsel before training on crawled data at
scale.

The EU DSM Directive Art. 4 TDM exception is opt-out. Sites that have
declared an opt-out via `robots.txt`, `ai.txt`, or machine-readable
reservations must be excluded. NEXUS does not currently implement this
filter. If you train in the EU, add it.

## 3. Personal Data in Training Corpora

Training on personal data engages GDPR Art. 6 (legal basis) and Art. 22
(automated decision-making). NEXUS provides optional PII redaction
(`AGENT_PII_REDACT_ENABLED`). It is off by default. Turn it on for any
corpus intended for model training in the EU.

## 4. EU AI Act Risk Tiers

| Tier | Obligation | NEXUS's role |
|---|---|---|
| Minimal risk | None | Most crawlers |
| Limited risk | Transparency (Art. 50) | Chatbots trained on crawled data |
| High risk | Conformity assessment (Art. 43), registration (Art. 49), data governance (Art. 10) | Biometric, critical infrastructure, education, employment, migration, justice models |
| Unacceptable | Prohibited (Art. 5) | Social scoring, manipulative AI, real-time biometric surveillance in public spaces |

If your model falls in the high-risk or prohibited tier, NEXUS does not
provide compliance. You must not use NEXUS output to train a prohibited
system, and you must implement the Art. 10 data governance obligations
(relevance, representativeness, accuracy, bias detection) yourself.

## 5. General-Purpose AI (GPAI) Models

Under AI Act Arts. 53–55, providers of GPAI models must publish a training
content summary, comply with the Copyright Directive's TDM opt-out, and (for
systemic-risk models) conduct adversarial testing. If you train a GPAI model
on NEXUS output, these obligations are yours.

## 6. Model Output Ownership

Who owns the output of a model trained on crawled data is unsettled law.
NEXUS asserts no claim over model outputs. It also asserts no claim over the
crawled data. Your rights and obligations flow from the source sites'
licenses and the applicable law.

## 7. Hallucination Disclaimer

Models trained on crawled content may hallucinate, reproduce
misinformation, or generate unlawful content. NEXUS provides no filter for
downstream outputs. Any deployment must include its own output filtering,
disclosure, and (where required) human oversight.

## 8. Dataset Cards

If you publish a dataset built from NEXUS output, publish a dataset card
documenting: source domains, crawl dates, language distribution, PII
redaction status, license mix, and known limitations. Recommended format:
Hugging Face dataset card or Datasheets for Datasets (Gebru et al., 2018).

## 9. Model Cards

If you publish a model trained on NEXUS output, publish a model card
documenting: training data provenance, evaluation results, intended use,
out-of-scope use, and known biases. Recommended format: Mitchell et al.,
2019, "Model Cards for Model Reporting."

## 10. Contact

AI compliance inquiries: https://github.com/<your-org>/nexus-crawler/issues

=== END: AI_DISCLOSURE.md ===

---

=== BEGIN: ACCESSIBILITY.md ===

# Accessibility Statement — NEXUS

**Conformance status:** NEXUS is a command-line tool. It has no graphical
user interface and therefore no WCAG conformance target. The statement below
applies to any web interface, documentation site, or dashboard that a
deployer adds on top of NEXUS.

## For the NEXUS software itself

- The CLI uses ANSI colors via `colorama`. On Windows terminals without
  `WT_SESSION`, `debug.py` degrades to plain text automatically.
- The `--no-console-logs` flag disables per-test console output.
- The `--log-file` flag redirects structured output to a file for screen
  readers or external tooling.
- Error messages are plain text and machine-parseable.

No further accessibility measures apply to a CLI tool beyond these.

## For deployer-added interfaces

If you build a web UI, dashboard, or documentation site around NEXUS, the
following targets apply:

- **WCAG 2.2 Level AA** — minimum.
- **WCAG 2.2 Level AAA** — recommended for documentation.
- **EN 301 549** — if operating in the EU.
- **Section 508** — if operating for a US federal agency.

## Conformance target

Any deployer-added interface must meet WCAG 2.2 AA. Required measures:

- Semantic HTML.
- Keyboard navigation for all functionality.
- Text alternatives for non-text content.
- Sufficient color contrast (4.5:1 for normal text, 3:1 for large text).
- Focus indicators.
- Respect for `prefers-reduced-motion`.
- No motion-triggered seizures.
- Form labels and error identification.
- Language of page declared.

## Feedback

Accessibility feedback: https://github.com/<your-org>/nexus-crawler/issues

## Assessment approach

Self-assessment. No third-party audit has been performed. Deployers must
perform their own audit before claiming conformance.

=== END: ACCESSIBILITY.md ===

---

=== BEGIN: CODE_OF_CONDUCT.md ===

# Code of Conduct — NEXUS

## Our Pledge

We as members, contributors, and maintainers pledge to make participation
in the NEXUS community a harassment-free experience for everyone, regardless
of age, body size, visible or invisible disability, ethnicity, sex
characteristics, gender identity and expression, level of experience,
education, socio-economic status, nationality, personal appearance, race,
religion, or sexual identity and orientation.

## Our Standards

Examples of behavior that contributes to a positive environment:

- Demonstrating empathy and kindness.
- Being respectful of differing opinions, viewpoints, and experiences.
- Giving and gracefully accepting constructive feedback.
- Accepting responsibility and apologizing for mistakes.
- Focusing on what is best for the community and the project.

Examples of unacceptable behavior:

- Sexualized language or imagery.
- Trolling, insulting or derogatory comments, personal or political attacks.
- Public or private harassment.
- Publishing others' private information without explicit permission.
- Using the NEXUS project to harass, dox, or target individuals.
- Other conduct which could reasonably be considered inappropriate in a
  professional setting.

## Enforcement Responsibilities

Maintainers are responsible for clarifying and enforcing these standards.
They will take appropriate and fair corrective action in response to any
behavior they deem inappropriate, threatening, offensive, or harmful.

## Scope

This Code of Conduct applies within all community spaces — GitHub issues,
pull requests, discussions, and any chat channels — and also applies when
an individual is officially representing the project in public spaces.

## Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be
reported to the maintainers at conduct@<your-domain>. All complaints will
be reviewed and investigated promptly and fairly.

Maintainers are obligated to respect the privacy and security of the
reporter of any incident.

## Enforcement Guidelines

1. **Correction** — a private written warning, with clarity around the
   violation.
2. **Warning** — a warning with consequences for continued behavior.
3. **Temporary Ban** — a temporary ban from any interaction with the
   community.
4. **Permanent Ban** — a permanent ban from any public interaction within
   the community.

## Attribution

This Code of Conduct is adapted from the Contributor Covenant, version 2.1,
available at https://www.contributor-covenant.org/version/2/1/code_of_conduct.html.

=== END: CODE_OF_CONDUCT.md ===

---

=== BEGIN: EXPORT.md ===

# Export Control and Sanctions Compliance — NEXUS

## 1. Scope

NEXUS contains cryptographic functionality via `curl-cffi`, `certifi`, and
the Python standard library `ssl` module. It may be subject to export
control and sanctions laws, including:

- **US Export Administration Regulations (EAR)** — 15 CFR Parts 730–774.
- **US International Traffic in Arms Regulations (ITAR)** — 22 CFR Parts
  120–130 (NEXUS is not defense-related; ITAR is unlikely to apply).
- **OFAC Sanctions** — 31 CFR Chapter V.
- **EU Dual-Use Regulation** — Regulation (EU) 2021/821.
- **UK Export Control Order 2008.**

## 2. Classification

NEXUS is publicly available open-source software. Under EAR §734.7 and
§740.13(e), publicly available encryption source code is generally
**not subject to EAR** when it is released publicly and the notification
requirement of §740.13(e) is met. The notification is filed with BIS and
the ENC Encryption Commodities & Software Classification Report.

NEXUS has not been classified by BIS. If you redistribute NEXUS commercially
or as part of a controlled product, you are responsible for classification.

## 3. Sanctions

You may not use, export, or re-export NEXUS:

- To any country subject to comprehensive US sanctions (currently Cuba,
  Iran, North Korea, Syria, and the Crimea, Donetsk, and Luhansk regions
  of Ukraine).
- To any person or entity on the OFAC Specially Designated Nationals (SDN)
  list, the BIS Entity List, or the EU consolidated sanctions list.
- For any prohibited end use, including nuclear, chemical, biological
  weapons, or missile technology.

## 4. Crawling as Export

Crawling sites hosted in sanctioned jurisdictions may constitute an export
of a service. The operator must screen target domains against sanctions
lists. NEXUS does not do this automatically.

## 5. End-User Screening

Operators distributing NEXUS commercially should screen end users against
consolidated sanctions lists. Free-of-charge open-source distribution
generally does not require screening, but commercial distribution does.

## 6. Encryption Notification (US)

If you choose to file the EAR §740.13(e) notification, the email address is
`crypt@bis.doc.gov` and `enc@nsa.gov`. Include the name of the software,
the URL of the source, and a description of the cryptographic functionality.

## 7. Record Keeping

Maintain records of distributions for five years, per EAR §762.6.

## 8. Contact

Export inquiries: https://github.com/<your-org>/nexus-crawler/issues

=== END: EXPORT.md ===

---

=== BEGIN: MULTI_JURIS.md ===

# Multi-Jurisdiction Overlays — NEXUS

The default suite uses Delaware, USA as the governing law and addresses EU,
UK, and California as overlays. The additional overlays below apply if NEXUS
is operated in, targets users in, or crawls content from the listed
jurisdictions.

## Brazil — LGPD (Lei 13.709/2018)

- Legal bases mirror GDPR Art. 6 (LGPD Art. 7).
- Data subject rights: confirmation, access, correction, anonymization,
  portability, deletion, information about sharing (LGPD Art. 18).
- ANPD is the supervisory authority.
- International transfers require adequacy, SCCs, or specific consent
  (LGPD Arts. 33–36).
- Add a Portuguese-language version of `PRIVACY_POLICY.md` for Brazilian
  users.

## China — PIPL, DSL, CSL

- Processing personal data requires consent or another PIPL Art. 13 basis.
- Cross-border transfers require a security assessment, standard contract
  filing, or certification (PIPL Art. 38).
- Important data and state secrets are separately regulated.
- Crawling foreign sites from within China may trigger cross-border data
  transfer rules.
- Add a Simplified Chinese version of `PRIVACY_POLICY.md`.

## India — DPDP Act, 2023

- Processing requires consent or a legitimate use (DPDP §7).
- Data principals have rights to access, correction, and erasure.
- Significant Data Fiduciaries have additional obligations (DPIA, audit,
  DPO).
- Cross-border transfers are restricted to notified countries.

## Canada — PIPEDA

- Consent-based processing.
- Breach notification to the OPC and affected individuals.
- Individual access requests must be answered within 30 days.

## Australia — Privacy Act 1988

- Australian Privacy Principles (APPs).
- Notifiable Data Breaches scheme.
- Cross-border disclosure rules (APP 8).

## South Africa — POPIA

- Lawful processing conditions (POPIA §8–25).
- Information Regulator is the supervisory authority.
- Cross-border transfers require adequate protection.

## Japan — APPI

- Consent or opt-out for third-party transfers.
- Cross-border transfer rules.
- PPC is the supervisory authority.

## South Korea — PIPA

- Consent-based processing.
- PIPC is the supervisory authority.
- Cross-border transfer notification or consent.

## Multi-Jurisdiction Operation

If NEXUS is operated from one jurisdiction but crawls content from multiple
jurisdictions, the applicable privacy law is generally determined by:

1. Where the data subject is located.
2. Where the processing occurs.
3. Where the operator is established.

The strictest applicable regime usually governs. Operators should maintain
a jurisdictional matrix and update it as operations expand.

## Recommendation

Do not claim multi-jurisdiction compliance without counsel in each
jurisdiction. This overlay identifies the surface; it does not discharge
the obligation.

=== END: MULTI_JURIS.md ===

---

=== BEGIN: MIGRATION.md ===

# License Migration Guide — NEXUS

## Current state

NEXUS is distributed under **MIT** per its README. However, the project
imports `pymupdf`, which is **AGPL-3.0**. This is a license compatibility
failure. Two migration paths are available.

## Path A — Preserve MIT (recommended)

### Step 1: Replace pymupdf

Replace `pymupdf` with `pypdf` (BSD-3-Clause) or `pdfminer.six` (MIT).

```python
# Before
import pymupdf

# After (pypdf)
from pypdf import PdfReader

# After (pdfminer.six)
from pdfminer.high_level import extract_text
```

For OCR, use `pytesseract` (Apache-2.0) invoked as a subprocess against
image files extracted by `pypdf` or `pdfminer.six`. Keep `tesseract` (the
binary) as an optional system dependency.

### Step 2: Update libraries.txt

Remove the `pymupdf==1.28.2` line. Add `pypdf` or `pdfminer.six`.

### Step 3: Update NOTICE and SBOM

Remove the pymupdf entry. Regenerate `SBOM.md`.

### Step 4: Verify

Run the test suite. Confirm PDF extraction and OCR still work. Confirm no
other module imports pymupdf.

```bash
grep -r "pymupdf" .
```

### Step 5: No license change required

The project remains MIT.

## Path B — Relicense to AGPL-3.0

If you cannot or do not want to replace pymupdf, relicense the whole project
to AGPL-3.0.

### Step 1: Replace LICENSE

Use the full AGPL-3.0 text from
https://www.gnu.org/licenses/agpl-3.0.txt.

### Step 2: Update SPDX identifiers

Change `SPDX-License-Identifier: MIT` to
`SPDX-License-Identifier: AGPL-3.0-or-later` in every source file.

### Step 3: Update README badge

Replace the MIT badge with an AGPL-3.0 badge.

### Step 4: Update NOTICE

Remove the "critical copyleft dependency" section for pymupdf (it is now
compatible). Keep the pyphen warning if you elect the GPL option there.

### Step 5: Add network source offer

AGPL-3.0 §13 requires that users interacting with the software over a
network be offered the Corresponding Source. If you operate NEXUS as a
service, add a "Source" link in the interface pointing to a canonical
repository.

### Step 6: Notify downstream

Fork maintainers and downstream redistributors must be notified. Their
existing MIT-licensed copies remain MIT (the MIT grant is irrevocable for
those copies), but new versions are AGPL-3.0.

## Path C — Do Nothing (not recommended)

The current state is a compliance risk. A downstream consumer who discovers
the pymupdf AGPL-3.0 dependency can demand that NEXUS's source be released
under AGPL. This is legal exposure. Do not choose this path.

## Timeline

Path A: 1–2 days of work.
Path B: 2–4 hours of work, plus downstream notification.
Path C: indefinite risk.

## Recommended

**Path A.** MIT is the better license for a tool intended to be widely
adopted, embedded, and extended. Replace pymupdf and keep MIT.

=== END: MIGRATION.md ===

---

=== BEGIN: AUDIT.md ===

# License Audit — NEXUS v4.0.0

## Existing files

| File | Present? | Status |
|---|---|---|
| LICENSE | Referenced in README, not verified in workspace dump | ⚠️ Verify |
| NOTICE | Missing | ❌ Add |
| TERMS_OF_USE.md | Missing | ❌ Add |
| TERMS_OF_SERVICE.md | N/A (software, not service) | ✅ N/A |
| PRIVACY_POLICY.md | Missing | ❌ Add |
| SECURITY.md | Missing | ❌ Add |
| TRADEMARK.md | Missing | ❌ Add |
| COMPATIBILITY.md | Missing | ❌ Add (critical) |
| SBOM.md | Missing | ❌ Add |
| AI_DISCLOSURE.md | Missing | ❌ Add |
| EXPORT.md | Missing | ❌ Add |
| COOKIES.md | Missing | ❌ Add |
| ACCESSIBILITY.md | Missing | ❌ Add |
| CODE_OF_CONDUCT.md | Missing | ❌ Add |
| CLA.md | Missing | ❌ Add |
| DPA.md | Missing | ❌ Add |
| SUB_PROCESSORS.md | Missing | ❌ Add |
| MULTI_JURIS.md | Missing | ❌ Add |
| MIGRATION.md | Missing | ❌ Add |
| HEADERS.md | Missing | ❌ Add |
| VERSIONS.md | Missing | ❌ Add |

## Gap analysis

### Critical (fix before next release)

1. **pymupdf AGPL-3.0 contamination.** MIT claim in README is unsupported
   by the dependency graph. See `COMPATIBILITY.md`. Fix: replace pymupdf
   or relicense to AGPL-3.0.
2. **No LICENSE file verified.** README claims MIT. Add the full text.
3. **No privacy policy** despite processing personal data (PII redactor
   exists, crawls arbitrary sites). Add `PRIVACY_POLICY.md`.
4. **No terms of use** despite crawling third-party sites. Add
   `TERMS_OF_USE.md`.

### High (fix within 30 days)

5. **No NOTICE** despite bundling many dependencies.
6. **No SECURITY.md** despite network-facing code.
7. **No AI disclosure** despite producing training corpora.
8. **No export control analysis** despite cryptographic code.
9. **pyphen tri-license ambiguity** — document the election.

### Medium (fix within 90 days)

10. No trademark policy.
11. No code of conduct.
12. No contributor agreement.
13. No SBOM.
14. No source headers with SPDX identifiers.

### Low (ongoing)

15. No accessibility statement.
16. No multi-jurisdiction overlays.
17. No legal document versioning.

## Risk-ranked fix order

1. Replace pymupdf → `COMPATIBILITY.md`, `MIGRATION.md`.
2. Add LICENSE file with full MIT text.
3. Add NOTICE with dependency attributions.
4. Add PRIVACY_POLICY.md.
5. Add TERMS_OF_USE.md.
6. Add SECURITY.md.
7. Add AI_DISCLOSURE.md.
8. Add EXPORT.md.
9. Add remaining documents.

## Note

This audit identifies gaps. It does not fix them. The full suite above
constitutes the fix.

=== END: AUDIT.md ===

---

=== BEGIN: PLAIN_LANGUAGE.md ===

# Plain-Language Summary — NEXUS

The following summary is **not legally binding**. It is a plain-language
restatement of the suite above for quick reference. If the summary and the
binding documents conflict, the binding documents govern.

## What NEXUS is

NEXUS is a free, open-source web crawler. It fetches pages, extracts text,
and produces structured records for AI dataset generation. It runs on your
machine. It has no accounts, no central server, and no paid services.

## What you can do

- Use it for anything.
- Modify it.
- Share it.
- Sell things you build with it.

## What you must not do

- Break the law.
- Break other sites' rules (robots.txt, ToS).
- Bypass paywalls or logins you are not authorized to bypass.
- Collect personal data without a legal basis.
- Generate CSAM. Ever.
- Harass or stalk anyone.

## What you are responsible for

- Complying with the laws of your country.
- Complying with the terms of service of every site you crawl.
- Complying with the terms of service of every external service NEXUS
  contacts.
- Complying with privacy law if you crawl personal data.
- Complying with copyright law if you use crawled content.
- Complying with AI law if you train models on the output.
- Securing your machine and any datasets you extract.

## What the authors are responsible for

- Providing the software as-is, with no warranty.
- Nothing else. The authors are not liable for what you do with it.

## The one big legal issue

NEXUS uses `pymupdf`, which is AGPL-3.0. AGPL is a strong copyleft license.
Shipping NEXUS as MIT with pymupdf inside is a conflict. The fix is either
to replace pymupdf (recommended) or to relicense NEXUS to AGPL-3.0. See
`COMPATIBILITY.md` and `MIGRATION.md`.

## The one big legal question about crawling

Whether crawling a site is legal depends on the site, the jurisdiction, and
what you do with the content. "Publicly accessible" does not mean "free to
scrape and reuse." Consult counsel if you crawl at scale or for commercial
purposes.

## Where to get help

- Security: see `SECURITY.md`.
- Conduct: see `CODE_OF_CONDUCT.md`.
- Legal questions: consult a lawyer. This project does not provide legal
  advice.

=== END: PLAIN_LANGUAGE.md ===

---

=== BEGIN: VERSIONS.md ===

# Legal Document Versions — NEXUS

Each legal document in this suite is versioned independently using semantic
versioning. **Major** = material change to rights or obligations. **Minor** =
clarification or addition. **Patch** = typo or formatting.

| Document | Version | Effective | Change log |
|---|---|---|---|
| LICENSE | 1.0.0 | 2026-01-01 | Initial MIT |
| NOTICE | 1.0.0 | 2026-01-01 | Initial inventory |
| TERMS_OF_USE.md | 1.0.0 | 2026-01-01 | Initial |
| TERMS_OF_SERVICE.md | 1.0.0 | 2026-01-01 | Initial (N/A + template) |
| PRIVACY_POLICY.md | 1.0.0 | 2026-01-01 | Initial |
| TERMS_OF_NEXUS.md | 1.0.0 | 2026-01-01 | Initial |
| CLA.md | 1.0.0 | 2026-01-01 | Initial DCO |
| DPA.md | 1.0.0 | 2026-01-01 | Initial template |
| SUB_PROCESSORS.md | 1.0.0 | 2026-01-01 | Initial |
| COOKIES.md | 1.0.0 | 2026-01-01 | Initial |
| SECURITY.md | 1.0.0 | 2026-01-01 | Initial |
| TRADEMARK.md | 1.0.0 | 2026-01-01 | Initial |
| HEADERS.md | 1.0.0 | 2026-01-01 | Initial |
| SBOM.md | 1.0.0 | 2026-01-01 | Initial |
| COMPATIBILITY.md | 1.0.0 | 2026-01-01 | Initial |
| AI_DISCLOSURE.md | 1.0.0 | 2026-01-01 | Initial |
| ACCESSIBILITY.md | 1.0.0 | 2026-01-01 | Initial |
| CODE_OF_CONDUCT.md | 1.0.0 | 2026-01-01 | Initial |
| EXPORT.md | 1.0.0 | 2026-01-01 | Initial |
| MULTI_JURIS.md | 1.0.0 | 2026-01-01 | Initial |
| MIGRATION.md | 1.0.0 | 2026-01-01 | Initial |
| AUDIT.md | 1.0.0 | 2026-01-01 | Initial |
| PLAIN_LANGUAGE.md | 1.0.0 | 2026-01-01 | Initial |
| VERSIONS.md | 1.0.0 | 2026-01-01 | Initial |

## Change log format

When a document changes, append an entry:

```
## [x.y.z] — YYYY-MM-DD
### Changed
- <what changed and why>
### Migration
- <what the user must do, if anything>
```

## Effective dates

- **Patch** changes take effect immediately.
- **Minor** changes take effect on publication.
- **Major** changes take effect 30 days after publication, with notice in
  `CHANGELOG.md`.

## Version pinning

Downstream consumers may pin to a specific version of the legal suite. The
canonical reference is the Git tag `legal-vX.Y.Z` in the repository.

=== END: VERSIONS.md ===

---
