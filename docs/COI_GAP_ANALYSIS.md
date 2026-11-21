> Historical report from the preview phase. The current official COI implementation and verification are described in [COI_COMPATIBILITY_REPORT.md](COI_COMPATIBILITY_REPORT.md) and [REFERENCE_COMPARISON.md](REFERENCE_COMPARISON.md). Earlier missing-material and compatibility statements below are superseded.

# COI requirements audit — 21 November 2026

Scope: existing FormForge repository, both supplied COI PDFs (task §3–7 and
regulations §2–4), current readers, API, UI, tests and dependency manifests.
No working module is removed. This document distinguishes baseline from the
upgrade; final verification is in COMPETITION_READINESS.md.

| Requirement | Baseline evidence | Gap / planned action |
|---|---|---|
| Python 3.14 / REST | 3.14.5, five endpoints, Swagger | retain |
| PDF/DOCX/XLSX/ODS/JPEG/PNG | 110 prior tests, actual readers | geometry and OCR improvements |
| DOC | explicit HTTP 415 | no verified permissive converter; retain honest rejection |
| Official JSON / design rules | only internal preview | official input material unavailable; adapter infrastructure only |
| Unknown documents | random-label DOCX regression | independent frozen evaluation with precision/recall/type/grouping/OCR metrics |
| Document understanding | source text/rectangles, blank-marker rules | column/table/label-space association, repeated groups, block roles |
| OCR | single Tesseract pass | bounded preprocessing candidates, deskew, objective quality selection |
| Review UI | label/type/required/options editing | add/delete/reorder, validation/sections/dictionaries/groups and source navigation |
| Dictionaries / initial data | per-field choices from document | registry/matcher, explicit initial data, proposals without official identities |
| Dependencies | simple field visibility | section visibility and conditional requiredness, combined cycle checks |
| Local AI | absent | optional small locally trained classifier; deterministic fallback |
| Temporary storage / JWT / limits | isolated worker, request temp, test coverage | preserve; regression checks after changes |
| Docker non-root / explicit image | Dockerfile/Compose config pass | daemon/build/run must be rechecked, not assumed |
| Permissive dependencies / offline | pinned Python closure, native build recipe | review changes; no external runtime API or model download |
| Competition deliverables | code, docs, sample JSON and screenshots | Polish 3-minute script; actual public video/deck still separate deliverables |

Source inventory: only `COI - Pełna treść zadania konkursowego.pdf` and
`COI - Regulamin zadania konkursowego.pdf`. All other examples are self-authored
synthetic files. None are official configuration references. The task points to
the challenge Discord materials channel; its attachments are not present here.

Priorities: P0 official-material blocker and mapping infrastructure; robust
geometry/OCR/types; frozen unknown-document evaluation; P1 review and provenance,
dictionaries/conditions; optional CPU classifier; final local/browser/security
verification. No claim of contest readiness follows from a green synthetic test suite.

Baseline rerun confirmed **110 passed** before the engine upgrade. No additional
official fixture was found. The Docker client remains installed but its daemon
socket is absent. Final delivery and exact remaining gaps are recorded separately
in COMPETITION_READINESS.md; the audit table above preserves the starting point.
