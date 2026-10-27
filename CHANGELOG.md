# Changelog

## Unreleased
Clearer handling of papers published after the last SCImago year under a publication-basis quartile filter. Which papers enter the main corpus does not change.

- With `--quartile` and `--quartile-basis publication` (the default basis), a paper published after the last SCImago year whose source is in the latest snapshot (`ranking_basis = LATEST_AVAILABLE`) now gets the exclusion reasons `QUARTILE_UNAVAILABLE; QUARTILE_PUBLICATION_YEAR_NOT_AVAILABLE` instead of `QUARTILE_UNAVAILABLE` alone. `QUARTILE_UNAVAILABLE` is kept for compatibility. The latest quartile is still never copied into the publication-year columns, and `LATEST_AVAILABLE` keeps its meaning.
- `run` and `enrich` print a warning with the number of such papers and the last SCImago year, suggesting `--quartile-basis latest` for anyone who intends to screen them by the latest snapshot. No warning appears without `--quartile`, with `--quartile-basis latest`, or when no paper is affected.
- `summary.json` always contains `quartile_filter_diagnostics`: the quartiles filtered on, basis, mode, `scimago_latest_year` and `future_year_papers_without_publication_quartile` (0 when no paper is affected). `run_metadata.json` already records the SCImago years and the quartile policy.
- On 100 real records, compared with 3.2.0: the same main corpus byte for byte, the new reason on the 12 affected rows of `_excluded.csv`, and identical files with `--quartile-basis latest`.
- 6 new offline tests: the precise reason (best and relevant-category modes), the latest basis, a paper inside the SCImago years, counts over mixed rows, the CLI warning for `enrich` and for `run`. Each was checked against deliberate faults. 81 tests in total.
- Documentation: README, `docs/README_vi.md` and the user guide now describe how the publication and latest bases treat papers newer than the SCImago data.

## 3.2.0 - 2026-10-27
One addition to `run`: the search field. Without the new option, `run` sends the same OpenAlex requests as 3.1.1, and `enrich` and `fetch-oa` are unchanged.

- `--search-field search|title_and_abstract` (`run`), with the default from `config.json` `run.search_field`, else `search`. `search` sends the query to the OpenAlex `search` parameter, as before (title, abstract and, where OpenAlex has it, full text). `title_and_abstract` sends it to the `title_and_abstract.search` filter instead (title and abstract only).
- A `title_and_abstract` query containing `,` or `|` (which separate and combine OpenAlex filter values) is refused before any SCImago or OpenAlex request, with exit code 2. An unknown `run.search_field` in `config.json` is refused without echoing the value.
- The search field is recorded in `run_metadata.json`, in `summary.json` (`openalex.search_field`) and, when it is not the default, in the checkpoint signature: resuming with another field stops with `Checkpoint parameters changed`, while checkpoints written by earlier versions resume unchanged with the default.
- The console states the search field at the start of `run`.
- Live check on 27 October 2026: one query matched 3,124 works with `search`, as with the 3.1.0 `run` earlier that day, and 228 with `title_and_abstract`, as with a separate measurement script; all 228 works contain the query terms in their title or abstract.
- 4 new offline tests: the request with each field (the default request keeps the parameters and order of 3.1.1), the checkpoint rule, refused queries, and precedence plus an end-to-end `run` through the CLI. Each test was checked against deliberate faults. 75 tests in total.
- `TEST_REPORT.md` records the real-data check of the 3.1.1 `fetch-oa` fix: on the 100 papers where 3.1.0 first had 17 links paused, one 3.1.1 run paused none and gave the same 38 PDFs as three 3.1.0 runs.
- User guide: Appendix I and new rows in the configuration and option tables.

## 3.1.1 - 2026-10-27
Bug fix in `fetch-oa`; nothing else changes.

- A DOI link that redirected to a publisher's bot check paused the resolver (doi.org) for the rest of the run, so every later DOI link was skipped as `HOST_PAUSED`, including links to other publishers. Now the publisher and any non-resolver host that redirected to it are blocked as before, and a resolver that only redirected is left alone; a resolver that answers with a bot check itself is still paused. Found in the first real use on a thesis corpus, where the first runs skipped 21 DOI links; rerunning `fetch-oa` was the workaround.
- New test with three local servers (resolver, blocked publisher, open publisher); the redirect-chain test now expects the resolver to stay usable. 71 tests in total.

## 3.1.0 - 2026-10-27
Two additions: quality signals with user-defined venue tiers, and the `fetch-oa` command. Without the new options, `enrich` writes byte-identical CSV/JSONL files to 3.0.5 for the same input; `summary.json` gains three counts.

Quality signals and venue tiers:
- `run` keeps five more OpenAlex fields per work: `is_retracted`, `fwci`, `citation_normalized_percentile`, `citation_top_1_percent` and `citation_top_10_percent`. They are taken from the responses already received, so no extra request is made. When duplicates are merged, a retraction reported by either copy is kept and missing metrics are filled.
- `--exclude-retracted` (`run`, `enrich`) excludes retracted works with reason `RETRACTED`. `summary.json` reports `papers_retracted`, `papers_without_retraction_flag` (rows retrieved before 3.1.0) and `papers_without_fwci`, and the CLI says when records lack the flag.
- `--venue-tiers <file>` (`run`, `enrich`) labels each paper with the tier of its venue from a list the user maintains (TSV, or CSV by extension; columns `tier`, `venue`, `openalex_source_id`, `issn`, `title_exact`, `title_contains`). Matching order: OpenAlex source ID, ISSN, whole source name, then the longest whole-word phrase in the source name. New columns `venue_tier` (tier, `UNLISTED` or `AMBIGUOUS`), `venue_tier_venue` and `venue_tier_match` in the enriched, main, excluded and source-audit files; tier counts in `summary.json`; the list's path, SHA-256 and size in `run_metadata.json`. The labels do not filter.
- The list is checked before any network access: unknown or repeated columns, empty tiers, the reserved names `UNLISTED`/`AMBIGUOUS`, invalid ISSNs or source IDs, an ID, ISSN or phrase given for two venues, and stray cells stop the command with the line number (exit 2).
- Re-enriching an output without `--venue-tiers` drops old tier columns instead of keeping stale labels.
- `examples/venue_tiers_example.tsv` shows the format (ISSNs from the SCImago 2025 snapshot).
- 7 new offline tests: field extraction, merge rules, the retraction filter, matching order, longest phrase, whole words, `&`, ambiguity, every list error, CSV lists, end-to-end `enrich` with metadata and re-enrichment, and a bad list stopping `run` before any request.

Open-access full text (`fetch-oa`):
- Input: any `run`/`enrich` output (`*_main.csv`, `*_enriched.csv/.jsonl`, `*_raw.csv`). Tries `best_oa_pdf_url`, then `oa_url`; closed-access papers are listed without any request. No API key and no OpenAlex request.
- Polite access: sequential requests, `--delay` seconds between two requests to the same host (default 2, minimum 1; a longer robots.txt Crawl-delay wins, up to 60 s), fixed User-Agent `OpenAlexLiteratureIntelligence/<version>` with the repository URL. robots.txt follows RFC 9309 (redirects followed, longest match, `*` and `$`); an unreadable robots.txt skips the host for the run. Only complete PDFs (`%PDF-` ... `%%EOF`, Content-Length checked) up to `--max-mb` (default 100) are kept.
- Bot checks stop all further requests to a host: a challenge or CAPTCHA page (Cloudflare, Akamai, Imperva, PerimeterX, DataDome, DDoS-Guard, AWS WAF), HTTP 403, or `tdm-reservation: 1` (also on a redirect). The host is written at once to `blocked_hosts.json` with the evidence and is skipped in later runs until removed from that file; hosts that redirected to the check are blocked too. Titles of ordinary pages (for example a paper about CAPTCHAs) and scripts that challenge services inject into ordinary pages do not count. Nothing tries to get past a bot check.
- Run-only pauses instead of permanent blocks: HTTP 429, 5xx with Retry-After, three network failures in a row, and DOI/handle resolvers (doi.org and similar), so one rate limit cannot cut a repository or every DOI link for good.
- Outputs: `pdf/`, `downloaded.csv`, `manual_download.csv/.html/.ris` (reason, DOI, links, file name to use), `pdf_manual/` (hand-downloaded PDFs are registered on the next run), `fetch_state.json`, `fetch_log.csv`, `fetch_summary.json`.
- Reruns skip downloaded papers and retry only temporary failures, decided per link; `--retry-failed` also retries permanent failures. Progress and blocks are saved after every paper and on Ctrl+C; a malformed response is recorded and the run continues. Rows marked closed access are never requested, even with a link. `--limit N` runs a pilot.
- An independent review before release found nine defects in the first draft (state lost on a crash, robots.txt redirects and wildcards, redirect-chain blocking, false positives on paper titles, per-link retries, 503 handling, closed-access rows with links, unsafe links in the HTML list, truncated PDFs); all are fixed and covered by tests.
- A live pilot on 20 papers found that redirects with a lower-case `location` header (doi.org) were not followed; fixed. `fetch_log.csv` now also lists every robots.txt request.
- 11 new offline tests with local servers: challenge pages, rate limits, robots.txt redirects, wildcards and outages, redirect chains, `tdm-reservation`, resolvers, interruption, cut-off and truncated bodies, busy servers, HTML/RIS escaping, lower-case header names, pacing and the User-Agent.
- 70 tests in total (52 from 3.0.5, 11 for `fetch-oa`, 7 for quality signals and venue tiers).
- User guide: Appendices G and H and new rows in the command and option tables; the Word file is now `docs/OpenAlex_Literature_Intelligence_User_Guide.docx` (version-neutral name). `*_fulltext/` added to `.gitignore`.

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
