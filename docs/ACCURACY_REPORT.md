> Historical report from the preview phase. The current official COI implementation and verification are described in [COI_COMPATIBILITY_REPORT.md](COI_COMPATIBILITY_REPORT.md) and [REFERENCE_COMPARISON.md](REFERENCE_COMPARISON.md). Earlier missing-material and compatibility statements below are superseded.

# Accuracy report — frozen local holdout v1

**Engine frozen before the first run; no recognition tuning after results.**
Manifest, input hashes and engine-file hashes: `evaluation/holdout-v1/manifest.json`.
This is a newly authored synthetic set, separate from `demo_samples`, not an
externally blinded corpus or official COI benchmark. It cannot establish quality
on arbitrary Polish government forms.

## Actual results

`python scripts/evaluate_accuracy.py` executed the real isolated worker on 12
files: ordinary PDFs, low-contrast/skewed scanned PDF, DOCX tables and multiline
inputs, XLSX, ODS, PNG, JPEG, repeated/multipage forms, multipage scan, labels
above blank lines, fields without colons, choice groups, and a no-field negative
control. No expected outputs are read by the conversion engine.

| Measure | Actual value | Denominator / meaning |
|---|---:|---|
| Field precision | 100.00% | 64 matched / 64 predicted |
| Field recall | 95.52% | 64 matched / 67 annotated |
| Field F1 | 97.71% | harmonic mean |
| Field type accuracy | 90.63% | 58 / 64 **matched** fields |
| Section grouping accuracy | 90.63% | 58 / 64 **matched** fields |
| OCR token coverage | 100.00% | annotated label/section tokens on OCR cases only |
| Internal JSON validity | 100.00% | 12 / 12 FormForge models; **not COI schema validity** |
| Median processing | 0.1494 s | worker startup and conversion included |
| p95 processing | 2.5317 s | nearest-rank p95 over 12 sequential conversions |
| Observed maximum child RSS | 143.27 MB | high-water mark, not concurrent server total |

Machine-readable case records, misses, extra fields, type errors, timings,
matching policy and hashes are in `docs/accuracy-results.json`.

## Matching protocol and limits

Predictions and annotations are matched one-to-one, on the same page, by greedy
descending normalized label similarity with a threshold fixed at **0.82 before
evaluation**. Type and section correctness are evaluated only for matched fields;
false negatives are reported separately. Section numbering prefixes are normalized.
Bounding-box accuracy, requiredness, option-list correctness, legal/process
semantics and official-schema compatibility are not measured by these percentages.

OCR coverage is partial source-token recall, not full-page transcription, CER,
word error rate, or a guarantee of correct layout. It can be 100% while fields are
missed or assigned to the wrong sections. PNG and JPEG variants share the same
authored form; likewise a multipage PDF and its scan share content. Therefore
12 files are not 12 unrelated administrative processes. The optional local
classifier has no claimed holdout accuracy improvement; these are deterministic
engine results.

## Failures retained in the final result

- `ankieta.png` and `ankieta.jpg`: SMS checkbox missed in each; three matched
  fields per file assigned to incorrect sections.
- `ewidencja_skan.pdf`: “Nazwa działalności” field missed despite recognized
  text. Label/line association is a remaining weakness.
- `rodzina_skan.pdf`: six Imię/Nazwisko fields incorrectly typed as textarea
  because multiple raster borders were associated with the same label.
- No false positives appeared in this small final corpus. This does not justify
  claiming a zero false-positive rate outside it. The separate compressed demo
  scan now produces 11 candidates for a source with 9 intended fields; candidate
  count alone is not an accuracy improvement.

These errors were **not fixed against the holdout**. Future changes need a new
independent external test set; retain v1 as a transparent historical result.
The evaluator refuses changed engine hashes or modified input files. Dataset
creation refuses to overwrite the frozen manifest.

## Reproduction

Install development dependencies and local Tesseract `pol+eng`, then:

```bash
python scripts/evaluate_accuracy.py
```

Do not rerun the authoring script to replace inputs. Tests and development
fixtures remain separate from this final holdout. Linux/container performance,
concurrency, handwriting, rotations beyond the small deskew range and natural
scanner/photo artifacts still need independent evaluation.
