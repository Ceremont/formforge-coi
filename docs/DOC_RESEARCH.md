# Offline DOC conversion review

DOC remains **HTTP 415**. This is an implementation/verification gap, not a
claim that permissively licensed DOC conversion is impossible.

| Candidate | Licensing / feasibility | Decision |
|---|---|---|
| PyMuPDF / Office | AGPL or paid commercial | excluded by requested policy |
| LibreOffice | MPL/LGPL | excluded under strict permissive-only application policy |
| Antiword / wvWare | GPL family | excluded |
| Apache OpenOffice current releases | Apache-2.0 | plausible candidate; no installed, audited converter/binary or real DOC regression corpus here |
| Apache POI HWPF | Apache project; reads Word 97–2003 and extracts older formats; upstream calls HWPF early-stage | plausible JVM-based reader; requires separately audited runtime/dependencies and sandbox, not yet verified |
| macOS textutil | proprietary system component | unsuitable for reproducible open-source Linux deployment |

Primary sources: [OpenOffice licensing](https://www.openoffice.org/about/),
[Apache distribution policy](https://www.openoffice.org/distribution/oem/),
[POI components and HWPF limitations](https://poi.apache.org/components/index.html),
[LibreOffice licenses](https://www.libreoffice.org/licenses/).

Before enabling DOC: test actual binary samples and versions, reject encrypted
or embedded macro content, disable macro execution and external links, isolate
the process/network/filesystem, apply parent timeout/process-group kill and memory
limits, preserve provenance through conversion, verify temporary cleanup and
check native/transitive notices in the actual image. None of these steps can be
replaced by accepting `.doc` in an extension list. Convert externally to DOCX/PDF
for current use; the product does not call external conversion APIs.
