"""Shared style, palette and artefact loaders for the HERALD final visual evidence archive.

Nothing here fits, trains or samples a model. Every number a figure draws comes either from a
committed result artefact under ``hpc_results/`` or from a deterministic call to the synthetic
generator, which is a data-generating process and not an estimator.

Dependencies are deliberately minimal: ``numpy`` and ``matplotlib``. The French geometry is
read from GeoJSON with the standard library and drawn as polygons, so that no geospatial stack
is required to reproduce a single figure.
"""

from __future__ import annotations

import json
import os
import pathlib
import statistics
from collections import defaultdict
from typing import Any, Iterable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
ARCHIVE = ROOT / "reports" / "final_visual_evidence"
RESULTS = ROOT / "hpc_results"
DATA = ROOT / "data"

FIG_REPORT = ARCHIVE / "figures" / "report"
FIG_SLIDES = ARCHIVE / "figures" / "slides"
TABLES = ARCHIVE / "tables"
PROVENANCE = ARCHIVE / "provenance"


# ── palette ──────────────────────────────────────────────────────────────────
#
# Okabe–Ito, which is distinguishable under deuteranopia, protanopia and tritanopia. Roles are
# fixed once here and used by every figure so that a colour means the same thing throughout the
# report and the slides.

PALETTE = {
    "commuting": "#0072B2",          # blue
    "similarity": "#E69F00",         # orange
    "complementarity": "#009E73",    # bluish green
    "union": "#56B4E9",              # sky blue
    "true_graph": "#111111",         # near-black
    "learned_graph": "#CC79A7",      # reddish purple
    "null": "#9A9A9A",               # grey
    "herald": "#D55E00",             # vermillion
    "classical": "#56B4E9",          # sky blue
    "other_neural": "#7B5EA7",       # purple
    "oracle": "#111111",             # near-black, same as truth: both know the answer
    "prevalence": "#9A9A9A",
    "grid": "#D8D8D8",
    "land": "#F2F2F2",
    "land_edge": "#BFBFBF",
    "text": "#1A1A1A",
    "warning": "#B22222",
}

FAMILY_ORDER = ("commuting", "similarity", "complementarity")

METHOD_COLOUR = {
    "persistence": PALETTE["null"],
    "sparse_var": PALETTE["classical"],
    "granger": PALETTE["classical"],
    "mtgnn": PALETTE["other_neural"],
    "nri": PALETTE["other_neural"],
    "herald": PALETTE["herald"],
    "oracle": PALETTE["oracle"],
    "neural_granger": PALETTE["learned_graph"],
}


def method_colour(name: str) -> str:
    key = name.split("@")[0].strip().lower()
    return METHOD_COLOUR.get(key, PALETTE["null"])


# ── style ────────────────────────────────────────────────────────────────────

def target() -> str:
    """``report`` or ``slides``. Set ``HERALD_FIG_TARGET=slides`` to render the slide set.

    The two sets are the same figures at different typography, written to different
    directories, so a redeploy of one never silently overwrites the other.
    """
    return os.environ.get("HERALD_FIG_TARGET", "report").strip().lower()


def use_style(scale: str | None = None) -> None:
    """Apply the archive's typography. ``slides`` is the same design at a larger size."""
    scale = scale or target()
    base = 13 if scale == "report" else 17
    plt.rcParams.update({
        "figure.dpi": 120,
        # 140 dpi over figures 7–20 inches wide is 1000–2700 px: enough for a projector and
        # for a screen, and small enough that the archive stays committable. The PDF beside
        # each PNG is vector and is the format to use in print.
        "savefig.dpi": 140,
        "savefig.bbox": "tight",
        "font.size": base,
        "axes.titlesize": base + 3,
        "axes.labelsize": base + 1,
        "xtick.labelsize": base - 1,
        "ytick.labelsize": base - 1,
        "legend.fontsize": base - 1,
        "axes.titleweight": "bold",
        "axes.edgecolor": "#666666",
        "axes.linewidth": 0.9,
        "axes.grid": True,
        "grid.color": PALETTE["grid"],
        "grid.linewidth": 0.7,
        "axes.axisbelow": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "text.color": PALETTE["text"],
        "axes.labelcolor": PALETTE["text"],
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "legend.frameon": False,
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
    })


def save(fig, stem: str) -> list[pathlib.Path]:
    """Write one figure as vector PDF and raster PNG, into the directory for this target."""
    directory = FIG_SLIDES if target() == "slides" else FIG_REPORT
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for suffix in (".pdf", ".png"):
        path = directory / f"{stem}{suffix}"
        fig.savefig(path)
        written.append(path)
    plt.close(fig)
    return written


def footnote(fig, text: str, width: int = 110) -> None:
    """Every figure carries its source, period and population in the figure itself.

    The text is hard-wrapped rather than left to run off the canvas, because ``bbox_inches=
    'tight'`` would otherwise widen the saved figure to fit a single long line.
    """
    import textwrap
    lines = []
    for paragraph in text.split("\n"):
        lines.extend(textwrap.wrap(paragraph, width=width) or [""])
    fig.text(0.0, -0.015, "\n".join(lines), fontsize=8.5, color="#555555",
             ha="left", va="top")


def stamp(fig_or_ax, text: str, colour: str | None = None) -> None:
    """A category stamp — REAL_FRANCE, SYNTHETIC_KNOWN_TRUTH, EXPLORATORY, FUTURE_WORK.

    Drawn against the figure, above and right of everything, so that it can never collide
    with a title.
    """
    fig = getattr(fig_or_ax, "figure", fig_or_ax)
    fig.text(1.0, 1.0, text, ha="right", va="bottom", fontsize=8.5,
             color=colour or "#666666", fontweight="bold",
             bbox=dict(boxstyle="round,pad=0.28", facecolor="#FFFFFF",
                       edgecolor=colour or "#BBBBBB", linewidth=0.8))


# ── result artefacts ─────────────────────────────────────────────────────────

def _load_dir(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} is missing. The HERALD 94/95/96 task artefacts are mirrored into "
            f"hpc_results/ by the stage-closure commit; see the archive README.")
    return [json.loads(p.read_text()) for p in sorted(path.glob("*.json"))]


def herald94_tasks() -> list[dict[str, Any]]:
    return _load_dir(RESULTS / "herald94" / "tasks")


def herald95_tasks() -> list[dict[str, Any]]:
    return _load_dir(RESULTS / "herald95" / "tasks")


def herald96_tasks() -> list[dict[str, Any]]:
    return _load_dir(RESULTS / "herald96" / "tasks")


def herald93_summary() -> dict[str, Any]:
    path = RESULTS / "herald93" / "benchmark_summary_v2.json"
    return json.loads(path.read_text())


def group(tasks: Iterable[dict[str, Any]], *keys: str) -> dict[tuple, list[dict[str, Any]]]:
    out: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for task in tasks:
        out[tuple(task[k] for k in keys)].append(task)
    return dict(out)


def median(values: Iterable[float]) -> float:
    values = [v for v in values if v is not None and not (isinstance(v, float) and np.isnan(v))]
    return float(statistics.median(values)) if values else float("nan")


# ── French artefacts ─────────────────────────────────────────────────────────

def ze2020_geometry() -> dict[str, dict[str, Any]]:
    """{ze2020: {label, rings, centroid}} for every zone in the published geometry."""
    raw = json.loads((DATA / "external" / "ze2020_geometry.geojson").read_text())
    out: dict[str, dict[str, Any]] = {}
    for feature in raw["features"]:
        code = str(feature["properties"]["ze2020"]).zfill(4)
        geometry = feature["geometry"]
        polygons = ([geometry["coordinates"]] if geometry["type"] == "Polygon"
                    else geometry["coordinates"])
        rings = [np.asarray(polygon[0], dtype=float) for polygon in polygons]
        biggest = max(rings, key=lambda r: len(r))
        out[code] = {"label": feature["properties"].get("libze2020", code),
                     "rings": rings,
                     "centroid": biggest.mean(axis=0)}
    return out


def mainland_zones() -> list[str]:
    """The 280 mainland ZE2020 the whole study uses. Read from the panel, never hard-coded."""
    import csv
    path = DATA / "processed" / "france_ze2020" / "fr_ze2020_clean_panel.csv"
    with path.open() as handle:
        zones = {str(row["ze2020"]).zfill(4) for row in csv.DictReader(handle)}
    return sorted(zones)


def commuting_edges(year: int = 2012) -> list[tuple[str, str, float]]:
    """Observed residence-to-work flows between distinct zones, one vintage. A prior, never a
    label: no result in this project is scored against it."""
    import csv
    import gzip
    path = DATA / "processed" / "france_ze2020" / "fr_ze2020_commuting_edges.csv.gz"
    keep = set(mainland_zones())
    edges: list[tuple[str, str, float]] = []
    with gzip.open(path, "rt") as handle:
        for row in csv.DictReader(handle):
            if int(row["observation_year"]) != year or row["is_self_loop"] == "1":
                continue
            source = str(row["source_ze2020"]).zfill(4)
            target = str(row["target_ze2020"]).zfill(4)
            if source in keep and target in keep:
                edges.append((source, target, float(row["commuter_count"])))
    return edges


def multisource_series() -> dict[str, dict[str, Any]]:
    """The five French signals as annual series per zone, with their availability window."""
    import csv
    wanted = {
        "urssaf_private_headcount_annual_mean": ("headcount", "Effectifs salariés privés",
                                                 "Urssaf", "salariés"),
        "urssaf_private_payroll_annual": ("payroll", "Masse salariale privée",
                                          "Urssaf", "€"),
        "urssaf_employer_establishments": ("establishments", "Établissements employeurs",
                                           "Urssaf", "établissements"),
        "local_unemployment_rate_annual_mean": ("unemployment", "Taux de chômage localisé",
                                                "Insee", "%"),
        "establishment_creations": ("creations", "Créations d'établissements",
                                    "Sirene / SIDE", "créations"),
    }
    path = DATA / "processed" / "france_ze2020" / "fr_ze2020_multisource_long_panel_v1.csv"
    out: dict[str, dict[str, Any]] = {
        key: {"label": label, "source": source, "unit": unit, "series": defaultdict(dict)}
        for key, label, source, unit in wanted.values()}
    with path.open() as handle:
        for row in csv.DictReader(handle):
            spec = wanted.get(row["measure"])
            if spec is None or row["availability_mask"] != "1" or not row["value"]:
                continue
            key = spec[0]
            zone = str(row["ze2020"]).zfill(4)
            # The sectoral rows share a measure name; sum them into the zone total.
            year = int(row["year"])
            current = out[key]["series"][zone].get(year, 0.0)
            out[key]["series"][zone][year] = current + float(row["value"])
    for entry in out.values():
        entry["series"] = {zone: dict(sorted(years.items()))
                           for zone, years in entry["series"].items()}
    return out


# ── synthetic world ──────────────────────────────────────────────────────────

def synthetic_world(*, n_zones: int = 80, seed: int = 9961,
                    scenario: str = "M1_MULTIRELATIONAL",
                    relational_scale: float = 1.0) -> dict[str, Any]:
    """A deterministic draw from the HERALD 96 generator. Generation, never estimation."""
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from src.data.synthetic.generate_multirelational_v96 import (
        MultirelationalConfig, generate_multirelational)
    return generate_multirelational(MultirelationalConfig(
        n_zones=n_zones, seed=seed, scenario=scenario, relational_scale=relational_scale))


# ── provenance ───────────────────────────────────────────────────────────────

def write_provenance(name: str, payload: dict[str, Any]) -> pathlib.Path:
    PROVENANCE.mkdir(parents=True, exist_ok=True)
    path = PROVENANCE / name
    path.write_text(json.dumps(payload, indent=1, sort_keys=True, default=str) + "\n")
    return path


def write_table(stem: str, header: list[str], rows: list[list[Any]],
                title: str, note: str) -> list[pathlib.Path]:
    """Every table is written twice: CSV for machines, Markdown for the report."""
    TABLES.mkdir(parents=True, exist_ok=True)
    import csv as _csv
    csv_path = TABLES / f"{stem}.csv"
    with csv_path.open("w", newline="") as handle:
        writer = _csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    md_path = TABLES / f"{stem}.md"
    lines = [f"# {title}", "", note, "",
             "| " + " | ".join(header) + " |",
             "|" + "|".join(["---"] * len(header)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    md_path.write_text("\n".join(lines) + "\n")
    return [csv_path, md_path]
