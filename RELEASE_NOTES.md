# FormForge COI 1.0.0

Local HackNation Competition Edition on `feature/competition-final`, tag `v1.0.0`.
No merge to main, push or visibility change. This extends the existing project.

196 tests pass in the checkout with organizer sources. Real Docker Compose,
browser workflows and network-none OCR/DOC/local-model integration passed.
68/69 organizer sources generate locally valid COI. New R3 raw-field micro F1
58.95% (baseline52.63%), only three documents/single annotator; review remains essential.

Requires Docker/Compose or Python3.14 and installed Tesseract pol+eng. First build
needs Internet. Core base digest and Python dependencies pinned. Runtime is local.
See README and QUICK_START_PL for exact commands, API and authentication.

Clean ZIP omits raw organizer/external source documents, historical raw traces,
venv/caches/secrets. Summary evidence and dynamically generated output JSON remain.
Source-dependent tests explicitly skip when the separate reference pack is absent.
All historical experiments remain in Git. Runtime schema retains organizer rights;
verify permission before wider redistribution. MIT code license is unchanged.

Open: actual COI importer, incomplete fields/conditions/sections, restricted DOC,
full dictionary/registry values, native/OS license audit and rights-transfer checks.
Public film<=3min and jury repository access are not supplied automatically.
This release is reviewable software, not proof of full competition compliance.
