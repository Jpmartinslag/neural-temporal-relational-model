"""Frozen checksums for L2 artifacts used by Phase 5.

Run verify_manifest() before training. Any mismatch means the graph
source changed after the audit; retrain only from the frozen versions.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

BASE = Path(__file__).resolve().parents[3]

# Checksums frozen at commit 0b46d7b (2026-06-10)
MANIFEST: dict[str, str] = {
    "data/processed/economic_graph/sector_panel_fr_nl_pt.csv":
        "0dbe2320e05143d4bc6da2aa0b9b1a9a",
    "data/processed/economic_graph/g1_l2_cogrowth/g1_l2_validation_by_country.csv":
        "92fc17ddc6803ace6b66a9d7918996ac",
    "data/processed/economic_graph/g1_l2_cogrowth/g1_l2_decision.json":
        "2f5829aa1289540ec95b5826a901492d",
    "data/processed/economic_graph/g1_l2_cogrowth/g1_l2_validation_nocovid.csv":
        "a5437b9808979d6634dad6c256681289",
}


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_manifest(strict: bool = True) -> dict[str, bool]:
    """Check each artifact against its frozen checksum.

    Returns dict of {relative_path: ok}. Raises if strict=True and any fail.
    """
    results = {}
    failures = []
    for rel, expected in MANIFEST.items():
        p = BASE / rel
        if not p.exists():
            results[rel] = False
            failures.append(f"MISSING: {rel}")
            continue
        actual = md5(p)
        ok = actual == expected
        results[rel] = ok
        if not ok:
            failures.append(f"CHECKSUM MISMATCH: {rel}\n  expected {expected}\n  got      {actual}")
    if strict and failures:
        raise RuntimeError("L2 artifact manifest verification failed:\n" + "\n".join(failures))
    return results
