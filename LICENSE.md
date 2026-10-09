Generated legal documentation suite, not legal advice. Review with qualified counsel before use.

**Jurisdiction default:** Delaware, USA. Overlays for EU, UK, and California applied. Regenerate with a different jurisdiction if needed.

**License type:** Open-Limited-Source Project (OLSP). Source is visible for study, verification, and research. Modification, redistribution, and commercial use are prohibited. All rights retained by the author.

---

## LICENSE

Open-Limited-Source Project License (OLSP) v1.0

Copyright (c) 2026 PurpleXPurple. All rights reserved.

SPDX-License-Identifier: LicenseRef-OLSP-1.0

This license applies to the software in this repository ("the Software"), including all source code, configuration, documentation, and accompanying materials, unless a file explicitly states otherwise.

1. GRANT OF PERMISSION

Subject to the terms of this License, you are granted a worldwide, royalty-free, non-exclusive, non-transferable, revocable permission to:

(a) view, download, and inspect the source code of the Software;
(b) run the Software for personal, educational, research, or other strictly non-commercial purposes;
(c) study the source code for transparency, security review, reproducibility, and academic evaluation.

2. RESTRICTIONS

You may NOT, without prior written permission from the copyright holder:

(a) modify, adapt, translate, or create derivative works of the Software;
(b) redistribute, sublicense, rent, lease, publish, or otherwise make the Software or any modified version available to any third party, whether for free or for a fee;
(c) use the Software, in whole or in part, for any commercial purpose, including as part of a product or service offered to others;
(d) use the Software to develop a competing product or service;
(e) remove, obscure, or alter any copyright, attribution, or license notice contained in the Software.

3. SOURCE AVAILABILITY IS NOT AN OPEN LICENSE

The source code may be visible for transparency and auditability so that you can verify what the Software does before running it on your own hardware. Making the source code visible does NOT grant any rights beyond those explicitly stated in Section 1. Visibility of the source code does not imply permission to modify, redistribute, or create derivative works.

4. RESEARCH AND EDUCATIONAL USE

Permitted research and educational use includes:

(a) academic study of the Software's algorithms, architecture, and methodology;
(b) citation of the Software in scholarly papers, theses, dissertations, and academic presentations, with proper attribution;
(c) use of the Software as a reference implementation for comparison in academic work;
(d) use of the Software in a classroom or laboratory setting for teaching purposes.

Research use does not include use in a commercial research context, use in a for-profit research laboratory, or use in research funded by an entity that will commercially exploit the results.

5. ATTRIBUTION

Any permitted use, reference, or citation of the Software must provide clear and visible attribution to the original creator as: "PurpleXPurple, NEXUS Universal Crawler, https://github.com/PurpleXPurple/Scraper." If the Software is used in academic work, citation in the bibliography or acknowledgments section is required.

6. TRADEMARKS

The names "NEXUS," "PurpleXPurple," and any associated logos, branding, or trademarks are reserved to the copyright holder. You may not use these names, or any confusingly confusingly similar name, to identify any modified version, fork, or derivative work, or any other software or service, without prior written permission.

7. NO CONTRIBUTIONS

This project does not accept external contributions. The Software is maintained solely by the copyright holder. Do not submit pull requests, patches, or other contributions. Any unsolicited contribution is not licensed to the project and will not be incorporated.

8. THIRD-PARTY COMPONENTS

Third-party components referenced by the Software remain under their own licenses, which govern those components. See the NOTICE file for the full list. The copyright holder of this Software makes no representation regarding the licensing of third-party components.

9. NO WARRANTY

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT. THE COPYRIGHT HOLDER MAKES NO WARRANTY THAT THE SOFTWARE WILL BE ERROR-FREE, THAT IT WILL NOT VIOLATE ANY THIRD-PARTY TERMS OF SERVICE, OR THAT CRAWLED CONTENT WILL BE LAWFUL TO USE.

10. LIMITATION OF LIABILITY

IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE, ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

11. TERMINATION

This License terminates automatically, without notice, if you breach any of its terms. Upon termination, you must stop using the Software and destroy all copies in your possession or control, except as required to preserve evidence of the breach.

12. GOVERNING LAW

This License is governed by the laws of the State of Delaware, USA, without regard to its conflict-of-law principles. For users in the European Union, mandatory consumer protection rights of the user's country of residence apply where required by law.

13. REQUESTING ADDITIONAL RIGHTS

If you wish to use the Software beyond the scope of this License (for example, for commercial purposes, modification, or redistribution), contact the copyright holder via https://github.com/PurpleXPurple/Scraper.

---

## NOTICE

NEXUS Universal Crawler

Copyright (c) 2026 PurpleXPurple. All rights reserved.

This product includes software developed by third parties. The following components are imported, bundled, or required at runtime.

CRITICAL: COPYLEFT DEPENDENCIES

pymupdf — AGPL-3.0-or-later

- Upstream: https://github.com/pymupdf/PyMuPDF
- Used in: scraper.py for PDF extraction and OCR fallback.
- Impact: The AGPL-3.0 network copyleft applies to the combined work if NEXUS is distributed or operated over a network. Under the OLSP, redistribution is prohibited, so the network-copyleft obligation is not triggered by distribution. However, operators who run NEXUS locally with pymupdf are using AGPL-licensed code and should review AGPL-3.0 Section 13 obligations if they ever expose the Software over a network.
- Remedy: If the copyright holder later decides to permit redistribution, pymupdf must be replaced with a permissive alternative (pypdf, BSD-3-Clause; or pdfminer.six, MIT) or the project must be relicensed to AGPL-3.0.

pyphen — GPL-2.0-or-later OR LGPL-2.1-or-later OR MPL-1.1

- Upstream: https://github.com/Kozea/Pyphen
- Used in: scraper.py for hyphenation.
- Impact: Safe under LGPL-2.1-or-later or MPL-1.1. Unsafe under GPL-2.0-or-later if the combined work is ever redistributed.

tld — MPL-1.1 OR GPL-2.0 OR LGPL-2.1

- Upstream: https://github.com/barseghyanartur/tld
- Impact: Same tri-license pattern as pyphen.

PERMISSIVE DEPENDENCIES

Apache-2.0: trafilatura, courlan, htmldate, nltk, regex, tzdata.

BSD-2-Clause or BSD-3-Clause: lxml, lxml-html-clean, justext, dateparser, babel, psutil, python-dateutil, pytz, six, click, cloudpickle, colorama, joblib, pycparser.

MIT: curl-cffi, selectolax, orjson, textstat, tzlocal, six, pip, setuptools, charset-normalizer, cffi, tqdm, urllib3.

ISC: certifi.

PSF-2.0: defusedxml.

Python Software Foundation License: Python standard library components.

EXTERNAL SERVICES CONTACTED AT RUNTIME

Stack Exchange API, Wayback Machine, Common Crawl, APIs.guru, Certificate Transparency (crt.sh), Google Public DNS, Cloudflare DNS, Quad9 DNS, hstspreload.org, ip-api.com, urlscan.io, DuckDuckGo Instant Answer, Datamuse, Wikipedia REST API, Jina Reader, Firecrawl, ReplyFast, Web2MD, Microlink, Kiprio, CORS relays (corsproxy.io, AllOrigins, cors.lol, Corsfix, KillCors), RapidAPI, archive.today, RDAP.

CONTENT LICENSE NOTES

Content extracted by NEXUS from third-party websites is not licensed by this project. Extracted content carries the license of its source. Wikipedia content is CC BY-SA 4.0. Stack Exchange content is CC BY-SA 4.0 (or 3.0 for older posts). The operator is responsible for compliance with each source's license.

---

## TERMS_OF_USE

Version 1.0.0. Effective 2026-01-01.

1. ACCEPTANCE

By downloading, installing, or using NEXUS (the "Software"), you accept these Terms of Use. If you do not accept them, do not use the Software.

2. ELIGIBILITY

You must be at least 16 years of age, or the age of digital consent in your jurisdiction, whichever is higher, to use the Software.

3. LICENSE GRANT

The Software is licensed under the Open-Limited-Source Project License (OLSP) v1.0. Subject to your compliance with these Terms and the OLSP, you are granted a worldwide, non-exclusive, royalty-free, non-transferable, revocable license to view, download, study, and run the Software for research, educational, and other strictly non-commercial purposes.

4. PERMITTED USE

You may use NEXUS to:

(a) crawl websites you own or have authorization to crawl, for research or educational purposes;
(b) study the source code for academic evaluation;
(c) run the Software locally on your own hardware for personal research;
(d) cite the Software in academic work with proper attribution.

5. PROHIBITED CONDUCT

You must not use NEXUS to:

(a) violate any applicable law, including the Computer Fraud and Abuse Act (18 U.S.C. Section 1030), the Digital Millennium Copyright Act, the EU Digital Services Act, or any analogous law;
(b) crawl content behind authentication walls you are not authorized to access;
(c) bypass paywalls, CAPTCHAs, or access controls you are not authorized to bypass;
(d) collect, process, or distribute personal data in violation of GDPR, UK GDPR, CCPA/CPRA, or any other applicable privacy law;
(e) collect, generate, or distribute child sexual abuse material. This prohibition is absolute and non-negotiable;
(f) harass, stalk, dox, or harm any individual;
(g) generate content intended to defraud, impersonate, or deceive;
(h) violate the terms of service of any site you crawl;
(i) modify, redistribute, sublicense, or commercially exploit the Software.

6. INTELLECTUAL PROPERTY

The Software is owned by PurpleXPurple and licensed under the OLSP. The "NEXUS" name and logo are reserved trademarks of PurpleXPurple. You may not use the name "NEXUS" to endorse or promote products derived from the Software without prior written permission.

Content extracted by the Software from third-party sites is owned by its respective rights holders and is not licensed by this project.

7. USER CONTENT

NEXUS does not host user content. It runs locally on your machine and writes output to your local filesystem. You are solely responsible for the content you crawl and the datasets you generate.

8. FEEDBACK

This project does not accept contributions. Do not submit feedback, bug reports, or feature requests expecting incorporation. Any unsolicited communication is not licensed to the project.

9. DISCLAIMERS

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT. THE AUTHOR MAKES NO WARRANTY THAT THE SOFTWARE WILL NOT VIOLATE ANY THIRD-PARTY TERMS OF SERVICE, THAT CRAWLED CONTENT WILL BE LAWFUL TO USE, OR THAT THE SOFTWARE WILL BE ERROR-FREE.

10. LIMITATION OF LIABILITY

IN NO EVENT SHALL THE AUTHOR OR COPYRIGHT HOLDER BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE, ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

11. INDEMNIFICATION

You agree to indemnify and hold harmless PurpleXPurple from any claim arising out of your use of the Software, including claims by third parties whose sites you crawl, claims by data subjects whose personal data you process, and claims by rights holders whose content you extract.

12. TERMINATION

These Terms terminate automatically if you breach them. The OLSP license terminates automatically if you breach its terms.

13. GOVERNING LAW

These Terms are governed by the laws of the State of Delaware, USA, without regard to its conflict-of-laws principles. For EU users, mandatory consumer protection rights of your country of residence apply.

14. DISPUTE RESOLUTION

Disputes arising under these Terms shall be resolved by binding arbitration in Wilmington, Delaware, under the rules of the American Arbitration Association. EU users retain the right to bring claims before their local courts.

15. CHANGES

The author may update these Terms. Material changes will be announced in the repository's CHANGELOG.md and will take effect 30 days after publication.

16. CONTACT

https://github.com/PurpleXPurple/Scraper

---

## PRIVACY_POLICY

Version 1.0.0. Effective 2026-01-01.

1. DATA CONTROLLER

For personal data processed during your use of NEXUS, you are the data controller. PurpleXPurple does not receive, store, or process any data generated by your use of the Software.

2. DATA CATEGORIES PROCESSED LOCALLY

When you run NEXUS, it processes:

(a) URLs you provide as seeds or discover during crawling;
(b) HTTP response bodies returned by sites you crawl;
(c) HTTP headers including cookies, ETags, and Last-Modified values;
(d) extracted text, metadata, entities, keywords, and chunks derived from crawled content;
(e) personal data present in crawled content (emails, phone numbers, SSNs, credit cards, IP addresses);
(f) operational data including logs, rate-limit state, dedup hashes, and cache entries.

All of the above are stored on your local filesystem under the .data directory. None of it is transmitted to PurpleXPurple.

3. THIRD-PARTY SERVICES CONTACTED

NEXUS contacts external services at runtime. Each service receives at minimum the request URL and your IP address. See the NOTICE file for the full list.

4. LEGAL BASIS

If you process personal data using NEXUS, you must establish a legal basis under GDPR Article 6. For crawling publicly available content, common bases include legitimate interests (Art. 6(1)(f)) for research or academic purposes, subject to a balancing test.

Special category data (Art. 9) requires an Art. 9 condition. NEXUS does not provide one. Do not crawl such data unless you have a lawful basis.

5. DATA SUBJECT RIGHTS

If you crawl content containing personal data, data subjects may contact you to exercise rights of access, rectification, erasure, restriction, portability, and objection. You must respond within the statutory period.

6. RETENTION

NEXUS retains crawled data on your local filesystem until you delete it. Default retention is indefinite. To comply with GDPR Art. 5(1)(e), configure retention limits and periodically purge.

7. INTERNATIONAL TRANSFERS

If you transfer personal data extracted by NEXUS outside the EEA/UK, you must ensure a valid transfer mechanism. NEXUS itself does not transfer data. You do.

8. SECURITY

NEXUS implements reasonable technical measures. You are responsible for securing the machine on which NEXUS runs and any datasets you extract.

9. COOKIES AND TRACKING

NEXUS does not set cookies on user devices. When crawling, NEXUS may receive cookies from target sites and stores them under .data/cookies for session continuity.

10. CHILDREN'S PRIVACY

NEXUS is not directed at children under 16. Do not use NEXUS to crawl content directed at children without complying with COPPA (US), GDPR Art. 8 (EU), or equivalent.

11. AI TRAINING DATA

If you use NEXUS output to train machine learning models, you are a provider of an AI system under the EU AI Act (Regulation (EU) 2024/1689). You must comply with transparency, data governance, and conformity assessment obligations. See the AI_DISCLOSURE file.

12. CHANGES

Material changes will be announced in CHANGELOG.md and take effect 30 days after publication.

13. CONTACT

https://github.com/PurpleXPurple/Scraper

---

## SECURITY

Supported Versions

Version 4.x: supported.
Version 3.x: critical fixes only.
Version 2.x and earlier: unsupported.

Reporting a Vulnerability

Do not open public issues for security vulnerabilities. Contact the author via https://github.com/PurpleXPurple/Scraper. If a private security advisory mechanism is available on GitHub, use it.

What to Include

Description of the vulnerability, steps to reproduce, affected versions, impact assessment, suggested fix (if any), and whether you intend to publish a write-up.

Response Timeline

Acknowledgement within 3 business days. Initial assessment within 7 business days. Fix or mitigation within 30 days for high-severity.

Scope

In scope: remote code execution via crafted crawled content, SQL injection in cache or dedup stores, path traversal in file writes, dependency vulnerabilities.

Out of scope: the fact that NEXUS crawls sites, rate limiting on target sites, detection by anti-bot systems, vulnerabilities in third-party services.

Safe Harbor

Good-faith security research on NEXUS is authorized. Do not test against third-party sites using NEXUS without authorization. Follow coordinated disclosure.

---

## TRADEMARK

"NEXUS" is a reserved trademark of PurpleXPurple. This policy explains permitted and prohibited uses.

Permitted Uses (No Permission Required)

Referring to NEXUS in factual, descriptive statements. Academic or journalistic references. Personal, non-commercial use of the name in discussion.

Uses Requiring Permission

Using "NEXUS" in a product name, company name, or domain name in a way that suggests official status. Using "NEXUS" on merchandise. Using the NEXUS logo. Claiming that a product is "official" or "endorsed by" NEXUS.

Forks

This project does not permit forks. The OLSP prohibits modification and redistribution. Any fork is a breach of the license.

Logo

The logo is not licensed. It is reserved. Do not use it without written permission.

---

## AI_DISCLOSURE

NEXUS generates corpora intended for research and academic study. If you use NEXUS output to train, fine-tune, or evaluate a machine learning model, you become a provider or deployer of an AI system under the EU AI Act (Regulation (EU) 2024/1689) and may be subject to equivalent obligations elsewhere.

1. TRAINING DATA PROVENANCE

NEXUS does not curate training data. You are responsible for documenting the provenance of every record used in training. The NEXUS record schema supports this via url, canonical_url, domain, tld, crawled_at, published_date, updated_date, content_hash, simhash, source_signature, license, extractor_version, and config_hash.

2. COPYRIGHT AND TRAINING DATA

Crawled content is owned by its rights holders. Whether training on crawled content is fair use, permitted under TDM exceptions, or an infringement is jurisdiction- and fact-specific. Consult counsel before training on crawled data at scale.

3. PERSONAL DATA IN TRAINING CORPORA

Training on personal data engages GDPR Art. 6 and Art. 22. NEXUS provides optional PII redaction. It is off by default. Turn it on for any corpus intended for model training in the EU.

4. EU AI ACT RISK TIERS

Minimal risk: no obligations. Limited risk: transparency obligations. High risk: conformity assessment, registration, data governance. Unacceptable risk: prohibited.

If your model falls in the high-risk or prohibited tier, NEXUS does not provide compliance. You must not use NEXUS output to train a prohibited system.

5. GENERAL-PURPOSE AI MODELS

Under AI Act Arts. 53 to 55, providers of GPAI models must publish a training content summary, comply with the TDM opt-out, and conduct adversarial testing for systemic-risk models. If you train a GPAI model on NEXUS output, these obligations are yours.

6. MODEL OUTPUT OWNERSHIP

Who owns the output of a model trained on crawled data is unsettled law. NEXUS asserts no claim over model outputs. It also asserts no claim over the crawled data.

7. HALLUCINATION DISCLAIMER

Models trained on crawled content may hallucinate, reproduce misinformation, or generate unlawful content. NEXUS provides no filter for downstream outputs.

8. DATASET CARDS

If you publish a dataset built from NEXUS output, publish a dataset card documenting source domains, crawl dates, language distribution, PII redaction status, license mix, and known limitations.

9. MODEL CARDS

If you publish a model trained on NEXUS output, publish a model card documenting training data provenance, evaluation results, intended use, out-of-scope use, and known biases.

10. CONTACT

https://github.com/PurpleXPurple/Scraper

---

## EXPORT

1. SCOPE

NEXUS contains cryptographic functionality via curl-cffi, certifi, and the Python standard library ssl module. It may be subject to export control and sanctions laws, including US EAR, OFAC sanctions, EU Dual-Use Regulation, and UK Export Control Order.

2. CLASSIFICATION

NEXUS is publicly available software. Under EAR Section 734.7 and Section 740.13(e), publicly available encryption source code is generally not subject to EAR when released publicly. NEXUS has not been classified by BIS. If you redistribute NEXUS commercially, you are responsible for classification.

3. SANCTIONS

You may not use, export, or re-export NEXUS to any country subject to comprehensive US sanctions, to any person or entity on the OFAC SDN list, the BIS Entity List, or the EU consolidated sanctions list, or for any prohibited end use.

4. CRAWLING AS EXPORT

Crawling sites hosted in sanctioned jurisdictions may constitute an export of a service. The operator must screen target domains against sanctions lists. NEXUS does not do this automatically.

5. RECORD KEEPING

If you distribute NEXUS commercially, maintain records of distributions for five years per EAR Section 762.6.

6. CONTACT

https://github.com/PurpleXPurple/Scraper

---

## ACCESSIBILITY

NEXUS is a command-line tool. It has no graphical user interface and therefore no WCAG conformance target.

For the NEXUS software itself:

The CLI uses ANSI colors via colorama. On Windows terminals without WT_SESSION, debug.py degrades to plain text automatically. The --no-console-logs flag disables per-test console output. The --log-file flag redirects structured output to a file. Error messages are plain text and machine-parseable.

No further accessibility measures apply to a CLI tool beyond these.

If a deployer adds a web interface, dashboard, or documentation site, that interface must meet WCAG 2.2 Level AA as a minimum. NEXUS itself does not provide such an interface.

---

## CODE_OF_CONDUCT

This project is maintained solely by PurpleXPurple. It does not have a community, does not accept contributions, and does not operate issues or discussions for community interaction.

This Code of Conduct applies only if the author opens a public interaction surface in the future. Until then, it has no scope.

1. OUR PLEDGE

We pledge to make participation in any future NEXUS community a harassment-free experience for everyone.

2. OUR STANDARDS

Positive behavior includes empathy, respect for differing opinions, constructive feedback, and accepting responsibility.

Unacceptable behavior includes sexualized language, trolling, insults, harassment, and publishing others' private information.

3. ENFORCEMENT

Reports may be sent to the author via https://github.com/PurpleXPurple/Scraper.

4. ATTRIBUTION

Adapted from the Contributor Covenant, version 2.1.

---

## CONTRIBUTING

This project does not accept external contributions.

The Software is maintained solely by PurpleXPurple. Do not submit pull requests, patches, or other contributions. Any unsolicited contribution is not licensed to the project and will not be incorporated.

If you have a security vulnerability to report, see the SECURITY file.

If you have a legal concern, see the TERMS_OF_USE file.

---

## SBOM

Software Bill of Materials. NEXUS v4.0.0. Generated 2026-01-01.

Direct Dependencies

babel 2.18.0. BSD-3-Clause. Locale parsing.
certifi 2026.7.22. MPL-2.0. CA bundle.
cffi 2.1.1. MIT. C interop.
charset-normalizer 3.5.1. MIT. Encoding detection.
click 8.5.0. BSD-3-Clause. CLI.
cloudpickle 3.1.2. BSD-3-Clause. Multiprocessing.
colorama 0.4.6. BSD-3-Clause. Terminal colors.
courlan 1.4.0. Apache-2.0. URL cleaning.
curl-cffi 0.16.3. MIT. TLS impersonation.
dateparser 1.4.3. BSD-3-Clause. Date parsing.
defusedxml 0.7.1. PSF-2.0. Safe XML.
htmldate 1.10.0. Apache-2.0. Date extraction.
joblib 1.6.0. BSD-3-Clause. Parallel batch.
justext 3.0.2. BSD-2-Clause. Boilerplate removal.
lxml 6.1.3. BSD-3-Clause. XML/HTML tree.
lxml-html-clean 0.4.5. BSD-3-Clause. HTML sanitize.
nltk 3.10.3. Apache-2.0. Stopwords.
orjson 3.12.0. MIT OR Apache-2.0. Fast JSON.
pip 26.2.1. MIT. Package manager.
pycparser 3.0. BSD-3-Clause. cffi dependency.
pymupdf 1.28.2. AGPL-3.0-or-later. PDF and OCR. Critical.
pyphen 0.18.1. GPL-2.0+ OR LGPL-2.1+ OR MPL-1.1. Hyphenation. Watch.
python-dateutil 2.9.0.post0. BSD-3-Clause OR Apache-2.0. Date parsing.
pytz 2026.3.post1. MIT. Timezone.
regex 2026.9.10. Apache-2.0. Unicode regex.
selectolax 0.4.11. MIT. HTML parser.
setuptools 84.0.0. MIT. Build tooling.
six 1.17.0. MIT. Compatibility.
textstat 0.7.13. MIT. Readability.
tld 0.13.2. MPL-1.1 OR GPL-2.0 OR LGPL-2.1. TLD extract. Watch.
tqdm 4.70.1. MIT OR MPL-2.0. Progress bars.
trafilatura 2.2.0. Apache-2.0. Article extraction.
tzdata 2026.3. Apache-2.0. Timezone database.
tzlocal 5.4.4. MIT. Local timezone.
urllib3 2.7.0. MIT. HTTP client.

Plus psutil. BSD-3-Clause. Required by README but not in libraries.txt.

Transitive Dependencies

Not enumerated. Generate a full SBOM with pip-audit or cyclonedx-py.

Critical Findings

1. pymupdf (AGPL-3.0) is incompatible with permissive licensing. Under OLSP, redistribution is prohibited, so the distribution-triggered copyleft is not activated. However, if the Software is ever exposed over a network, AGPL Section 13 obligations may apply. See the COMPATIBILITY file.
2. pyphen (tri-license). Safe under LGPL-2.1+ or MPL-1.1. Unsafe under GPL-2.0+ if redistributed.
3. tld (tri-license). Same pattern.
4. certifi (MPL-2.0). File-level copyleft only. No issue.

---

## COMPATIBILITY

Dependency License Compatibility for the OLSP

The OLSP is a source-available, research-only license that prohibits modification and redistribution. It is not OSI-approved and is not an open-source license.

Compatibility Matrix

MIT, BSD-2, BSD-3, ISC, PSF, Apache-2.0: compatible.
MPL-2.0, MPL-1.1, LGPL-2.1+, LGPL-3.0: compatible at file-level or library-level.
GPL-2.0+, GPL-3.0+: incompatible if linked into the same work and redistributed.
AGPL-3.0+: incompatible if distributed or exposed over a network.

Findings

Critical: pymupdf (AGPL-3.0-or-later)

scraper.py imports pymupdf at module level. Under AGPL-3.0 Section 13, if the Software is exposed over a network, the operator must offer Corresponding Source under AGPL. The OLSP prohibits redistribution, which avoids the distribution-triggered obligation. But network exposure is not covered by the OLSP prohibition.

Remedies, in order of preference:

1. Replace pymupdf with pypdf (BSD-3-Clause) or pdfminer.six (MIT). For OCR, use pytesseract (Apache-2.0) as a separate process.
2. Keep pymupdf but document that any network exposure of NEXUS triggers AGPL Section 13 and the operator must comply.
3. Move pymupdf to an optional extra. Lazy import behind a feature flag. Legally fragile without counsel.

Watch: pyphen (GPL-2.0+ OR LGPL-2.1+ OR MPL-1.1)

Tri-licensed. Under the GPL option, redistribution is incompatible. Under LGPL or MPL, compatible. Downstream consumers must elect LGPL-2.1+ or MPL-1.1.

Watch: tld (MPL-1.1 OR GPL-2.0 OR LGPL-2.1)

Same tri-license pattern.

No Issue

All other direct dependencies are permissive or weak-copyleft with a non-GPL election option.

Recommendation

Under the OLSP, redistribution is prohibited, so the distribution-triggered copyleft of pymupdf is not activated. However, if the copyright holder ever decides to permit redistribution, pymupdf must be replaced. Document the current state in the NOTICE file.

Detection Script

pip install pip-licenses. pip-licenses --with-urls --format markdown. Review for GPL, AGPL, SSPL, BUSL, and copyleft entries.

---

## VERSIONS

Each legal document in this suite is versioned independently using semantic versioning. Major indicates a material change to rights or obligations. Minor indicates a clarification or addition. Patch indicates a typo or formatting.

LICENSE: 1.0.0. 2026-01-01. Initial OLSP.
NOTICE: 1.0.0. 2026-01-01. Initial inventory.
TERMS_OF_USE: 1.0.0. 2026-01-01. Initial.
PRIVACY_POLICY: 1.0.0. 2026-01-01. Initial.
SECURITY: 1.0.0. 2026-01-01. Initial.
TRADEMARK: 1.0.0. 2026-01-01. Initial.
AI_DISCLOSURE: 1.0.0. 2026-01-01. Initial.
EXPORT: 1.0.0. 2026-01-01. Initial.
ACCESSIBILITY: 1.0.0. 2026-01-01. Initial.
CODE_OF_CONDUCT: 1.0.0. 2026-01-01. Initial.
CONTRIBUTING: 1.0.0. 2026-01-01. Initial.
SBOM: 1.0.0. 2026-01-01. Initial.
COMPATIBILITY: 1.0.0. 2026-01-01. Initial.
VERSIONS: 1.0.0. 2026-01-01. Initial.

Change log format: when a document changes, append an entry with the version, date, what changed, and what the user must do.

Effective dates: patch changes take effect immediately. Minor changes take effect on publication. Major changes take effect 30 days after publication.

---

## PLAIN_LANGUAGE

The following summary is not legally binding. If the summary and the binding documents conflict, the binding documents govern.

What NEXUS is

NEXUS is a universal cross-domain web crawler for AI dataset generation. It runs locally on your machine. It has no accounts, no central server, and no paid services.

What you can do

You can view, download, study, and run NEXUS for research, education, and personal non-commercial purposes. You can cite it in academic work.

What you must not do

You must not modify, redistribute, sublicense, or commercially exploit NEXUS. You must not break the law, break other sites' rules, bypass paywalls, collect personal data without a legal basis, or generate child sexual abuse material.

What you are responsible for

You are responsible for complying with the laws of your country, the terms of service of every site you crawl, the terms of service of every external service NEXUS contacts, privacy law if you crawl personal data, copyright law if you use crawled content, and AI law if you train models on the output.

What the author is responsible for

Providing the software as-is, with no warranty. Nothing else.

The one big legal issue

NEXUS uses pymupdf, which is AGPL-3.0. If you ever expose NEXUS over a network, AGPL Section 13 may require you to offer the source under AGPL. See the COMPATIBILITY file.

The one big legal question about crawling

Whether crawling a site is legal depends on the site, the jurisdiction, and what you do with the content. Publicly accessible does not mean free to scrape and reuse. Consult counsel if you crawl at scale.

Where to get help

Security: see the SECURITY file. Conduct: see the CODE_OF_CONDUCT file. Legal questions: consult a lawyer. This project does not provide legal advice.

---

=== END OF LICENSE SUITE ===

---

=== BEGIN LAW ===

Legal Risk and Liability Auditor

Risk identification, not legal advice. State this once.

Project Snapshot

NEXUS Universal Crawler. Source-available at https://github.com/PurpleXPurple/Scraper. Distributed under the Open-Limited-Source Project License (OLSP) v1.0, a custom source-available license that permits research, educational, and personal non-commercial use, and prohibits modification, redistribution, and commercial use. Stack: Python 3.14, curl-cffi, selectolax, trafilatura, pymupdf, orjson. Distribution model: public GitHub repository, local execution only. Monetization: none. Data handled: crawls arbitrary public web content, which may include personal data. Jurisdiction of operation: default Delaware, USA. Jurisdiction of users: worldwide. Jurisdiction of incorporation: not stated.

RISK REGISTER

1. LICENSE ENFORCEABILITY

Risk: The OLSP is a custom, non-standard license. Its enforceability is untested. If a downstream consumer ignores the restrictions, enforcement depends on contract law, not copyright law alone. Custom licenses are enforceable in most jurisdictions but require clear acceptance and consideration.

Trigger: A third party modifies, redistributes, or commercially exploits NEXUS.

Who could bring it: The copyright holder (PurpleXPurple).

Exposure: Loss of control over the Software. No statutory damages unless registered with the US Copyright Office. Attorney fees and litigation costs.

Likelihood: Medium if the project gains visibility. Low otherwise.

How (Self): Register the copyright with the US Copyright Office. Add a clickwrap or browsewrap acceptance mechanism if the project grows. Keep clear records of the license text and date of first publication. Consider using a standard source-available license (PolyForm Noncommercial) as a fallback if the custom license is challenged.

How (Nexus): /Law.

2. PYMUPDF AGPL-3.0 CONTAMINATION

Risk: pymupdf is AGPL-3.0. AGPL Section 13 requires that users interacting with the software over a network be offered the Corresponding Source. The OLSP prohibits redistribution, which avoids the distribution-triggered obligation, but does not cover network exposure.

Trigger: Exposing NEXUS as a network service (API, web interface, or hosted crawler) without offering source under AGPL.

Who could bring it: pymupdf's copyright holders (Artifex Software), the AGPL enforcement community, or a downstream consumer who discovers the dependency.

Exposure: Injunction requiring source release. Statutory damages. Attorney fees. Loss of the OLSP license (the combined work would be AGPL, not OLSP).

Likelihood: High if the Software is exposed over a network. Low if kept strictly local.

How (Self): Replace pymupdf with pypdf (BSD-3-Clause) or pdfminer.six (MIT). Document the current dependency in the NOTICE. If you keep pymupdf, add a notice that network exposure triggers AGPL Section 13.

How (Nexus): /Law, /License.

3. SCRAPING AND CFAA EXPOSURE

Risk: Crawling websites may violate the Computer Fraud and Abuse Act (18 U.S.C. Section 1030) if the crawler exceeds authorized access. Under Van Buren v. United States (2021), using authorized access for an improper purpose is not a CFAA violation, but accessing areas of a site that are off-limits is. The line is fact-specific.

Trigger: Crawling a site that has explicitly prohibited crawling, or crawling behind a login wall.

Who could bring it: The site operator.

Exposure: Civil damages, criminal referral in egregious cases, injunction, attorney fees.

Likelihood: Low for public content, medium for sites with explicit anti-crawling terms.

How (Self): Respect robots.txt. Do not crawl behind authentication. Do not bypass rate limits. Keep records of crawled domains and dates. Add a robots.txt parser if not already present.

How (Nexus): /Law.

4. TERMS OF SERVICE BREACH

Risk: Crawling a site in violation of its terms of service is a breach of contract, not a CFAA violation (hiQ v. LinkedIn). But breach of contract can still lead to civil liability.

Trigger: Crawling a site whose terms prohibit automated access.

Who could bring it: The site operator.

Exposure: Contract damages, injunction, attorney fees. Usually low in monetary terms, but can be significant if the site claims lost revenue.

Likelihood: Medium for commercial sites with anti-scraping terms.

How (Self): Review terms of service before crawling major sites. Maintain a blocklist of sites that explicitly prohibit crawling. Document compliance efforts.

How (Nexus): /Law.

5. GDPR AND PRIVACY EXPOSURE

Risk: NEXUS crawls arbitrary web content, which may include personal data (names, emails, phone numbers, IP addresses). Processing personal data without a legal basis violates GDPR, UK GDPR, and equivalent laws.

Trigger: Crawling content containing personal data and storing it locally without a legal basis.

Who could bring it: Data subjects, supervisory authorities (ICO, CNIL, DPA), or the operator's own customers if NEXUS is used as a service.

Exposure: Fines up to 20 million EUR or 4 percent of global turnover (GDPR Art. 83). Data subject claims for damages. Reputational harm.

Likelihood: Medium for research use, high for commercial deployment.

How (Self): Enable PII redaction if crawling for research. Document the legal basis. Do not crawl special-category data. Maintain a retention policy. If operating in the EU, appoint a DPO if required.

How (Nexus): /Law, /License.

6. COPYRIGHT INFRINGEMENT IN CRAWLED CONTENT

Risk: Crawling and storing copyrighted content is generally lawful for personal use, but redistributing or using it in training corpora may infringe copyright.

Trigger: Publishing crawled content, training a model on it, or redistributing it.

Who could bring it: Rights holders (publishers, authors, photographers).

Exposure: Statutory damages up to 150,000 USD per work for willful infringement. Injunction. Attorney fees.

Likelihood: High if crawled content is used in a public dataset or a commercial model.

How (Self): Do not redistribute crawled content. Do not use it in a public dataset. If training a model, document provenance and comply with TDM exceptions. Consult counsel.

How (Nexus): /Law, /License.

7. DMCA SECTION 1201 ANTI-CIRCUMVENTION

Risk: Bypassing paywalls, DRM, or access controls may violate DMCA Section 1201, even if the underlying content is not infringed.

Trigger: Crawling a site with paywall bypass, CAPTCHA solving, or access-control circumvention.

Who could bring it: Rights holders, platform operators.

Exposure: Statutory damages up to 2,500 USD per violation (Section 1201). Injunction.

Likelihood: Low if NEXUS does not bypass controls. The Software does not include CAPTCHA solving by design.

How (Self): Do not add CAPTCHA solving. Do not add paywall bypass. Document that NEXUS does not circumvent access controls.

How (Nexus): /Law.

8. AI ACT COMPLIANCE

Risk: If NEXUS output is used to train a model, the operator becomes a provider or deployer under the EU AI Act. The Act imposes transparency, data governance, and conformity assessment obligations.

Trigger: Training a model on crawled data and deploying it in the EU.

Who could bring it: National market surveillance authorities, the EU AI Office.

Exposure: Fines up to 35 million EUR or 7 percent of global turnover for prohibited practices. Fines up to 15 million EUR for other violations.

Likelihood: Low for research use, high for commercial deployment.

How (Self): Publish a training content summary. Comply with TDM opt-out. Conduct adversarial testing if the model is systemic-risk. Classify the model's risk tier before deployment.

How (Nexus): /Law, /License.

9. EXPORT CONTROL AND SANCTIONS

Risk: NEXUS contains cryptographic code. Exporting it to sanctioned jurisdictions or to sanctioned persons may violate EAR, OFAC, or EU dual-use rules.

Trigger: Distributing NEXUS to a person or entity on a sanctions list, or operating it in a sanctioned jurisdiction.

Who could bring it: BIS, OFAC, EU national authorities.

Exposure: Civil penalties up to 300,000 USD per violation. Criminal penalties for willful violations. Loss of export privileges.

Likelihood: Low for public open-source distribution (EAR Section 734.7 and 740.13(e) cover publicly available encryption source code).

How (Self): Keep the source publicly available. Do not add access controls. File the EAR Section 740.13(e) notification if distributing commercially.

How (Nexus): /Law, /License.

10. TRADEMARK AND BRANDING

Risk: The "NEXUS" name may conflict with existing trademarks. There are numerous products named NEXUS.

Trigger: Using the name in commerce in a way that suggests endorsement or is confusingly similar to an existing mark.

Who could bring it: Existing trademark holders.

Exposure: Injunction, damages, forced rebrand.

Likelihood: Medium. The name "NEXUS" is widely used.

How (Self): Perform a trademark clearance search. Consider renaming if the project grows. Use "NEXUS Universal Crawler" as a descriptive identifier.

How (Nexus): /Law.

11. CUSTOM LICENSE ENFORCEABILITY AGAINST DOWNSTREAM CONSUMERS

Risk: A custom license that prohibits modification and redistribution may be challenged as overbroad or unenforceable in jurisdictions that recognize broad user rights (for example, in the EU under the Software Directive's exceptions for decompilation and interoperability).

Trigger: A user in the EU decompiles NEXUS for interoperability purposes and the author attempts to enforce the prohibition.

Who could bring it: The user, defending against enforcement.

Exposure: The prohibition may be unenforceable in that jurisdiction. The author may be liable for wrongful enforcement.

Likelihood: Low for research use. Medium if the project gains traction.

How (Self): Add a severability clause. Acknowledge that mandatory local law rights are not waived. Consult counsel if enforcing against EU users.

How (Nexus): /Law.

12. LIABILITY FOR CRAWLED CONTENT HARM

Risk: Crawled content may contain defamatory, harassing, or unlawful material. If the operator redistributes it, the operator may be liable.

Trigger: Redistributing crawled content that contains unlawful material.

Who could bring it: The subject of the content.

Exposure: Defamation damages, privacy claims, injunction.

Likelihood: Low if the operator does not redistribute. High if the operator publishes a dataset.

How (Self): Do not redistribute crawled content. If publishing a dataset, filter for unlawful material. Maintain a takedown process.

How (Nexus): /Law.

13. THIRD-PARTY SERVICE TERMS VIOLATIONS

Risk: NEXUS contacts external services (Stack Exchange, Wayback, Common Crawl, etc.) at runtime. Each service has its own terms of service. Using a service in violation of its terms exposes the operator to termination and, in some cases, civil liability.

Trigger: Exceeding rate limits, using a service for prohibited purposes, or ignoring robots.txt on the service's own domain.

Who could bring it: The service operator.

Exposure: Account termination, IP ban, civil damages.

Likelihood: Low for research use with rate limiting. Higher for bulk crawling.

How (Self): Respect each service's terms and rate limits. Document the services contacted. The NEXUS budget tracker already limits external API calls.

How (Nexus): /Law.

14. RESEARCH ETHICS AND IRB REVIEW

Risk: If NEXUS is used for research involving human subjects (even indirectly, by crawling data about individuals), IRB or ethics committee review may be required.

Trigger: Publishing research results based on crawled personal data without ethics review.

Who could bring it: The researcher's institution, journals, or funding bodies.

Exposure: Retraction, loss of funding, institutional sanctions.

Likelihood: Medium for academic research involving personal data.

How (Self): Consult the institution's IRB or ethics committee before crawling personal data. Document the research purpose.

How (Nexus): /Law.

WORST-CASE SCENARIOS

1. AGPL Contamination

You expose NEXUS as a hosted service. A downstream consumer discovers pymupdf. They demand the source under AGPL-3.0. You cannot comply because your OLSP prohibits redistribution and you have not offered source under AGPL. They file a claim. Artifex joins. The court orders source release and damages. Your OLSP is void for the combined work.

2. Copyright Class Action

You publish a dataset built from NEXUS output. A publisher discovers thousands of its articles in your dataset. They file a class action on behalf of all affected publishers. Statutory damages at 150,000 USD per work, times thousands of works, exceeds any realistic settlement capacity.

3. GDPR Enforcement

You crawl a site containing personal data of EU residents and store it without a legal basis. A data subject files a complaint. The DPA investigates, finds no legal basis and no retention policy. The fine is proportional to your revenue, but even a small fine includes enforcement costs, legal fees, and mandatory remediation.

PRIORITIZATION MATRIX

Critical: AGPL contamination via pymupdf if network-exposed. Copyright infringement if redistributing content. GDPR if processing personal data without a basis.

High: CFAA if crawling behind auth walls. DMCA Section 1201 if bypassing controls. AI Act if training prohibited systems. Custom license enforceability if challenged.

Medium: Terms of service breach. Trademark conflict. Third-party service terms.

Low: Export control. Research ethics. Defamation if not redistributing.

MITIGATION ROADMAP

Phase 1, before any public release or use:

1. Replace pymupdf with pypdf or pdfminer.six. This eliminates the AGPL contamination risk.
2. Add the full OLSP license text to the repository.
3. Add the NOTICE file with dependency attributions.
4. Add the PRIVACY_POLICY file.
5. Add the TERMS_OF_USE file.

Phase 2, within 30 days:

6. Register the copyright with the US Copyright Office.
7. Perform a trademark clearance search for "NEXUS."
8. Add the SECURITY file and disclosure policy.
9. Add the AI_DISCLOSURE file.
10. Document the legal basis for any personal data processing.

Phase 3, ongoing:

11. Monitor dependency licenses for changes.
12. Review terms of service before crawling new major sites.
13. Maintain a retention policy for crawled data.
14. Update the legal suite when the project changes.

BLIND SPOTS

1. The OLSP has not been reviewed by counsel. Custom licenses are enforceable but require careful drafting. A single ambiguous clause can render the restriction unenforceable.
2. The interaction between the OLSP and AGPL-3.0 is legally unsettled. The OLSP prohibits redistribution, which avoids distribution-triggered copyleft, but network exposure is not addressed by the OLSP. This is a gap.
3. Research use is not a legal category in most privacy laws. GDPR does not exempt research from the legal basis requirement. Academic research may benefit from derogations (Art. 89) but those require safeguards.
4. The copyright status of AI training data is unsettled in most jurisdictions. The US Copyright Office has taken the position that training on lawfully acquired data is fair use in some contexts, but this is not settled law.
5. The NEXUS codebase contacts over 25 external services. Each service has its own terms. The cumulative compliance burden is significant and is not addressed by any single document.

Standing Note

This is risk identification, not legal advice. Consult qualified counsel before acting on any finding.

=== END LAW ===
