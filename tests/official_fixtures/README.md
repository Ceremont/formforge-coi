# Official fixtures: intentionally empty

No official COI input/expected-JSON pairs were supplied. Do not put synthetic
fixtures here and label them official. Unit tests for ConfiguredAdapter use a
clearly marked toy schema and do not establish COI compatibility.

When actual files arrive, add a manifest with `cases` entries containing `id`,
`input`, `expected` and `mime`; paths are relative to the manifest. Use the real
schema and mapping, then run `scripts/verify_official.py`. The output must match
expected JSON exactly, including absence of extra keys. Configure local schema
references only; remote `$ref` retrieval is forbidden.
