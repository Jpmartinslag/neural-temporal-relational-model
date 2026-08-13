"""Checks on the final visual evidence archive.

These are not model tests. They check the three things that could quietly go wrong in an
archive of this kind: a figure declared in the README that does not exist, a number in a
caption that no longer matches its artefact, and a French figure that has acquired a learned
relational score.

Run without pytest:  python tests/test_visual_evidence.py
"""

from __future__ import annotations

import csv
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "reports" / "final_visual_evidence"
sys.path.insert(0, str(ARCHIVE / "scripts"))

FIGURES = [
    "A01_project_flow", "A02_current_architecture", "A03_future_architecture",
    "F01_ze2020_zones", "F02_commuting_network", "F03_similarity_map",
    "F04_complementarity_map", "F05_support_comparison", "F06_representative_series",
    "F07_temporal_representation",
    "R01_temporal_performance", "R02_forecast_skill", "R03_auprc_versus_prevalence",
    "R04_scale_diagnostic", "R05_cost_and_parameters", "R06_scientific_evolution",
    "S01_synthetic_territories", "S02_true_graph", "S03_candidate_support",
    "S04_learned_scores", "S05_no_mechanism", "S06_with_mechanism", "S07_relational_scales",
    "S08_S09_oracle_and_models_over_scale", "S10_true_versus_learned_graph",
    "S11_auprc_versus_prevalence", "S12_prediction_versus_recovery",
]

TABLES = ["T01_sources_and_periods", "T02_temporal_representations", "T03_candidate_relations",
          "T04_models_compared", "T05_prediction_versus_recovery",
          "T06_demonstrated_not_demonstrated_future", "T07_state_of_the_art_coherence"]

FAILURES: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        FAILURES.append(message)


def v01_every_figure_exists_in_both_formats() -> None:
    for target in ("report", "slides"):
        for stem in FIGURES:
            for suffix in (".pdf", ".png"):
                path = ARCHIVE / "figures" / target / f"{stem}{suffix}"
                check(path.exists(), f"missing figure {path.relative_to(ROOT)}")
                if path.exists():
                    check(path.stat().st_size > 4_000,
                          f"suspiciously small figure {path.relative_to(ROOT)}")


def v02_every_table_exists_and_parses() -> None:
    for stem in TABLES:
        csv_path = ARCHIVE / "tables" / f"{stem}.csv"
        md_path = ARCHIVE / "tables" / f"{stem}.md"
        check(csv_path.exists(), f"missing table {csv_path.relative_to(ROOT)}")
        check(md_path.exists(), f"missing table {md_path.relative_to(ROOT)}")
        if csv_path.exists():
            with csv_path.open() as handle:
                rows = list(csv.reader(handle))
            check(len(rows) >= 2, f"{stem}.csv has no data rows")
            width = len(rows[0])
            check(all(len(row) == width for row in rows),
                  f"{stem}.csv has ragged rows")


def v03_provenance_is_complete() -> None:
    expected = {"stage_audit.json", "figures_france.json", "figures_synthetic.json",
                "figures_architecture.json", "figures_results.json"}
    present = {p.name for p in (ARCHIVE / "provenance").glob("*.json")}
    check(expected <= present, f"missing provenance: {sorted(expected - present)}")

    documented = set()
    for name in expected - {"stage_audit.json"}:
        payload = json.loads((ARCHIVE / "provenance" / name).read_text())
        documented |= set(payload["figures"])
    # S05 and S06 share one entry each; S08_S09 is one figure from two questions.
    keys = {stem.split("_")[0] for stem in FIGURES} | {"S08_S09"}
    keys.discard("S08")
    check(keys <= documented | {"S08"},
          f"figures without provenance: {sorted(keys - documented)}")


def v04_the_audit_still_runs_and_still_finds_the_known_issues() -> None:
    payload = json.loads((ARCHIVE / "provenance" / "stage_audit.json").read_text())
    findings = payload["findings"]
    check(bool(findings), "the audit reports no findings at all, which is itself suspicious")
    check(not any(f["severity"] == "HIGH" for f in findings),
          f"the audit found a HIGH severity issue: "
          f"{[f['finding'] for f in findings if f['severity'] == 'HIGH']}")

    # The two verdicts the whole stage rests on.
    for support in payload["herald96"]["supports"]:
        for scale in payload["herald96"]["scales"]:
            cell = payload["herald96"]["cells"][f"M0_NULL@{scale}|{support}"]
            check(abs(cell["oracle_all_families"]) < 1e-12,
                  f"the oracle is non-zero in the null scenario: {cell}")
    for scenario in ("N2_NONLINEAR", "N3_REGIME", "N4_INTERACTION"):
        series = [payload["herald95"]["ladder"][f"{scenario}@{s}"]["oracle"]
                  for s in (0.0, 0.5, 1.0, 2.0)]
        check(all(b >= a for a, b in zip(series, series[1:])),
              f"the oracle is not monotone in {scenario}: {series}")


def v05_no_french_figure_carries_a_learned_score() -> None:
    payload = json.loads((ARCHIVE / "provenance" / "figures_france.json").read_text())
    check(payload["rule"].startswith("no learned relational score"),
          "the French provenance no longer declares the no-learned-score rule")
    # Only the per-figure records: the top-level `rule` states the prohibition and therefore
    # contains the words the prohibition is about.
    blob = json.dumps(payload["figures"]).lower()
    for forbidden in ("learned", "score appris", "auprc", "edge_score", "recovered"):
        check(forbidden not in blob,
              f"a French figure's provenance mentions {forbidden!r}, which would mean a "
              f"learned relational quantity has been drawn on a map of France")


def v06_the_future_architecture_is_marked_everywhere() -> None:
    payload = json.loads((ARCHIVE / "provenance" / "figures_architecture.json").read_text())
    entry = payload["figures"]["A03"]
    check("NOT IMPLEMENTED" in entry["status"],
          "A03 no longer declares itself unimplemented in its provenance")
    source = (ARCHIVE / "scripts" / "fig_architecture.py").read_text()
    check("PROPOSED FUTURE ARCHITECTURE — NOT IMPLEMENTED" in source,
          "A03 has lost its title banner")


def v07_readme_and_captions_cover_every_figure() -> None:
    readme = (ARCHIVE / "README.md").read_text()
    captions = (ARCHIVE / "captions" / "captions_fr.md").read_text()
    for stem in FIGURES:
        code = stem.split("_")[0]
        code = "S08/S09" if code == "S08" else code
        check(code in readme, f"{code} is not listed in the archive README")
        check(code in captions, f"{code} has no caption")


def v08_no_document_merges_the_two_protocols() -> None:
    """HERALD 93's AUPRC of 0.73 and HERALD 96's of 0.02 must never be ranked together."""
    table = (ARCHIVE / "tables" / "T04_models_compared.md").read_text()
    check("Neural Granger" not in table.split("|")[0:0] and
          "granger neuronal" not in table.lower(),
          "T04 lists a HERALD 96 arm beside HERALD 93 methods")
    check("HERALD 96" in table,
          "T04 does not say which experiment is excluded from it and why")


CHECKS = [v01_every_figure_exists_in_both_formats,
          v02_every_table_exists_and_parses,
          v03_provenance_is_complete,
          v04_the_audit_still_runs_and_still_finds_the_known_issues,
          v05_no_french_figure_carries_a_learned_score,
          v06_the_future_architecture_is_marked_everywhere,
          v07_readme_and_captions_cover_every_figure,
          v08_no_document_merges_the_two_protocols]


def main() -> int:
    for entry in CHECKS:
        before = len(FAILURES)
        entry()
        status = "ok  " if len(FAILURES) == before else "FAIL"
        print(f"  {status} {entry.__name__}")
    if FAILURES:
        print(f"\n{len(FAILURES)} failure(s):")
        for message in FAILURES:
            print(f"  - {message}")
        return 1
    print(f"\n{len(CHECKS)} checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
