# OpenAlex Literature Intelligence

![version](https://img.shields.io/badge/version-3.0.5%20Stable-blue) ![license](https://img.shields.io/badge/license-MIT-blue) ![python](https://img.shields.io/badge/python-3.11%2B-blue) ![tests](https://img.shields.io/badge/unit%20tests-52%2F52-brightgreen)

A command-line tool that turns a literature search into an auditable corpus. It finds works in
[OpenAlex](https://openalex.org/), attaches SCImago venue data (SJR, quartiles, categories, estimated
APC) both for the year each paper was published and for the latest snapshot, screens a main corpus with
a policy you declare, and records why every paper was kept or excluded.

```text
query -> OpenAlex discovery -> deduplication -> SCImago 2010-2025 enrichment
      -> policy screening -> raw / enriched / main / excluded / audit outputs
```

## What it does

- **Discovery.** One or many OpenAlex queries, cursor paging, resume after interruption, and
  deduplication by DOI, then OpenAlex ID, then normalized title and year.
- **Venue enrichment.** Each source is matched to the SCImago snapshots of 2010-2025 by ISSN, then
  ISSN-L, then title. A title match is never accepted when the ISSNs contradict each other.
- **Publication-year ranking.** SJR, Best Quartile and category quartiles come from the snapshot of the
  publication year. Nothing is interpolated: a 2026 paper gets latest metadata
  (`ranking_basis = LATEST_AVAILABLE`), not an invented 2026 quartile.
- **Source status.** `ACTIVE_LATEST`, `HISTORICAL_ONLY`, `UNMATCHED` or `AMBIGUOUS`, relative to the
  latest snapshot.
- **Screening.** The default main corpus is journals with status `ACTIVE_LATEST`. Optional filters:
  quartile (publication-year or latest, Best Quartile or a chosen category), estimated APC ceiling,
  DOAJ, CWTS Core, source type.
- **Audit trail.** The raw corpus is never overwritten; every excluded paper carries its exclusion
  reasons; a per-source audit, a summary and run metadata (tool version, policy, manifest, environment)
  are written with each run; every SCImago file is verified by SHA-256.

## What it does not do

- It does not search Scopus or Web of Science; discovery uses the OpenAlex Works API.
- It does not download full-text PDFs. OpenAlex open-access links are kept as fields.
- Presence in SCImago is not proof of current Scopus indexing, and absence is not evidence that a
  venue is predatory. The tool never makes either claim.
- APC values are estimates from a 2025 snapshot, not official publisher prices.
- It supports, but does not replace, a systematic-review protocol and title, abstract and full-text
  screening.

## Quick start

Requirements: Python 3.11 or newer, Internet access, and an OpenAlex API key (see
https://help.openalex.org/api/authentication/). Only `run` needs the key.

Windows PowerShell:

```powershell
git clone https://github.com/tvquynh/openalex-literature-intelligence.git
cd openalex-literature-intelligence
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item config.example.json config.json   # then put your key in openalex.api_key
```

Linux or macOS:

```bash
git clone https://github.com/tvquynh/openalex-literature-intelligence.git
cd openalex-literature-intelligence
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp config.example.json config.json          # then put your key in openalex.api_key
```

Download and verify the SCImago data (about 185 MB, once), then run a 100-paper pilot:

```bash
python literature_pipeline.py sync-scimago
python literature_pipeline.py validate-repo
python literature_pipeline.py run --query "malware detection machine learning" --from-year 2020 --to-year 2026 --require-abstract --max-per-query 100 --output pilot
```

`config.json` is private and listed in `.gitignore`. Settings are resolved in the order: command-line
argument, then `config.json`, then the built-in default. The `OPENALEX_API_KEY` environment variable is
still read after `config.json` for backward compatibility, but it is deprecated.

## Commands

| Command | Purpose | Needs API key |
|---|---|---|
| `sync-scimago` | Download the SCImago mirror into the local cache and verify every file by SHA-256 | no |
| `validate-repo` | Check the cache against `SHA256SUMS.txt` (`--offline` uses the cache only) | no |
| `run` | OpenAlex discovery, SCImago enrichment, screening and audit outputs | yes |
| `enrich` | Re-enrich and re-screen an existing OpenAlex CSV/JSONL without querying OpenAlex | no |
| `inspect-source` | Show one venue's SCImago history by `--title` or `--issn` | no |

Common screening options (for `run` and `enrich`):

| Option | Effect on the main corpus |
|---|---|
| `--quartile Q1 --quartile Q2` | keep the selected quartiles |
| `--quartile-basis publication` or `latest` | quartile of the publication year, or of the latest snapshot |
| `--quartile-mode relevant-category --relevant-category "Software"` | use the quartile of the named categories instead of Best Quartile |
| `--max-apc 1000` | keep venues with an estimated APC of at most 1000 USD |
| `--require-doaj`, `--require-cwts-core` | keep sources that OpenAlex lists in DOAJ or in the CWTS Core list |
| `--source-type journal --source-type "conference and proceedings"` | allowed SCImago source types (default: journal) |
| `--all-source-types` | drop the journal-only default |
| `--include-historical-only`, `--any-source-status` | also admit `HISTORICAL_ONLY` sources, or disable status filtering |

Filters combine with AND. Records that fail a filter go to `_excluded.csv` with the reason, so a
stricter or looser policy can be applied later with `enrich` without querying OpenAlex again.

## Outputs

For `--output pilot`:

| File | Content |
|---|---|
| `pilot_raw.csv`, `pilot_raw.jsonl` | unique OpenAlex records before enrichment |
| `pilot_enriched.csv`, `pilot_enriched.jsonl` | raw records plus SCImago fields, status, match method and diagnostics |
| `pilot_main.csv` | records that pass the active policy |
| `pilot_excluded.csv` | the other records, with `main_exclusion_reasons` |
| `pilot_source_audit.csv` | one row per OpenAlex source: status, match method, candidates, paper count |
| `pilot_summary.json` | counts by status, source class, match method, quartile and ranking basis |
| `pilot_run_metadata.json` | tool version, queries, policy, manifest and environment; records whether a key was configured, never the key |
| `pilot_checkpoint.json` | cursor and progress per query, used to resume |

## SCImago data and the default mirror

The SCImago CSV files are not part of this repository. `sync-scimago` downloads them from the mirror
named in `scimago.manifest_url`, which by default is
`https://scopus.cuatui.cloud/du-lieu/scimago/manifest.json`. This is a community mirror maintained by the
author on a best-effort basis, without an availability guarantee; its files are delivered through a CDN
cache. You can point the tool to any mirror with the same `manifest.json` and `SHA256SUMS.txt` layout
through `config.json` or `--manifest-url`. Once the cache is verified, `enrich`, `inspect-source` and
`validate-repo` work with `--offline`.

The original data come from the SCImago Journal & Country Rank (https://www.scimagojr.com/) and from
OpenAlex. If you redistribute data or derived datasets, check the terms of those providers first; see
[THIRD_PARTY_DATA.md](THIRD_PARTY_DATA.md).

## Documentation

- [docs/USER_GUIDE.md](docs/USER_GUIDE.md): the complete user guide (also as
  [Word](docs/OpenAlex_Literature_Intelligence_v3.0.5_User_Guide.docx)): concepts, installation, every
  command and filter, output fields, workflows by research goal, troubleshooting and limitations.
- [docs/README_vi.md](docs/README_vi.md) and [docs/QUICKSTART_vi.md](docs/QUICKSTART_vi.md):
  Vietnamese README and quick start.
- [RELEASE_NOTES.md](RELEASE_NOTES.md), [CHANGELOG.md](CHANGELOG.md), [TEST_REPORT.md](TEST_REPORT.md),
  [SECURITY.md](SECURITY.md).

## Tests

```bash
python -m unittest discover -s tests -v
```

The 52 tests need neither network access nor an API key: they use a synthetic SCImago repository and
local servers with fake keys.

## Citation and license

If the tool supports published work, please cite it using [CITATION.cff](CITATION.cff) (GitHub shows it
under "Cite this repository"). The code is released under the [MIT License](LICENSE). The license covers
the code only; OpenAlex and SCImago data remain under the terms of their providers.

Questions and bug reports are welcome in the
[issue tracker](https://github.com/tvquynh/openalex-literature-intelligence/issues). Please never paste an
API key or the contents of `config.json`.
