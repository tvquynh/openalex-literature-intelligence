# Security notes

## OpenAlex API key

- Put the key in the private file `config.json` (copied from `config.example.json`), field
  `openalex.api_key`. Never hard-code it in Python, and never put it in a shared ZIP, a Git repository,
  a screenshot or a public log.
- `config.json` is listed in `.gitignore`. Only `config.example.json`, which holds no key, is meant to
  be shared.
- Logs, metadata and test reports never contain the key: run metadata records only
  `openalex_api_key_configured`, `openalex_api_key_source` and `openalex_api_key_stored_in_output`.
- The code contains no key and no personal e-mail address; the OpenAlex `mailto` address is read from
  `config.json` only.
- Errors raised while reading `config.json` never echo values or unknown key names from the file.
- On a shared computer, restrict read access to `config.json` to your own account.
- The `OPENALEX_API_KEY` environment variable is still read, with lower priority than `config.json`,
  for backward compatibility; it is deprecated.
- Avoid `--api-key` on the command line: the value is visible in shell history and process lists
  (it still has the highest priority if used).
- If a key has ever been shared publicly or sent somewhere you no longer control, rotate it in the
  OpenAlex settings.
- OpenAlex receives the key as the `api_key` query parameter, so request URLs contain it. Since v3.0.4,
  every OpenAlex error message (HTTP 4xx, network errors) shows `api_key=REDACTED`, and the original
  exception, which contains the URL, is not chained into the traceback. v3.0.3 printed the full URL,
  key included, on HTTP 4xx and network errors; upgrade if you still use it.

## Repository integrity

Every file of the SCImago mirror is checked against `SHA256SUMS.txt`:

- a cached file with the right hash is reused;
- a cached file with the wrong hash is downloaded again when online;
- offline, a file with the wrong hash stops the run and is never used.

SHA-256 checks integrity; it is not a digital signature or a proof of origin. HTTPS, provenance
records and checksums are used together to reduce the risk of corrupted or unexpectedly changed files.

## Outputs

`run_metadata.json` never records the API key. Before sharing a corpus, check the reuse and
redistribution terms of the third-party metadata it contains (see `THIRD_PARTY_DATA.md`).

## Reporting a vulnerability

Please do not post details of a security problem in a public issue. Open an issue that only says you
found one and ask for a private contact. Never include a real API key in any report.
