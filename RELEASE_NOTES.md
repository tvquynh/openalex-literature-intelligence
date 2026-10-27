# Release notes - OpenAlex Literature Intelligence

- **Version:** 3.0.5
- **Status:** Stable
- **Release date:** 2026-10-25

OpenAlex Literature Intelligence finds literature in OpenAlex and enriches each venue with historical and latest SCImago data (SJR, quartiles, categories, estimated APC). It then screens a main corpus and keeps a full audit trail. See `README.md` for usage and `CHANGELOG.md` for every change.

## Major fixes and improvements (3.0.3 -> 3.0.5)
- **ISSN conflict protection:**
  - a title match is never accepted when the source's ISSN contradicts the SCImago candidate's ISSN; the result is `UNMATCHED`, `TITLE_MATCH_ISSN_CONFLICT`, with the candidate listed for review;
  - the ISSN always wins over the title;
  - `&` in a title now matches `and`.
- **Historical source matching:**
  - `HISTORICAL_ONLY` covers every earlier SCImago snapshot, including 2026 papers and years in which a source is missing;
  - SCImago "(discontinued)" title labels are understood;
  - a source still present in the latest snapshot is never called historical-only.
- **Journal-only default screening:**
  - the main corpus defaults to journal + `ACTIVE_LATEST`;
  - `--include-historical-only` admits only `HISTORICAL_ONLY` (no unmatched or ambiguous rows);
  - `--all-source-types` and `--source-type` override the journal-only default.
- **config.json support:**
  - a private `config.json` holds the OpenAlex key, e-mail and defaults; precedence is CLI > config.json > built-in default;
  - `config.example.json` is the public template;
  - `run` stops with a clear message when no key is configured;
  - no personal e-mail is built into the code.
- **API key redaction:**
  - the key never appears in error messages or tracebacks;
  - run metadata records only `openalex_api_key_configured` and `openalex_api_key_source`.
- **Improved audit reporting:**
  - per-source audit aggregated over all papers (`MIXED`, `paper_status_counts`);
  - `match_diagnostic` / `issn_conflict_candidates`;
  - quartile `-` reported as not assigned;
  - exact relevant-category matching;
  - `run_metadata.json` for `enrich` as well;
  - re-enriching an old output gives the same result as enriching the raw file.
- **Improved cache/checksum verification:**
  - every SCImago file is SHA-256 verified; corrupted files are re-downloaded online and refused offline;
  - a missing remote file fails fast with a clear message;
  - unsafe file names in the manifest are rejected.

## Upgrade notes
- **Create `config.json`:** `Copy-Item config.example.json config.json`, then set `"api_key"`. The `OPENALEX_API_KEY` environment variable still works as a fallback but is deprecated.
- **E-mail:** the built-in OpenAlex `mailto` address was removed. Set `"email"` in `config.json` if you want one sent.
- **Renamed metadata fields:** `openalex_api_key_configured`, `openalex_api_key_source`, `openalex_api_key_stored_in_output`.
- **SCImago cache:** with `config.example.json` the cache lives in `cache/scimago`; without a config it stays `data/scimago`. The first `sync-scimago` into a new folder downloads about 180 MB.
- **Examples:** the example query file and scripts are now in `examples/`.

## Known limitations
1. OpenAlex search results can change over time, in both content and ranking order.
2. The SCImago mirror currently covers 2010-2025.
3. 2026 publications use the latest available (2025) metadata, marked `LATEST_AVAILABLE`, not a "2026 quartile".
4. Conference coverage in SCImago varies substantially across years. A conference missing from one year is not evidence of Scopus discontinuation.
5. SCImago presence is not identical to official current Scopus status. SCImago absence is not evidence that a venue is predatory.
6. APC values are 2025 snapshot estimates, not guaranteed publisher prices.
7. Strict ISSN conflict protection may prefer false negatives over false-positive venue matches; review `TITLE_MATCH_ISSN_CONFLICT` rows in `source_audit.csv`.
8. The SCImago mirror repeats the current H-index in every year, so `h_index_at_publication` is not a historical H-index.
9. The mirror's server `manifest.json` still lists only four matching methods. This is documentation only; the client does not read it.
