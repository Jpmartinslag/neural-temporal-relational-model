"""Rebuild the whole archive: audit, tables, then every figure.

    python reports/final_visual_evidence/scripts/make_all.py

Requires only ``numpy`` and ``matplotlib``. Nothing here trains, fits or submits anything;
the heaviest operation is a deterministic draw from the synthetic generator.
"""

from __future__ import annotations

import sys
import time

import audit_stage
import fig_architecture
import fig_france
import fig_results
import fig_synthetic
import make_tables

STAGES = [("audit", audit_stage.main),
          ("tables", make_tables.main),
          ("France figures", fig_france.main),
          ("synthetic figures", fig_synthetic.main),
          ("architecture diagrams", fig_architecture.main),
          ("result figures", fig_results.main)]


def main() -> int:
    failures = []
    for name, entry in STAGES:
        start = time.time()
        try:
            entry()
            print(f"  ok  {name} ({time.time() - start:.1f}s)")
        except Exception as error:  # noqa: BLE001 - the point is to report, not to swallow
            failures.append((name, error))
            print(f"  FAIL {name}: {error!r}")
    if failures:
        print(f"\n{len(failures)} stage(s) failed")
        return 1
    print("\narchive rebuilt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
