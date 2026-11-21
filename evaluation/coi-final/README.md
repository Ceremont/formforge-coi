# Final evaluation protocol

Baseline: `aaa8148`, 0.3.0, 178 tests, 62/69 accepted. `baseline.json` protects
all 323 historical files from coi-v1 and engine-v03 by SHA256. Originals remain
unchanged; current evaluation never rewrites those directories.

- `known-results.json`: all 69 organizer sources; 01/05 paired development
  references and the other seven sets previously evaluated development inputs.
- `development-results.json`: the three external files from 0.3, now development.
- `promoted-development-documents/`: first new R1 set. Blank-table failures were
  used to improve generic extraction, so this set is explicitly not independent.
- `secondary-audit-documents/`: R2 set, preserved separately before a regression
  on the already-promoted parking source led to a numbered-caption correction.
  Conservatively not called the final independent holdout.
- `unknown-documents/`: final R3 sources acquired, inspected and annotated after
  the R3 recognition freeze. One annotator; three forms/two publishers. No further
  extraction/layout/field/section tuning used their outcomes. Full workflow truth,
  conditional coverage and population accuracy are not established.
- `engine-freeze.json`: R3 hashes of recognition/model/settings/mapping/validation
  code and bundled data. API main.py and later UI/deployment work are separate.
- `mapping-hotfix.json`: a narrowly scoped post-freeze exporter crash guard,
  discovered on known 08 JPEG/JPG. Unsupported boolean-to-empty-option binding is
  reported for review instead of discarding the whole conversion. Original freeze
  unchanged; before/after hashes and a regression test are recorded. R3 holdout raw
  predictions and COI exports are asserted unchanged by this guard.
- `trials/`: full prior freezes/results and annotation locks. Exploratory results
  must not be presented as final independent results or silently overwritten.
- `baseline-v03/`: original 0.3 code exported from Git and run on identical final
  unseen inputs. Current extra OLE library is unused by that old code.
- `field-metrics.json`: fixed-pattern, accent-folded, one-to-one source label/type
  inventories. Only explicitly scoped ground truth is scored. PDF page restriction
  is used where preregistered; no invented full-corpus precision/recall/F1.

Strict label matching also measures readability. It may miss a recovered region
with a damaged label. Type ties favor a correct type in duplicate-label groups,
so named-person/row alignment is not established. Section accuracy means source
heading recall at similarity >=0.85, with separate section F1 for extra headings.
Raw source-field scores are distinct from policy-expanded reference workflows.

Originals acquired for evaluation are excluded from Git/clean release until
redistribution rights are confirmed. Manifests preserve URLs/hashes; place original
files there separately to reproduce conversion. Runtime does not read corpora,
reference configurations, hashes or prepared outputs. All processing is real.

CLI: `python scripts/evaluate_final.py known`, `development`, `promoted`,
`secondary`, `unknown`; then `python scripts/score_final.py`. Recognition changes
require a new experiment rather than overwriting the active freeze.
