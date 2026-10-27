# Changelog

## 3.0.5 - 2026-10-27 (GitHub publication)
First public repository. Code unchanged from the 3.0.5 Stable release (every `.py`, `.ps1`, `.txt` and `.json` file is byte-identical). Documentation reorganized: English `README.md`, full user guide in `docs/USER_GUIDE.md` and `docs/OpenAlex_Literature_Intelligence_v3.0.5_User_Guide.docx`, Vietnamese README and quick start moved to `docs/`, English `SECURITY.md`, `LICENSE` (MIT) and `CITATION.cff` added. The mirror-operator notes (`SERVER_MANIFEST_UPDATE_REQUIRED.md`, `manifest_patch_example.json`) are not part of the public repository. Archived on Zenodo: concept DOI 10.5281/zenodo.23680134, v3.0.5 DOI 10.5281/zenodo.23680135.

## 3.0.5 - 2026-10-25 (Stable)
Stable release; code identical to the independently reviewed 3.0.5 candidate (52/52 unit, 96/96 acceptance). Release packaging: `RELEASE_NOTES.md`, examples moved to `examples/`.

- Blocked title fallback when ISSN identifiers conflict: if the source has valid ISSN/ISSN-L and a title candidate lists ISSNs with no overlap, the candidate is rejected; if all are rejected the result is `UNMATCHED` with `latest_match_method`/`publication_match_method` `TITLE_MATCH_ISSN_CONFLICT` (historical: `ANY_EARLIER_SNAPSHOT_TITLE_MATCH_ISSN_CONFLICT`) and weaker title levels are not tried. Candidates without ISSN and sources without valid ISSN are unaffected. Same rule for latest, publication-year and historical snapshots and `inspect-source`.
- New audit columns `match_diagnostic` (`ISSN_CONFLICT`) and `issn_conflict_candidates` (enriched/main/excluded/source_audit); `summary.json` `match_diagnostic_counts`.
- Removed the hard-coded personal e-mail (`DEFAULT_EMAIL = ""`); `mailto` comes from `--email` or `config.json` `openalex.email`, else none is sent.
- Run metadata renamed: `openalex_api_key_configured`, `openalex_api_key_source`, `openalex_api_key_stored_in_output` (replace `api_key_configured`, `api_key_source`, `openalex_api_key_stored`).
- Prepared a server-side merge patch for the mirror's documented `matching_policy` (not part of the client; the remote manifest was not modified).
- Title normalisation treats `&` as `and` (OpenAlex `Computers & Security` vs SCImago `Computers and Security` never matched without an ISSN; found while inspecting the venues named in the review). SCImago uses `&` in only 5 titles of the 2025 snapshot and the change creates no new normalised-title collisions in the 2010/2015/2020/2025 snapshots.
- Added regression tests (52 unit tests: correct title + wrong ISSN, title without ISSN, ISSN wins over title, historical title with correct/wrong ISSN, SCImago candidate without ISSN, ambiguous title with/without ISSN, invalid ISSN, `&` vs `and`, inspect-source, no personal e-mail in source).

## 3.0.4 - 2026-10-25
Independent audit release.

Configuration (new standard layout):
- Private `config.json` next to `literature_pipeline.py` (or `--config <path>`) holds the OpenAlex key and optional defaults: `openalex.api_key`, `openalex.email`, `scimago.manifest_url`, `scimago.cache_dir`, `run.from_year`, `run.to_year`, `run.require_abstract`, `run.max_per_query`. Precedence: CLI argument > config.json > code default (the legacy `OPENALEX_API_KEY` environment variable is still read after config.json, deprecated).
- Strict validation (unknown sections/keys, wrong types, invalid JSON -> `ERROR (config)`, exit 2); messages never echo values or unknown key names from the file. Relative `cache_dir` is resolved against the config file's folder.
- `run` without any key stops before any SCImago/OpenAlex request with instructions (exit 2); the other commands need no key.
- `run_metadata.json` records `api_key_configured`, `api_key_source` (e.g. `config.json`), `config_file` and `settings_sources`; never the key.
- `config.example.json` rewritten to the new schema (empty key); `.gitignore` added (config.json, caches, environments). The release packaging script excludes every `config.json`, refuses to package if any other file contains its key, and writes portable `/` ZIP paths. Reference-corpus counts are unchanged (29/1/70 papers, 21/1/51 unique sources, main 25 journal-only / 29 all-source-types); the fixes change semantics only where v3.0.3 contradicted the stated policy.
- Security: OpenAlex error paths no longer print the API key. HTTP 4xx messages included the full request URL (with `api_key=`), and network errors printed/raised the urllib3 message containing the URL. Messages are now redacted and exceptions are re-raised without the chained original.
- `HISTORICAL_ONLY` now follows the manifest definition (matched in any snapshot earlier than latest, absent from latest). v3.0.3 only checked the publication-year snapshot, so papers from 2026, from years where the source is absent, or without a year were `UNMATCHED` even though `inspect-source` said `HISTORICAL_ONLY`. New fields: `historical_match_method`, `historical_match_candidates`, `historical_snapshot_years`, `scimago_type_historical`.
- A Sourceid found through history that is still present in the latest snapshot is `ACTIVE_LATEST` (`SOURCEID_VIA_*` methods), never `HISTORICAL_ONLY`.
- Future publication years: `ranking_basis = LATEST_AVAILABLE` only for `ACTIVE_LATEST` rows; other rows are `UNAVAILABLE` (v3.0.3 labelled unmatched 2026 papers `LATEST_AVAILABLE`). Rows without a valid year now get `UNAVAILABLE` explicitly.
- `--include-historical-only` now admits exactly ACTIVE_LATEST + HISTORICAL_ONLY to the main corpus, as its name and README section 9 describe. Previously it removed the status filter, so UNMATCHED and AMBIGUOUS rows also entered main (reference corpus: 52 papers instead of 26). The old behaviour is available explicitly as `--any-source-status`.
- SCImago `-` quartile placeholder is stored as blank (unavailable); summary distinguishes `NOT_ASSIGNED` from `UNAVAILABLE`; quartile filters report `QUARTILE_UNAVAILABLE`.
- `--relevant-category` uses exact (case/punctuation-insensitive) category matching instead of substring matching.
- New lowest-priority match rule `TITLE_STATUS_NORMALIZED` (ignores SCImago "(discontinued)"/"(ceased)" title labels), shared by enrichment and `inspect-source`.
- `scimago_sourceid_at_publication` and `publication_sourceid_differs` record which Sourceid supplied publication-year metrics.
- `source_audit.csv` aggregates all papers of a source (`paper_status_counts`, `MIXED`; descriptive columns such as `source_class` are the sorted distinct values joined with ` | `) instead of copying the first row; output no longer depends on input order.
- Enrichment first removes every enrichment/screening column from the input rows, so re-enriching a previous `_enriched.csv`/`_main.csv` gives exactly the same result as enriching the raw file. v3.0.3 kept stale `*_latest` metrics, Sourceids and APC values on rows that were no longer ACTIVE_LATEST.
- After retries, OpenAlex network failures raise `requests.RequestException` (as in v3.0.3) with a redacted message.
- OpenAlex dedup treats DOI and OpenAlex ID as aliases of one work, so a work first stored without a DOI is not duplicated when it later returns with one.
- `main.csv`/`excluded.csv` use the enriched column order, so an empty partition still has a header.
- `enrich` writes `<output>_run_metadata.json` (input SHA-256, policy, manifest, environment) and adds `scimago_repository` to its summary; `run_metadata.json` gains `environment`.
- Repository: HTTP 404/other 4xx fail fast with a clear "remote file not found" message (previously retried 5 times); cache fallback prints a warning; manifest file names that could escape the cache directory are rejected; repository errors are printed as one `ERROR` line with exit code 2.
- `inspect-source` prints status semantics notes and states when the source is absent from the latest snapshot; the historical lookup reuses records found during the scan (only unseen annual files are re-read).
- Performance: ASCII fast path in `title_normalized_key` (identical output on all 65,379 SCImago titles); the latest snapshot is no longer parsed twice during enrichment.
- Version string now comes from `litintel.__version__` everywhere (VERSION file, CLI, User-Agent, run metadata were 3.0.2/3.0.3 mixed). Added `--version`.
- Added offline regression tests (`tests/test_regressions.py`, 41 tests including 6 config tests) and `tools/check_reference_invariants.py`.

## 3.0.3 - 2026-10-25
- `inspect-source` searches earlier SCImago snapshots when the source is absent from the latest snapshot, so historical-only sources such as Mobile Information Systems are reported `HISTORICAL_ONLY` with their trajectory instead of `UNMATCHED`.
- (This entry was missing from the bundled 3.0.3 changelog; VERSION and run metadata still said 3.0.2.)

## 3.0.2 - 2026-10-25
- Main corpus is now **journal-only by default** in addition to requiring presence in the latest SCImago snapshot.
- Added `--all-source-types` to explicitly disable the default journal-only filter.
- `--source-type` now overrides the default when supplied and can be repeated for journal/conference combinations.
- Added `source_class`, `openalex_source_type`, and `scimago_source_type` to source audit output.
- Summary now separates paper counts from unique-source counts and includes source-class breakdowns.
- Replaced ambiguous OpenAlex `done=false` reporting with `query_exhausted`, `stopped_by_limit`, `has_more_results`, `resume_available`, and `run_completed_successfully`.
- Existing v3.0.x checkpoints are migrated automatically to checkpoint schema version 2.
- Improved console messages when a query stops because `--max-per-query` was reached.

## 3.0.1
- Clarified SCImago sync messages: `missing` was replaced by `Local cache not found`.
- Added explicit success messages after each download and SHA-256 verification.
- Added a final success statement confirming all required files are present and verified.

## 3.0.0 - 2026-10-25

- OpenAlex multi-query downloader with resume/deduplication.
- Remote SCImago repository via manifest.
- SHA-256 verification and local cache/offline fallback.
- Historical SJR/quartile lookup for 2010-2025.
- Latest snapshot status and agreed main-corpus policy.
- Category-specific quartile support.
- Journal Value / estimated APC 2025 enrichment.
- Source matching audit and explicit ACTIVE_LATEST / HISTORICAL_ONLY / UNMATCHED / AMBIGUOUS statuses.
- Existing CSV/JSONL enrichment mode.
- Source history inspection command.
