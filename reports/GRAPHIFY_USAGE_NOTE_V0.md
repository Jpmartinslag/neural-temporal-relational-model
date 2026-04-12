# Graphify Usage Note v0

## Decision

Use graphify as a local project-context map, not as an automatic pipeline dependency.

## Current Role

- `graphify-out/GRAPH_REPORT.md` is the first place to check for architecture or codebase-orientation questions when it exists.
- `graphify-out/graph.json` can support focused graph queries.
- `src/data/build_project_context_graphify_v0.py` regenerates the low-cost context graph.

## Boundaries

- Do not scan `data/raw`, `data/interim`, or `data/processed` with graphify by default.
- Do not install graphify hooks automatically yet.
- Keep `graphify-out/` local and ignored by git.
- Regenerate the graph manually after major structural changes.

## Rationale

This gives better global context without making graphify a fragile or expensive mandatory step. Deeper integration can be reconsidered after the model/STGNN workflow is stable.
