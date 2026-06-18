# HERALD Repository Structure

**Purpose:** orient a human reader (advisor, economist, the author) or an AI
picking up this repository cold — what each top-level folder is for, what's
safe to trust, and what to read first. Documentation only; no folder was
moved or deleted to produce this file.

---

## Read first, in this order

1. `README.md` — project overview, current state summary, dashboard link, roadmap.
2. `reports/HERALD_PROJECT_TRAJECTORY.md` — narrative evolution, April→June 2026.
3. `reports/HERALD_CURRENT_STATE.md` — detailed per-layer completion table.
4. `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` — every DEC-001→DEC-068 decision, never renumbered or deleted.
5. `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md` — classifies every report as active/historical/blocked/regenerable.

Do not start anywhere else. Do not trust a claim, number, or file path found
outside these five documents (or the ones they point to) without
cross-checking the decision log first.

Agent-local files such as `CODEX_MEMORY.md` are intentionally ignored and
not part of the public scientific repository.

---

## Active folders

| Path | What it is |
|---|---|
| `src/` | Ingestion adapters, forecast/model code, export builders, dashboard builders. Current code lives here; nothing here is auto-generated. |
| `tests/` | One suite per DEC/phase/dashboard version. Green tests gate every claim in the decision log. |
| `reports/` | Decisions, audits, evidence policy, naming conventions, architecture overview, and `reports/dashboards/` (the Observatory HTML files). This is the primary documentation tree. |
| `data/processed/herald_observatory_v04_granular/` | Clean, tested FR/PT/NL exports for the v0.4 dashboard (territory state, observed-only relation edges, blocked proxy edges kept separate). |
| `data/processed/european_panel/pt_municipal_sector_panel.csv` and sibling canonical panels | The actual input panels current builders read from. |

## Historical folders (kept for traceability, not where you start)

| Path | What it is |
|---|---|
| `docs/architecture/` | Older architecture diagrams/views (e.g. a LikeC4 model). Superseded by `reports/HERALD_ARCHITECTURE_OVERVIEW.md` as the current source — kept only as a historical reference, verify before reusing. |
| `metadata/` | Older data catalogs and dataset notes, partly superseded by `reports/herald_artifact_registry.json`. Check the registry before trusting anything here. |
| `hpc/` | SLURM batch scripts and remote-execution audits spanning both closed and still-open research phases — the folder itself is active (new jobs still get added here), but most individual scripts inside correspond to phases the decision log marks CLOSED. Check the phase name against the decision log before reusing a script. |

## Generated / heavy folders (do not start here)

| Path | What it is |
|---|---|
| `hpc_results/` | Raw outputs of HPC jobs, the large majority from closed/superseded branches (graph-temporal, P6 dual-graph, geographic-graph — all CLOSED per the decision log). Mixed git-tracked (small JSON/manifest/README) and gitignored (large npz/csv/logs) content. Never treat a file here as current evidence without first finding the DEC entry that interprets it. |
| `data/external/*/raw/` | Raw, regenerable ingestion caches (Portugal geometry, Belgium/Italy/Netherlands/Eurostat raw downloads). Gitignored. Regenerate via the corresponding `src/data/ingest_*` / `build_*` script, never edit by hand. |
| `data/processed/herald_observatory_v05_narrative/`, `data/processed/herald_observatory_v051_narrative/` | Presentation-layer exports for the narrative dashboards. Only the small checksummed `manifest.json` in each is git-tracked; the large `territory_view.json`/`.csv` payloads (tens of MB each) are gitignored and regenerable from `build_observatory_v05*_narrative_exports.py`. |
| `scripts/`, `tools/` | Small, narrow-purpose standalone utilities (audit/merge helpers, external tool wrappers). Not part of the main pipeline; not where you start. |

---

## A note on dashboards specifically

`reports/dashboards/` contains several HTML files spanning different
Observatory milestones (v0.3, v0.4, v0.4.1, v0.5, v0.5.1). Only one is
"current" at any time — check
`reports/HERALD_CURRENT_STATE.md`'s Visualization row for which one, and what
its actual decision status is (e.g. `OBSERVATORY_V051_CANDIDATE_NEEDS_MAP_REDESIGN`
is a *candidate*, not an accepted final dashboard). Older dashboard files are
kept committed for audit trail, not deleted, even after being superseded.

---

## Future cleanup (proposal only — not executed)

Documented here as a suggestion for a future, separate task — nothing below
was acted on in this consolidation:

- `hpc_results/` could be pruned to keep only the results referenced by an
  ACTIVE decision-log entry, archiving the rest outside git history (it is
  already partially gitignored, but many small tracked files from closed
  branches remain).
- `metadata/` could be merged into `reports/herald_artifact_registry.json`
  once every entry there has a corresponding registry record, then archived.
- `docs/architecture/` could be folded into `reports/HERALD_ARCHITECTURE_OVERVIEW.md`
  if the LikeC4 model is still considered worth maintaining; otherwise marked
  explicitly ARCHIVED in the active document index.

Any of the above requires an explicit decision (new DEC or charter update)
before execution — this section is not an authorization to delete or move
anything.
