# Test report - OpenAlex Literature Intelligence v3.0.5 Stable

Release date: 2026-10-25. Code is byte-identical to the independently reviewed 3.0.5 candidate. This release changed packaging and documentation only.

## Automated test suite (shipped in `tests/`)
Command: `python -m unittest discover -s tests -v`, run in a brand-new virtual environment on an exact copy of this release tree.

| Item | Result |
|---|---|
| Tool version | 3.0.5 (`python literature_pipeline.py --version`) |
| Python | 3.11.9 |
| OS | Windows 11 Pro, build 26100 (Python's `platform` reports `Windows-10-10.0.26100-SP0`) |
| Dependencies | requests 2.34.2, urllib3 2.8.0, idna 3.20, charset-normalizer 3.5.2, certifi 2026.10.23 |
| Total tests | 52 |
| Passed | 52 |
| Failed | 0 |
| Skipped | 0 |
| Duration | 10.9 s |

The same 52 tests also pass on Python 3.14.4 (candidate review). They need no network and no API key: they use a synthetic SCImago repository and local 127.0.0.1 servers with fake keys.

Test groups:
- **Matching:** ISSN conflict, title fallback, ISSN priority, `&`/`and`, ambiguity, invalid ISSN.
- **Historical sources:** discontinued titles, any earlier snapshot, Sourceid still in latest.
- **Configuration:** with and without `config.json`, precedence, keyless `run`, invalid configs.
- **Security:** API-key redaction, no personal e-mail in source.
- **Repository checksums:** cold, warm, corrupt, offline, tampered, 404, unsafe names.
- **Corpus policy:** journal-only, all source types, historical-only, order-independent audit, stable schema.
- **Ranking:** exact-year metrics, future years, quartile placeholder.
- **Resume/checkpoint:** stop-by-limit, resume, legacy checkpoint.
- **Dedup:** DOI/OpenAlex-ID aliases.

## Reference-corpus regression (100 OpenAlex records, real verified SCImago 2010-2025 mirror)
Run with this release's code (not shipped: needs the reference corpus).

| Check | Result |
|---|---|
| journal-only main / excluded | 25 / 75 |
| `--all-source-types` main / excluded | 29 / 71 |
| papers ACTIVE_LATEST / HISTORICAL_ONLY / UNMATCHED | 29 / 1 / 70 |
| unique sources ACTIVE_LATEST / HISTORICAL_ONLY / UNMATCHED | 21 / 1 / 51 |
| independent invariant checker (`tools/check_reference_invariants.py`) | 20/20 PASS (default), 20/20 PASS (all source types) |
| `inspect-source --title "IEEE Access" --issn 9999-9999` | UNMATCHED, `TITLE_MATCH_ISSN_CONFLICT` |

The full acceptance suite of the 3.0.5 candidate (96/96 PASS) applies unchanged, because the code is identical. A fresh install from the release ZIP into an empty folder with Windows PowerShell 5.1 passed all 16 steps, including `sync-scimago` from an empty cache (17/17 files), `validate-repo`, `inspect-source`, a live 20-record OpenAlex query and the unit tests.
