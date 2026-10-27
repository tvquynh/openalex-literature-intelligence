"""Offline regression tests for OpenAlex Literature Intelligence (stdlib unittest only).

Run from the project root:
    python -m unittest discover -s tests -v

Every test uses a tiny synthetic SCImago repository written to a temporary directory and, where
HTTP is needed, a local 127.0.0.1 server. No internet access and no real API key are used.
"""
from __future__ import annotations

import contextlib
import csv
import hashlib
import http.server
import io
import json
import random
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from litintel import openalex, scimago_repo  # noqa: E402
from litintel.common import normalize_issn, normalize_quartile, read_csv, redact_secrets, split_issns  # noqa: E402
from litintel.pipeline import apply_main_policy, build_summary, enrich_existing_file, source_audit  # noqa: E402
from litintel.scimago import enrich_records, relevant_category_summary, source_history  # noqa: E402

openalex.time.sleep = lambda *_: None
scimago_repo.time.sleep = lambda *_: None

HEADER = [
    "Rank", "Sourceid", "Title", "Type", "Issn", "Publisher", "Open Access", "Open Access Diamond", "SJR",
    "SJR Best Quartile", "H index", "Total Docs. (YEAR)", "Total Docs. (3years)", "Total Refs.",
    "Total Citations (3years)", "Citable Docs. (3years)", "Citations / Doc. (2years)", "Ref. / Doc.", "%Female",
    "Overton", "Country", "Region", "Publisher", "Coverage", "Categories", "Areas",
]
FIRST, LATEST = 2020, 2023

# sourceid -> (title by year, type, issn by year, quartile by year, categories)
SOURCES = {
    "100": ({y: "Alpha Journal" for y in range(2020, 2024)}, "journal", {y: "11111111" for y in range(2020, 2024)},
            {2020: "-", 2021: "Q2", 2022: "Q1", 2023: "Q1"}, "Information Systems ({q}); Management Information Systems (Q1)"),
    "200": ({2020: "Hist Journal (discontinued)", 2021: "Hist Journal (discontinued)"}, "journal",
            {2020: "2222222X", 2021: "2222222X"}, {2020: "Q3", 2021: "Q2"}, "Software ({q})"),
    "300": ({2020: "Old Name", 2021: "Old Name", 2022: "New Name", 2023: "New Name"}, "journal",
            {2020: "33333333", 2021: "33333333", 2022: "33333334", 2023: "33333334"},
            {2020: "Q4", 2021: "Q4", 2022: "Q3", 2023: "Q3"}, "Software ({q})"),
    "401": ({2023: "Shared One"}, "journal", {2023: "44444444"}, {2023: "Q1"}, "Software ({q})"),
    "402": ({2023: "Shared Two"}, "journal", {2023: "44444444"}, {2023: "Q2"}, "Software ({q})"),
    "500": ({y: "Conf Proc" for y in range(2020, 2024)}, "conference and proceedings",
            {y: "55555555" for y in range(2020, 2024)}, {y: "-" for y in range(2020, 2024)}, "Software"),
    "600": ({2023: "Reissued Proc"}, "conference and proceedings", {2023: "66666666"}, {2023: "Q3"}, "Software ({q})"),
    "601": ({2020: "Reissued Proc"}, "conference and proceedings", {2020: "66666666"}, {2020: "Q4"}, "Software ({q})"),
    "700": ({2021: "Mixed Journal", 2022: "Mixed Journal"}, "journal", {2021: "77777777", 2022: "77777777"},
            {2021: "Q2", 2022: "Q2"}, "Software ({q})"),
    "701": ({2022: "Mixed Journal B"}, "journal", {2022: "77777777"}, {2022: "Q3"}, "Software ({q})"),
    "800": ({2020: "Journal X", 2021: "Journal X", 2022: "Journal X Series"}, "journal",
            {2020: "88888888", 2021: "88888888", 2022: "88888889"}, {2020: "Q2", 2021: "Q2", 2022: "Q3"}, "Software ({q})"),
    # v3.0.5 ISSN-conflict fixtures: a source without ISSN, and two sources sharing a normalised title.
    "910": ({y: "NoIssn Proceedings" for y in range(2020, 2024)}, "conference and proceedings",
            {y: "" for y in range(2020, 2024)}, {y: "Q3" for y in range(2020, 2024)}, "Software ({q})"),
    "920": ({2023: "Twin Journal"}, "journal", {2023: "92092092"}, {2023: "Q2"}, "Software ({q})"),
    "921": ({2023: "Twin-Journal"}, "journal", {2023: ""}, {2023: "Q3"}, "Software ({q})"),
    "930": ({2023: "Alpha and Beta Review"}, "journal", {2023: "93093093"}, {2023: "Q1"}, "Software ({q})"),
}
TYPE_OVERRIDES = {("800", 2022): "book series"}


def build_repo(directory: Path) -> Dict:
    """Write a synthetic SCImago mirror (4 annual files + APC snapshot + manifest + checksums)."""
    directory.mkdir(parents=True, exist_ok=True)
    for year in range(FIRST, LATEST + 1):
        header = [h.replace("YEAR", str(year)) for h in HEADER]
        with (directory / f"scimagojr-{year}.csv").open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh, delimiter=";", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(header)
            rank = 0
            for sid, (titles, stype, issns, quartiles, cats) in SOURCES.items():
                if year not in titles:
                    continue
                rank += 1
                q = quartiles[year]
                sjr = "" if q == "-" else f"{int(sid) / 100 + year - 2000:.3f}".replace(".", ",")
                row = [str(rank), sid, titles[year], TYPE_OVERRIDES.get((sid, year), stype), issns[year], "Pub", "No", "No", sjr, q, "42",
                       "10", "30", "100", "50", "30", "1,5", "10", "", "0", "Viet Nam", "Asiatic Region", "Pub",
                       "2020-2023", cats.format(q=q if q != "-" else "Q4"), "Computer Science"]
                writer.writerow(row)
    with (directory / "journal-value.csv").open("w", encoding="utf-8", newline="") as fh:
        fh.write("Rank;Sourceid;Title;Type;Issn;Publisher;Open Access;Open Access Diamond;SJR;SJR Best Quartile;"
                 "Total Docs. (2023);Estimated APC (USD);Estimated value (USD)\n")
        fh.write('1;100;"Alpha Journal";journal;"11111111";No;No;"Pub";1,230;Q1;10;1500;1000;\n')
    manifest = {
        "schema_version": 1, "dataset": "synthetic", "updated": "2026-10-25", "base_url": "http://127.0.0.1:1/",
        "sjr": {"first_year": FIRST, "last_year": LATEST, "latest_snapshot_year": LATEST,
                "url_pattern": "scimagojr-{year}.csv", "delimiter": ";", "encoding": "utf-8"},
        "journal_value": {"year": LATEST, "file": "journal-value.csv"},
        "checksums": {"algorithm": "sha256", "file": "SHA256SUMS.txt"},
        "files": {"expected_total_data_files": LATEST - FIRST + 2},
        "policy": {"require_present_in_latest_scimago_for_main_corpus": True},
    }
    write_checksums(directory, manifest)
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def write_checksums(directory: Path, manifest: Dict) -> None:
    names = [f"scimagojr-{y}.csv" for y in range(FIRST, LATEST + 1)] + [manifest["journal_value"]["file"]]
    lines = [f"{hashlib.sha256((directory / n).read_bytes()).hexdigest()}  {n}" for n in names]
    (directory / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def paper(pid: str, year, source: str, issn: str = "", issn_l: str = "", stype: str = "journal", src_id: str = "") -> Dict:
    return {"openalex_id": pid, "doi": "", "title": f"Paper {pid}", "publication_year": str(year),
            "source": source, "source_openalex_id": src_id or f"S-{source}", "source_type": stype,
            "issn": issn, "issn_l": issn_l, "source_is_in_doaj": "False", "source_is_core": "False"}


def corpus() -> List[Dict]:
    return [
        paper("p01", 2021, "Alpha Journal", "1111-1111", "1111-1111"),
        paper("p02", 2020, "Alpha Journal", "1111-1111", "1111-1111"),
        paper("p03", 2026, "Alpha Journal", "1111-1111", "1111-1111"),
        paper("p04", 2021, "Hist Journal", "2222-222x", "2222-222x"),
        paper("p05", 2022, "Hist Journal", "2222-222X", "2222-222X"),
        paper("p06", 2026, "Hist Journal", "2222-222X", "2222-222X"),
        paper("p07", 2020, "Hist Journal", "", "", src_id="S-hist-title-only"),
        paper("p08", 2023, "Unknown Venue", "9999-9999", "9999-9999"),
        paper("p09", 2023, "Shared", "4444-4444", "4444-4444"),
        paper("p10", 2021, "Conf Proc", "5555-5555", "5555-5555", stype="conference"),
        paper("p11", 2020, "Old Name", "3333-3333", "3333-3333"),
        paper("p12", 2020, "Reissued Proc", "6666-6666", "6666-6666", stype="conference"),
        paper("p13", 2026, "Old Name", "3333-3333", "3333-3333", src_id="S-old-name-2"),
        paper("p14", 2021, "Mixed Journal", "7777-7777", "7777-7777", src_id="S-mixed"),
        paper("p15", 2022, "Mixed Journal", "7777-7777", "7777-7777", src_id="S-mixed"),
        paper("p16", "", "Alpha Journal", "1111-1111", "1111-1111"),
        paper("p17", 2021, "", "", "", stype=""),
    ]


class RepoCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name) / "scimago"
        self.manifest = build_repo(self.dir)

    def tearDown(self):
        self.tmp.cleanup()

    def enrich(self, rows=None, categories=None):
        rows = rows if rows is not None else corpus()
        out = enrich_records(rows, self.dir, self.manifest, categories or [])
        return {r["openalex_id"]: r for r in out}, out


class TestNormalization(unittest.TestCase):
    def test_issn_normalization_handles_hyphen_case_and_lists(self):
        self.assertEqual(normalize_issn("1574-017x"), "1574017X")
        self.assertEqual(split_issns("1574-017x; 1875-905X, 1574017X|0000-0001"), ["1574017X", "1875905X", "00000001"])
        self.assertEqual(split_issns(""), [])

    def test_quartile_placeholder(self):
        self.assertEqual(normalize_quartile("-"), "")
        self.assertEqual(normalize_quartile(" q2 "), "Q2")

    def test_relevant_category_is_exact_not_substring(self):
        cats = "Information Systems and Management (Q1); Management Information Systems (Q1); Communication (Q1)"
        self.assertEqual(relevant_category_summary(cats, ["Information Systems", "Computer Networks and Communications"]), ("", ""))
        cats = "Information Systems (Q3); Management Information Systems (Q1)"
        self.assertEqual(relevant_category_summary(cats, ["information systems"]), ("Information Systems (Q3)", "Q3"))

    def test_redact_secrets(self):
        text = "GET /works?search=x&api_key=SECRET123&mailto=a@b.c failed; key SECRET123"
        redacted = redact_secrets(text, "SECRET123")
        self.assertNotIn("SECRET123", redacted)
        self.assertIn("api_key=REDACTED", redacted)


class TestEnrichment(RepoCase):
    def test_active_latest_uses_exact_publication_year_row(self):
        rows, _ = self.enrich()
        p01 = rows["p01"]
        self.assertEqual(p01["source_status"], "ACTIVE_LATEST")
        self.assertEqual(p01["scimago_sourceid"], "100")
        self.assertEqual(p01["ranking_basis"], "EXACT_PUBLICATION_YEAR")
        self.assertEqual(p01["sjr_year_at_publication"], 2021)
        self.assertEqual(p01["best_quartile_at_publication"], "Q2")  # 2021 row, not the latest Q1
        self.assertAlmostEqual(p01["sjr_at_publication"], 22.0)
        self.assertEqual(p01["best_quartile_latest"], "Q1")

    def test_dash_quartile_is_unavailable_not_a_value(self):
        rows, out = self.enrich()
        self.assertEqual(rows["p02"]["best_quartile_at_publication"], "")
        self.assertEqual(rows["p02"]["ranking_basis"], "EXACT_PUBLICATION_YEAR")
        main, excluded = apply_main_policy(out, self.manifest, source_types=["journal"], quartiles=["Q1"])
        self.assertIn("QUARTILE_UNAVAILABLE", rows["p02"]["main_exclusion_reasons"])
        summary = build_summary(out, main, excluded)
        self.assertNotIn("-", summary["publication_quartile_counts"])
        self.assertGreaterEqual(summary["publication_quartile_counts"]["NOT_ASSIGNED"], 1)

    def test_future_year_never_gets_publication_year_metrics(self):
        rows, _ = self.enrich()
        p03 = rows["p03"]
        self.assertEqual(p03["source_status"], "ACTIVE_LATEST")
        self.assertEqual(p03["ranking_basis"], "LATEST_AVAILABLE")
        self.assertIsNone(p03["sjr_year_at_publication"])
        self.assertIsNone(p03["sjr_at_publication"])
        self.assertEqual(p03["best_quartile_at_publication"], "")
        self.assertEqual(p03["best_quartile_latest"], "Q1")

    def test_future_year_without_latest_metadata_is_unavailable(self):
        rows, _ = self.enrich()
        self.assertEqual(rows["p06"]["ranking_basis"], "UNAVAILABLE")
        self.assertEqual(rows["p08"]["ranking_basis"], "UNAVAILABLE")

    def test_historical_only_from_publication_year(self):
        rows, _ = self.enrich()
        p04 = rows["p04"]
        self.assertEqual(p04["source_status"], "HISTORICAL_ONLY")
        self.assertEqual(p04["scimago_sourceid_historical"], "200")
        self.assertEqual(p04["best_quartile_at_publication"], "Q2")
        self.assertFalse(p04["in_scimago_latest"])
        self.assertNotIn("sjr_latest", p04)

    def test_historical_only_when_publication_year_absent_or_future(self):
        rows, _ = self.enrich()
        for pid in ("p05", "p06"):
            row = rows[pid]
            self.assertEqual(row["source_status"], "HISTORICAL_ONLY", pid)
            self.assertEqual(row["scimago_sourceid_historical"], "200")
            self.assertEqual(row["historical_match_method"], "ANY_EARLIER_SNAPSHOT_ISSNL_EXACT")
            self.assertEqual(row["historical_snapshot_years"], "2020-2021")
            self.assertEqual(row["ranking_basis"], "UNAVAILABLE")
            self.assertEqual(row["best_quartile_at_publication"], "")

    def test_historical_title_with_discontinued_suffix(self):
        rows, _ = self.enrich()
        p07 = rows["p07"]
        self.assertEqual(p07["source_status"], "HISTORICAL_ONLY")
        self.assertEqual(p07["publication_match_method"], "TITLE_STATUS_NORMALIZED")
        self.assertEqual(p07["best_quartile_at_publication"], "Q3")

    def test_unmatched_and_ambiguous_are_never_resolved_silently(self):
        rows, _ = self.enrich()
        self.assertEqual(rows["p08"]["source_status"], "UNMATCHED")
        p09 = rows["p09"]
        self.assertEqual(p09["source_status"], "AMBIGUOUS")
        self.assertEqual(p09["scimago_sourceid"], "")
        self.assertEqual(p09["latest_match_candidates"], "401; 402")
        self.assertEqual(p09["ranking_basis"], "UNAVAILABLE")
        self.assertEqual(rows["p15"]["source_status"], "AMBIGUOUS")  # two Sourceids share the ISSN in 2022

    def test_sourceid_present_in_latest_is_never_historical_only(self):
        rows, _ = self.enrich()
        p11, p13 = rows["p11"], rows["p13"]
        self.assertEqual(p11["source_status"], "ACTIVE_LATEST")
        self.assertEqual(p11["latest_match_method"], "SOURCEID_VIA_PUBLICATION_YEAR_ISSNL_EXACT")
        self.assertEqual(p11["scimago_title_latest"], "New Name")
        self.assertEqual(p11["best_quartile_at_publication"], "Q4")
        self.assertEqual(p13["source_status"], "ACTIVE_LATEST")
        self.assertEqual(p13["latest_match_method"], "SOURCEID_VIA_HISTORICAL_ISSNL_EXACT")
        self.assertEqual(p13["ranking_basis"], "LATEST_AVAILABLE")

    def test_publication_metrics_from_other_sourceid_are_flagged(self):
        rows, out = self.enrich()
        p12 = rows["p12"]
        self.assertEqual(p12["scimago_sourceid"], "600")
        self.assertEqual(p12["scimago_sourceid_at_publication"], "601")
        self.assertTrue(p12["publication_sourceid_differs"])
        self.assertEqual(build_summary(out, [], [])["papers_with_publication_sourceid_differing_from_identity"], 1)
        self.assertFalse(rows["p01"]["publication_sourceid_differs"])

    def test_missing_year_and_missing_source(self):
        rows, _ = self.enrich()
        self.assertEqual(rows["p16"]["ranking_basis"], "UNAVAILABLE")
        self.assertEqual(rows["p17"]["source_status"], "UNMATCHED")

    def test_reenrichment_ignores_stale_enrichment_columns(self):
        _, first = self.enrich()
        snapshot = {r["openalex_id"]: {k: str(v) for k, v in r.items()} for r in first}
        stale = [dict(r) for r in first]
        for row in stale:  # values an older run / older SCImago release might have left behind
            row.update({"scimago_sourceid_historical": "401", "sjr_latest": "9.9", "best_quartile_latest": "Q1",
                        "scimago_type_latest": "journal", "historical_snapshot_years": "1999", "source_status": "ACTIVE_LATEST"})
        _, second = self.enrich(stale)
        for row in second:
            self.assertEqual({k: str(v) for k, v in row.items()}, snapshot[row["openalex_id"]], row["openalex_id"])
        ambiguous = {r["openalex_id"]: r for r in second}["p09"]
        self.assertEqual((ambiguous["source_status"], ambiguous["ranking_basis"]), ("AMBIGUOUS", "UNAVAILABLE"))
        self.assertNotIn("sjr_latest", ambiguous)

    def test_historical_result_does_not_depend_on_other_rows(self):
        row_a = paper("a", 2026, "Journal X", "8888-8888", "8888-8888", src_id="S-x")
        row_b = paper("b", 2026, "Other", "8888-8889", "8888-8889", src_id="S-other")
        alone, _ = self.enrich([dict(row_a)])
        together, _ = self.enrich([dict(row_a), dict(row_b)])
        for field in ("source_status", "historical_snapshot_years", "scimago_type_historical"):
            self.assertEqual(alone["a"][field], together["a"][field], field)
        self.assertEqual(alone["a"]["historical_snapshot_years"], "2020-2021")
        self.assertEqual(alone["a"]["scimago_type_historical"], "journal")
        self.assertEqual(together["b"]["scimago_type_historical"], "book series")

    def test_relevant_category_quartile_uses_exact_category(self):
        rows, _ = self.enrich(categories=["Information Systems"])
        self.assertEqual(rows["p01"]["relevant_category_quartile_at_publication"], "Q2")
        self.assertEqual(rows["p01"]["relevant_categories_at_publication"], "Information Systems (Q2)")


class TestMainPolicyAndReporting(RepoCase):
    def test_partition_journal_only_and_all_source_types(self):
        _, out = self.enrich()
        main, excluded = apply_main_policy(out, self.manifest, source_types=["journal"])
        ids_main = {r["openalex_id"] for r in main}
        self.assertEqual(len(main) + len(excluded), len(out))
        self.assertFalse(ids_main & {r["openalex_id"] for r in excluded})
        self.assertTrue(all(r["source_status"] == "ACTIVE_LATEST" for r in main))
        self.assertTrue(all((r.get("scimago_type_latest") or r["source_type"]) == "journal" for r in main))
        self.assertNotIn("p10", ids_main)
        _, out = self.enrich()
        main_all, _ = apply_main_policy(out, self.manifest, source_types=[])
        self.assertIn("p10", {r["openalex_id"] for r in main_all})
        self.assertEqual(len(main_all), sum(1 for r in out if r["source_status"] == "ACTIVE_LATEST"))

    def test_include_historical_only_does_not_admit_unmatched_or_ambiguous(self):
        _, out = self.enrich()
        main, _ = apply_main_policy(out, self.manifest, source_types=["journal"], include_historical_only=True)
        statuses = {r["source_status"] for r in main}
        self.assertEqual(statuses, {"ACTIVE_LATEST", "HISTORICAL_ONLY"})
        self.assertIn("p04", {r["openalex_id"] for r in main})
        _, out = self.enrich()
        main_any, _ = apply_main_policy(out, self.manifest, source_types=["journal"], any_source_status=True)
        self.assertTrue({"UNMATCHED", "AMBIGUOUS"} <= {r["source_status"] for r in main_any})

    def test_source_audit_aggregates_and_is_order_independent(self):
        _, out = self.enrich()
        audit = {a["source_openalex_id"]: a for a in source_audit(out)}
        self.assertEqual(audit["S-mixed"]["source_status"], "MIXED")
        self.assertEqual(audit["S-mixed"]["paper_status_counts"], "AMBIGUOUS:1; HISTORICAL_ONLY:1")
        self.assertEqual(audit["S-Hist Journal"]["paper_count"], 3)
        rows = corpus()
        random.Random(7).shuffle(rows)
        _, shuffled = self.enrich(rows)
        key = lambda a: a["source_openalex_id"]  # noqa: E731
        self.assertEqual(sorted(source_audit(out), key=key), sorted(source_audit(shuffled), key=key))

    def test_source_audit_descriptive_fields_are_order_independent(self):
        p1 = paper("h1", 2022, "Journal X Series", "8888-8889", "8888-8889", src_id="S-shared")
        p2 = paper("u1", 2023, "Unknown Venue", "9999-9999", "9999-9999", src_id="S-shared")
        _, forward = self.enrich([dict(p1), dict(p2)])
        _, backward = self.enrich([dict(p2), dict(p1)])
        a, b = source_audit(forward), source_audit(backward)
        self.assertEqual(a, b)
        self.assertEqual(a[0]["source_class"], "BOOK_SERIES | JOURNAL")
        self.assertEqual(a[0]["source_status"], "MIXED")
        self.assertEqual(build_summary(forward, [], [])["unique_source_class_counts"],
                         build_summary(backward, [], [])["unique_source_class_counts"])

    def test_enrich_file_outputs_stable_schema_and_metadata(self):
        tmp = Path(self.tmp.name)
        src = tmp / "in.csv"
        rows = [paper("x1", 2023, "Unknown Venue", "9999-9999")]
        with src.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        summary = enrich_existing_file(src, tmp / "out", self.dir, self.manifest, source_types=["journal"])
        self.assertEqual(summary["main_corpus_records"], 0)
        header_main = (tmp / "out_main.csv").read_text(encoding="utf-8-sig").splitlines()[0]
        header_enriched = (tmp / "out_enriched.csv").read_text(encoding="utf-8-sig").splitlines()[0]
        self.assertEqual(header_main, header_enriched)
        meta = json.loads((tmp / "out_run_metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["command"], "enrich")
        self.assertEqual(len(meta["input_sha256"]), 64)
        self.assertEqual(len(read_csv(tmp / "out_excluded.csv")), 1)


class TestInspectSource(RepoCase):
    def test_active_source_history_is_per_year(self):
        match, history, apc, status = source_history(self.dir, self.manifest, "Alpha Journal")
        self.assertEqual((status, match.sourceid), ("ACTIVE_LATEST", "100"))
        self.assertEqual([h["year"] for h in history], [2020, 2021, 2022, 2023])
        self.assertEqual([h["best_quartile"] for h in history], ["", "Q2", "Q1", "Q1"])
        self.assertEqual(len({h["sjr"] for h in history if h["sjr"] is not None}), 3)
        self.assertEqual(apc["estimated_apc_usd"], 1500.0)

    def test_historical_only_source_found_with_trajectory(self):
        match, history, apc, status = source_history(self.dir, self.manifest, "Hist Journal")
        self.assertEqual((status, match.sourceid), ("HISTORICAL_ONLY", "200"))
        self.assertEqual(match.method, "HISTORICAL_TITLE_STATUS_NORMALIZED")
        self.assertEqual([h["year"] for h in history], [2020, 2021])
        self.assertIsNone(apc)
        match, _, _, status = source_history(self.dir, self.manifest, "", "2222-222x")
        self.assertEqual((status, match.method), ("HISTORICAL_ONLY", "HISTORICAL_ISSN_EXACT"))

    def test_old_title_of_latest_source_is_active(self):
        match, history, _, status = source_history(self.dir, self.manifest, "Old Name")
        self.assertEqual((status, match.sourceid), ("ACTIVE_LATEST", "300"))
        self.assertEqual(match.method, "SOURCEID_VIA_HISTORICAL_TITLE_EXACT")
        self.assertEqual(len(history), 4)

    def test_ambiguous_and_unmatched(self):
        self.assertEqual(source_history(self.dir, self.manifest, "", "4444-4444")[3], "AMBIGUOUS")
        self.assertEqual(source_history(self.dir, self.manifest, "", "7777-7777")[3], "AMBIGUOUS")
        self.assertEqual(source_history(self.dir, self.manifest, "No Such Venue")[3], "UNMATCHED")


class _StaticHandler(http.server.SimpleHTTPRequestHandler):
    hits: List[str] = []

    def log_message(self, *args):
        pass

    def do_GET(self):  # noqa: N802
        type(self).hits.append(self.path)
        super().do_GET()


@contextlib.contextmanager
def serve(directory: Path):
    handler = type("Handler", (_StaticHandler,), {"hits": []})
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **k: handler(*a, directory=str(directory), **k))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/", handler
    finally:
        server.shutdown()
        server.server_close()


class TestRepositoryIntegrity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.remote = Path(self.tmp.name) / "remote"
        self.cache = Path(self.tmp.name) / "cache"
        self.manifest = build_repo(self.remote)

    def tearDown(self):
        self.tmp.cleanup()

    def publish(self, base_url):
        self.manifest["base_url"] = base_url
        (self.remote / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def sync(self, base, **kw):
        with contextlib.redirect_stdout(io.StringIO()):
            return scimago_repo.sync_repository(self.cache, base + "manifest.json", verbose=True, **kw)

    def test_cold_warm_corrupt_and_offline(self):
        with serve(self.remote) as (base, _):
            self.publish(base)
            state = self.sync(base)["state"]
            self.assertEqual((state["downloaded_files"], state["reused_files"], state["integrity_verified"]), (5, 0, True))
            state = self.sync(base)["state"]
            self.assertEqual((state["downloaded_files"], state["reused_files"]), (0, 5))
            self.assertTrue(scimago_repo.validate_cached_repository(self.cache, base + "manifest.json")["ok"])

            target = self.cache / "scimagojr-2021.csv"
            target.write_bytes(target.read_bytes().replace(b"Alpha", b"Alphb"))
            result = scimago_repo.validate_cached_repository(self.cache, offline=True)
            self.assertFalse(result["ok"])
            self.assertEqual([r["file"] for r in result["files"] if not r["sha256_ok"]], ["scimagojr-2021.csv"])
            with self.assertRaises(scimago_repo.RepositoryError):
                scimago_repo.sync_repository(self.cache, offline=True, verbose=False)
            state = self.sync(base)["state"]
            self.assertEqual(state["downloaded_files"], 1)
            self.assertTrue(scimago_repo.validate_cached_repository(self.cache, offline=True)["ok"])

    def test_remote_bytes_not_matching_checksum_are_rejected(self):
        with serve(self.remote) as (base, _):
            self.publish(base)
            self.sync(base)
            good = (self.cache / "scimagojr-2022.csv").read_bytes()
            (self.cache / "scimagojr-2022.csv").write_bytes(b"corrupt")
            (self.remote / "scimagojr-2022.csv").write_bytes(b"tampered remote bytes")
            with self.assertRaisesRegex(scimago_repo.RepositoryError, "SHA-256 mismatch"):
                self.sync(base)
            self.assertEqual((self.cache / "scimagojr-2022.csv").read_bytes(), b"corrupt")
            self.assertFalse((self.cache / "scimagojr-2022.csv.part").exists())
            self.assertFalse(scimago_repo.validate_cached_repository(self.cache, offline=True)["ok"])
            (self.remote / "scimagojr-2022.csv").write_bytes(good)
            self.assertEqual(self.sync(base)["state"]["downloaded_files"], 1)

    def test_missing_remote_file_fails_fast(self):
        with serve(self.remote) as (base, handler):
            self.publish(base)
            (self.remote / "scimagojr-2020.csv").unlink()
            with self.assertRaisesRegex(scimago_repo.RepositoryError, "not found \\(HTTP 404\\)"):
                self.sync(base)
            self.assertEqual(sum(1 for p in handler.hits if p.startswith("/scimagojr-2020.csv")), 1)

    def test_offline_without_cache_and_unsafe_names(self):
        with self.assertRaises(scimago_repo.RepositoryError):
            scimago_repo.sync_repository(self.cache, offline=True, verbose=False)
        bad = json.loads(json.dumps(self.manifest))
        bad["journal_value"]["file"] = "../outside.csv"
        self.assertTrue(any("Unsafe" in e for e in scimago_repo.validate_manifest(bad)))


class _OpenAlexHandler(http.server.BaseHTTPRequestHandler):
    works = [{"id": f"https://openalex.org/W{i}", "doi": f"https://doi.org/10.1/{i}", "title": f"T{i}",
              "publication_year": 2024, "primary_location": {"source": {"display_name": "Alpha Journal"}}}
             for i in range(1, 4)]
    status = 200
    calls: List[str] = []

    def log_message(self, *args):
        pass

    def do_GET(self):  # noqa: N802
        from urllib.parse import parse_qs, urlparse
        type(self).calls.append(self.path)
        if type(self).status != 200:
            body = b'{"error": "bad request"}'
            self.send_response(type(self).status)
        else:
            qs = parse_qs(urlparse(self.path).query)
            start = 0 if qs["cursor"][0] == "*" else int(qs["cursor"][0])
            per_page = int(qs["per_page"][0])
            chunk = self.works[start:start + per_page]
            nxt = str(start + per_page) if start + per_page < len(self.works) else None
            body = json.dumps({"meta": {"count": len(self.works), "next_cursor": nxt}, "results": chunk}).encode()
            self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@contextlib.contextmanager
def fake_openalex(status=200):
    handler = type("H", (_OpenAlexHandler,), {"calls": [], "status": status})
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    old = openalex.OPENALEX_WORKS_URL
    openalex.OPENALEX_WORKS_URL = f"http://127.0.0.1:{server.server_port}/works"
    try:
        yield handler
    finally:
        openalex.OPENALEX_WORKS_URL = old
        server.shutdown()
        server.server_close()


class TestOpenAlex(unittest.TestCase):
    FAKE_KEY = "FAKEKEY_NEVER_PRINT_42"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def download(self, limit, **kw):
        with contextlib.redirect_stdout(io.StringIO()):
            return openalex.download_queries(["q"], 2020, 2026, self.FAKE_KEY, "", self.dir / "raw.jsonl",
                                             self.dir / "ckpt.json", max_per_query=limit, **kw)

    def test_api_key_never_appears_in_errors(self):
        for status in (400, 403):
            with fake_openalex(status=status):
                client = openalex.OpenAlexClient(api_key=self.FAKE_KEY)
                with self.assertRaises(RuntimeError) as ctx:
                    client.request({"search": "x", "api_key": self.FAKE_KEY})
                self.assertNotIn(self.FAKE_KEY, str(ctx.exception))
                self.assertIsNone(ctx.exception.__cause__)
        old_retries, openalex.MAX_RETRIES = openalex.MAX_RETRIES, 2
        try:
            client = openalex.OpenAlexClient(api_key=self.FAKE_KEY, base_url="http://127.0.0.1:9/works")
            out = io.StringIO()
            with contextlib.redirect_stdout(out), self.assertRaises(openalex.requests.RequestException) as ctx:
                client.request({"search": "x", "api_key": self.FAKE_KEY})
            self.assertNotIn(self.FAKE_KEY, str(ctx.exception) + out.getvalue())
            self.assertIsNone(ctx.exception.__cause__)
            self.assertTrue(ctx.exception.__suppress_context__)
        finally:
            openalex.MAX_RETRIES = old_retries

    def test_stop_by_limit_is_success_not_failure_and_resume_exhausts(self):
        with fake_openalex():
            rows, summary = self.download(2)
            state = summary["queries"][0]
            self.assertEqual(len(rows), 2)
            self.assertEqual((state["stopped_by_limit"], state["has_more_results"], state["query_exhausted"],
                              state["run_completed_successfully"]), (True, True, False, True))
            rows, summary = self.download(10)
            state = summary["queries"][0]
            self.assertEqual(len(rows), 3)
            self.assertEqual((state["stopped_by_limit"], state["query_exhausted"], state["has_more_results"]), (False, True, False))
        ckpt = json.loads((self.dir / "ckpt.json").read_text(encoding="utf-8"))
        self.assertNotIn(self.FAKE_KEY, json.dumps(ckpt))
        self.assertNotIn(self.FAKE_KEY, (self.dir / "raw.jsonl").read_text(encoding="utf-8"))

    def test_legacy_checkpoint_at_limit_needs_no_network(self):
        sig = {"query": "q", "from_year": 2020, "to_year": 2026, "require_abstract": False}
        (self.dir / "ckpt.json").write_text(json.dumps({"version": 1, "queries": {"q": {
            "signature": sig, "cursor": "abc", "retrieved": 2, "page": 1, "matches_total": 9, "done": False}}}), encoding="utf-8")
        with fake_openalex() as handler:
            _, summary = self.download(2)
            self.assertEqual(handler.calls, [])
        state = summary["queries"][0]
        self.assertEqual((state["stopped_by_limit"], state["has_more_results"], state["run_completed_successfully"]), (True, True, True))
        self.assertEqual(json.loads((self.dir / "ckpt.json").read_text(encoding="utf-8"))["version"], 2)

    def test_dedup_doi_and_openalex_id_are_aliases(self):
        store = openalex.RecordStore()
        self.assertTrue(store.add({"openalex_id": "W1", "doi": "", "title": "A", "matched_query": "q1"}))
        self.assertFalse(store.add({"openalex_id": "W1", "doi": "https://doi.org/10.5/ABC", "title": "A", "matched_query": "q2"}))
        self.assertFalse(store.add({"openalex_id": "", "doi": "10.5/abc", "title": "A", "matched_query": "q3"}))
        self.assertEqual(len(store), 1)
        record = next(iter(store.values()))
        self.assertEqual(record["doi"], "10.5/abc")
        self.assertEqual(record["matched_query"], "q1 || q2 || q3")
        self.assertTrue(store.add({"openalex_id": "W2", "doi": "10.5/xyz", "title": "B"}))
        self.assertIsNone(store.add({"openalex_id": "", "doi": "", "title": ""}))


class TestIssnConflict(RepoCase):
    """v3.0.5: a title match must never override contradictory ISSN evidence (generic, fixture-driven)."""

    def one(self, row, categories=None):
        rows, out = self.enrich([row], categories)
        return rows[row["openalex_id"]], out

    def test_1_6_latest_title_with_wrong_issn_does_not_match(self):
        row, out = self.one(paper("c1", 2021, "Alpha Journal", "9999-9999", "9999-9999"))
        self.assertEqual(row["source_status"], "UNMATCHED")
        self.assertEqual(row["latest_match_method"], "TITLE_MATCH_ISSN_CONFLICT")
        self.assertEqual(row["latest_match_candidates"], "100")
        self.assertEqual(row["scimago_sourceid"], "")
        self.assertNotIn("sjr_latest", row)
        self.assertNotIn("best_quartile_latest", row)
        self.assertEqual((row["sjr_at_publication"], row["best_quartile_at_publication"]), (None, ""))
        self.assertEqual(row["ranking_basis"], "UNAVAILABLE")
        self.assertEqual(row["publication_match_method"], "TITLE_MATCH_ISSN_CONFLICT")
        self.assertEqual(row["historical_match_method"], "ANY_EARLIER_SNAPSHOT_TITLE_MATCH_ISSN_CONFLICT")
        self.assertEqual((row["match_diagnostic"], row["issn_conflict_candidates"]), ("ISSN_CONFLICT", "100"))
        main, _ = apply_main_policy(out, self.manifest, source_types=[], include_historical_only=True)
        self.assertEqual(main, [])
        audit = source_audit(out)[0]
        self.assertEqual((audit["latest_match_method"], audit["match_diagnostic"]), ("TITLE_MATCH_ISSN_CONFLICT", "ISSN_CONFLICT"))
        self.assertEqual(build_summary(out, [], [])["match_diagnostic_counts"], {"ISSN_CONFLICT": 1})

    def test_2_title_without_issn_still_matches(self):
        row, _ = self.one(paper("c2", 2021, "Alpha Journal", "", ""))
        self.assertEqual((row["source_status"], row["latest_match_method"], row["scimago_sourceid"]), ("ACTIVE_LATEST", "TITLE_EXACT", "100"))
        self.assertEqual(row["match_diagnostic"], "")

    def test_3_issn_wins_over_different_title(self):
        row, _ = self.one(paper("c3", 2021, "Alpha Journal (Online Edition)", "1111-1111", ""))
        self.assertEqual((row["source_status"], row["latest_match_method"], row["scimago_sourceid"]), ("ACTIVE_LATEST", "ISSN_EXACT", "100"))
        self.assertEqual(row["best_quartile_at_publication"], "Q2")

    def test_4_discontinued_title_with_correct_issn_is_historical(self):
        row, _ = self.one(paper("c4", 2021, "Hist Journal", "2222-222X", ""))
        self.assertEqual((row["source_status"], row["scimago_sourceid_historical"]), ("HISTORICAL_ONLY", "200"))
        self.assertEqual(row["match_diagnostic"], "")

    def test_5_historical_title_with_wrong_issn_does_not_match(self):
        for year in (2021, 2026):
            row, _ = self.one(paper(f"c5-{year}", year, "Hist Journal", "9999-9999", ""))
            self.assertEqual(row["source_status"], "UNMATCHED", year)
            self.assertNotIn("scimago_sourceid_historical", row)
            self.assertEqual(row["historical_match_method"], "ANY_EARLIER_SNAPSHOT_TITLE_MATCH_ISSN_CONFLICT")
            self.assertEqual(row["historical_match_candidates"], "200")
            self.assertEqual((row["best_quartile_at_publication"], row["ranking_basis"]), ("", "UNAVAILABLE"))
            self.assertEqual(row["match_diagnostic"], "ISSN_CONFLICT")

    def test_7_candidate_without_issn_is_not_a_conflict(self):
        row, _ = self.one(paper("c7", 2021, "NoIssn Proceedings", "9999-9999", "9999-9999", stype="conference"))
        self.assertEqual((row["source_status"], row["latest_match_method"], row["scimago_sourceid"]), ("ACTIVE_LATEST", "TITLE_EXACT", "910"))
        self.assertEqual(row["match_diagnostic"], "")

    def test_8_ambiguous_title_is_never_resolved_silently(self):
        row, _ = self.one(paper("c8", 2023, "Twin Journal.", "", ""))
        self.assertEqual((row["source_status"], row["latest_match_method"], row["latest_match_candidates"]), ("AMBIGUOUS", "TITLE_NORMALIZED", "920; 921"))
        # With an ISSN, the contradicting candidate is excluded; the remaining one (no ISSN) is unique.
        row, _ = self.one(paper("c8b", 2023, "Twin Journal.", "9999-9999", ""))
        self.assertEqual((row["source_status"], row["scimago_sourceid"]), ("ACTIVE_LATEST", "921"))
        self.assertEqual((row["match_diagnostic"], row["issn_conflict_candidates"]), ("ISSN_CONFLICT", "920"))

    def test_ampersand_title_matches_and_title(self):
        row, _ = self.one(paper("c10", 2023, "Alpha & Beta Review", "", ""))
        self.assertEqual((row["source_status"], row["latest_match_method"], row["scimago_sourceid"]), ("ACTIVE_LATEST", "TITLE_NORMALIZED", "930"))
        row, _ = self.one(paper("c10b", 2023, "Alpha & Beta Review", "9999-9999", ""))
        self.assertEqual((row["source_status"], row["latest_match_method"]), ("UNMATCHED", "TITLE_MATCH_ISSN_CONFLICT"))

    def test_invalid_issn_is_not_identifier_evidence(self):
        row, _ = self.one(paper("c9", 2021, "Alpha Journal", "12-34", ""))
        self.assertEqual((row["source_status"], row["latest_match_method"]), ("ACTIVE_LATEST", "TITLE_EXACT"))

    def test_inspect_source_applies_the_same_rule(self):
        match, history, _, status = source_history(self.dir, self.manifest, "Alpha Journal", "9999-9999")
        self.assertEqual((status, match.method, match.candidates, history), ("UNMATCHED", "TITLE_MATCH_ISSN_CONFLICT", ("100",), []))
        match, _, _, status = source_history(self.dir, self.manifest, "Hist Journal", "9999-9999")
        self.assertEqual((status, match.method, match.candidates), ("UNMATCHED", "TITLE_MATCH_ISSN_CONFLICT", ("200",)))
        match, _, _, status = source_history(self.dir, self.manifest, "Alpha Journal", "1111-1111")
        self.assertEqual((status, match.sourceid, match.method), ("ACTIVE_LATEST", "100", "ISSN_EXACT"))
        match, _, _, status = source_history(self.dir, self.manifest, "Hist Journal")
        self.assertEqual((status, match.sourceid), ("HISTORICAL_ONLY", "200"))

    def test_no_personal_email_or_key_in_source(self):
        import re
        sources = [ROOT / "literature_pipeline.py", ROOT / "config.example.json", *sorted((ROOT / "litintel").glob("*.py"))]
        emails = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
        for path in sources:
            text = path.read_text(encoding="utf-8")
            found = [e for e in emails.findall(text) if not e.endswith(("example.org", "example.com"))]
            self.assertEqual(found, [], path.name)
        self.assertEqual(json.loads((ROOT / "config.example.json").read_text(encoding="utf-8"))["openalex"], {"api_key": "", "email": ""})


_COPY_COUNTER = [0]


def make_project_copy(base: Path, config=None) -> Path:
    """Fresh copy of the CLI (script + litintel, never an existing config.json); optional config.json."""
    import shutil
    proj = base / f"proj{_COPY_COUNTER[0]}"
    _COPY_COUNTER[0] += 1
    proj.mkdir(parents=True)
    shutil.copy2(ROOT / "literature_pipeline.py", proj / "literature_pipeline.py")
    shutil.copytree(ROOT / "litintel", proj / "litintel", ignore=shutil.ignore_patterns("__pycache__"))
    if config is not None:
        text = config if isinstance(config, str) else json.dumps(config)
        (proj / "config.json").write_text(text, encoding="utf-8")
    return proj


def load_cli(proj: Path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(f"lp_copy_{proj.name}", proj / "literature_pipeline.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_cli(proj: Path, argv: List[str]):
    from unittest import mock
    cli = load_cli(proj)
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = cli.main(argv)
        except SystemExit as exc:  # argparse errors
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class TestConfig(unittest.TestCase):
    FAKE_KEY = "CFGKEY_NEVER_PRINT_987654"

    def setUp(self):
        from unittest import mock
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.repo = self.base / "scimago_remote"
        self.manifest = build_repo(self.repo)
        # No ambient credential may leak into these tests.
        self.env = mock.patch.dict("os.environ", {}, clear=False)
        self.env.start()
        import os
        os.environ.pop("OPENALEX_API_KEY", None)

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def parsed(self, proj, argv):
        cli = load_cli(proj)
        args = cli.build_parser().parse_args(argv)
        from litintel.config import load_config
        config = load_config(args.config, proj)
        sources = cli.resolve_settings(args, config)
        return args, sources

    def test_without_config_file_defaults_apply_and_offline_commands_work(self):
        proj = make_project_copy(self.base)
        args, sources = self.parsed(proj, ["run", "--query", "x"])
        self.assertEqual((args.from_year, args.to_year, args.require_abstract, args.max_per_query), (2010, 2026, False, None))
        self.assertEqual(args.cache_dir, Path("data") / "scimago")
        self.assertEqual(sources["cache_dir"], "default")
        self.assertEqual(sources["api_key"], "not configured")
        code, out, _ = run_cli(proj, ["validate-repo", "--offline", "--cache-dir", str(self.repo)])
        self.assertEqual(code, 0)
        self.assertIn("Config: none", out)
        code, out, _ = run_cli(proj, ["inspect-source", "--offline", "--cache-dir", str(self.repo), "--title", "Alpha Journal"])
        self.assertEqual(code, 0)
        self.assertIn("source_status: ACTIVE_LATEST", out)

    def test_run_without_key_fails_fast_with_clear_message(self):
        proj = make_project_copy(self.base, {"openalex": {"api_key": ""}})
        cache = self.base / "must_not_be_created"
        with fake_openalex() as handler:
            code, out, err = run_cli(proj, ["run", "--query", "x", "--cache-dir", str(cache), "--output", str(self.base / "o" / "x")])
            self.assertEqual(handler.calls, [])
        self.assertEqual(code, 2)
        self.assertIn("needs an OpenAlex API key", err)
        self.assertIn("config.json", err)
        self.assertFalse(cache.exists())
        self.assertFalse((self.base / "o").exists())
        proj_none = make_project_copy(self.base)
        code, _, err = run_cli(proj_none, ["run", "--query", "x", "--cache-dir", str(cache)])
        self.assertEqual(code, 2)
        self.assertIn("needs an OpenAlex API key", err)

    def test_precedence_cli_over_config_over_environment_over_default(self):
        import os
        cfg = {"openalex": {"api_key": self.FAKE_KEY, "email": "cfg@example.org"},
               "scimago": {"cache_dir": "cache/scimago"}, "run": {"from_year": 2015, "require_abstract": True}}
        proj = make_project_copy(self.base, cfg)
        os.environ["OPENALEX_API_KEY"] = "ENVKEY_SHOULD_LOSE_123"
        args, sources = self.parsed(proj, ["run", "--query", "x", "--from-year", "2018"])
        self.assertEqual((args.from_year, sources["from_year"]), (2018, "cli"))
        self.assertEqual((args.to_year, sources["to_year"]), (2026, "default"))
        self.assertEqual((args.require_abstract, sources["require_abstract"]), (True, "config.json"))
        self.assertEqual((args.cache_dir, sources["cache_dir"]), (proj / "cache" / "scimago", "config.json"))
        self.assertEqual((args.email, args.api_key, args.api_key_source), ("cfg@example.org", self.FAKE_KEY, "config.json"))
        args, _ = self.parsed(proj, ["run", "--query", "x", "--api-key", "CLIKEY_WINS_456", "--cache-dir", "elsewhere"])
        self.assertEqual((args.api_key_source, args.cache_dir), ("cli", Path("elsewhere")))
        proj_env = make_project_copy(self.base, {"openalex": {"api_key": ""}})
        args, _ = self.parsed(proj_env, ["run", "--query", "x"])
        self.assertEqual((args.api_key, args.api_key_source), ("ENVKEY_SHOULD_LOSE_123", "environment"))

    def test_run_with_config_key_end_to_end_and_key_never_written(self):
        with serve(self.repo) as (base_url, _), fake_openalex() as handler:
            self.manifest["base_url"] = base_url
            (self.repo / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")
            cfg = {"openalex": {"api_key": self.FAKE_KEY, "email": ""},
                   "scimago": {"manifest_url": base_url + "manifest.json", "cache_dir": "cache/scimago"},
                   "run": {"max_per_query": 2}}
            proj = make_project_copy(self.base, cfg)
            out_prefix = self.base / "out" / "x"
            code, out, err = run_cli(proj, ["run", "--query", "q", "--output", str(out_prefix)])
            self.assertEqual(code, 0, err)
            self.assertTrue(handler.calls)
            self.assertTrue(all(self.FAKE_KEY in c for c in handler.calls))  # the key really was sent to OpenAlex
        self.assertTrue((proj / "cache" / "scimago" / "scimagojr-2023.csv").exists())
        meta = json.loads(Path(str(out_prefix) + "_run_metadata.json").read_text(encoding="utf-8"))
        self.assertEqual((meta["openalex_api_key_configured"], meta["openalex_api_key_source"]), (True, "config.json"))
        self.assertIs(meta["openalex_api_key_stored_in_output"], False)
        self.assertNotIn("api_key_configured", meta)  # v3.0.4 names replaced, not duplicated
        self.assertEqual(meta["openalex_email"], "")  # no built-in personal default
        self.assertEqual(Path(meta["config_file"]).resolve(), (proj / "config.json").resolve())
        self.assertEqual(meta["settings_sources"]["cache_dir"], "config.json")
        self.assertEqual(meta["max_per_query"], 2)
        self.assertIn("api_key: configured (source: config.json; value not shown)".replace("api_key", "OpenAlex API key"), out)
        self.assertNotIn(self.FAKE_KEY, out + err)
        for path in (self.base / "out").iterdir():
            self.assertNotIn(self.FAKE_KEY, path.read_text(encoding="utf-8-sig"), path.name)

    def test_invalid_config_is_rejected_without_echoing_values(self):
        planted = "PLANTED_VALUE_NEVER_ECHO_55"
        cases = [
            ('{"openalex": {"api_key": "' + planted + '",}}', "invalid JSON"),
            (json.dumps({"openalex": {planted: "x"}}), "unknown key in section 'openalex'"),
            (json.dumps({planted: {}}), "unknown top-level section"),
            (json.dumps({"run": {"from_year": "2015"}}), "'run.from_year' must be an integer"),
            (json.dumps({"run": {"from_year": True}}), "'run.from_year' must be an integer"),
            (json.dumps({"openalex": {"api_key": 12345}}), "'openalex.api_key' must be a string"),
            (json.dumps([1, 2]), "top level must be a JSON object"),
        ]
        for text, expected in cases:
            proj = make_project_copy(self.base, text)
            code, out, err = run_cli(proj, ["validate-repo", "--offline", "--cache-dir", str(self.repo)])
            self.assertEqual(code, 2, expected)
            self.assertIn(expected, err)
            self.assertNotIn(planted, out + err)
        proj = make_project_copy(self.base)
        code, _, err = run_cli(proj, ["validate-repo", "--config", str(self.base / "missing.json"), "--offline"])
        self.assertEqual(code, 2)
        self.assertIn("Config file not found", err)

    def test_example_config_is_valid_and_has_no_key(self):
        from litintel.config import load_config
        example = json.loads((ROOT / "config.example.json").read_text(encoding="utf-8"))
        self.assertEqual(example["openalex"]["api_key"], "")
        proj = make_project_copy(self.base, (ROOT / "config.example.json").read_text(encoding="utf-8"))
        config = load_config(None, proj)
        self.assertEqual(config.get("openalex", "api_key"), None)
        self.assertIn("config.json", (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines())


if __name__ == "__main__":
    unittest.main()
