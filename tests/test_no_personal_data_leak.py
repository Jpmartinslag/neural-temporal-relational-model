"""Repository-wide guard against accidental personal/infrastructure leakage.

Unlike `tests/test_public_delivery_surface.py` (scoped to the 11-file public
navigation surface), this test scans every tracked, text-readable file in the whole
repository -- because a personal path, username, or hostname can leak into a data
file, a job script, or a committed log just as easily as into a README, and a
2026-08-25 privacy/security audit found two such leaks outside the navigation
surface: a bare cluster username in `hpc/HPC_PHASE_INDEX.md` and a local laptop
hostname inside a committed smoke-test JSON artifact under `hpc_results/`. Both were
fixed; this test exists so neither pattern, or one like it, can reappear silently.

This is a leak-*regression* guard, not a full privacy audit -- it checks a short,
explicit list of concrete strings confirmed sensitive by that audit, not a general
heuristic. A short list here is a feature, not a gap: broadening it to something
fuzzy would risk false positives on legitimate content (institutional cluster names
mentioned generically, other researchers' names in the bibliography, etc.) and this
test's whole job is to catch a *reintroduction* of a known-bad string, not to
perform the audit itself.
"""
from __future__ import annotations

import pathlib
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]

# Extensions not worth reading as text (binary, or handled by a separate metadata
# audit rather than a text search).
_BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".npz", ".pt", ".gz", ".xlsx",
    ".docx", ".pptx", ".zip", ".ico", ".woff", ".woff2", ".ttf", ".eot",
}

# This file itself legitimately contains every fragment below, as the detection
# pattern -- exclude it from its own scan.
_SELF = "tests/test_no_personal_data_leak.py"
# The other guard's fragment list is likewise data, not a leak.
_OTHER_GUARD = "tests/test_public_delivery_surface.py"

# Confirmed-sensitive strings from the 2026-08-25 privacy/security audit. Each entry
# is a (fragment, human description) pair used to build a clear failure message.
KNOWN_SENSITIVE_FRAGMENTS = [
    ("/home/jpdark", "the author's local home directory"),
    ("/home/jpmartinsd", "the author's cluster account home directory"),
    ("Downloads/project_recomm", "the author's local project folder name"),
    ("jpdark-Legion", "the author's local laptop hostname"),
    ("hpc2.mesocentre.uca.fr", "the cluster's real fully-qualified hostname"),
    # A bare cluster username, checked as a whole word so it doesn't collide with
    # the fragments above (which already cover its path forms).
    ("jpmartinsd", "the author's cluster account username, unqualified"),
]


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    )
    return [line for line in out.stdout.splitlines() if line]


def _is_scannable(rel: str) -> bool:
    if rel in (_SELF, _OTHER_GUARD):
        return False
    return pathlib.Path(rel).suffix.lower() not in _BINARY_EXTENSIONS


@pytest.mark.parametrize("fragment,description", KNOWN_SENSITIVE_FRAGMENTS)
def test_known_sensitive_fragment_does_not_reappear(fragment, description):
    offenders = []
    for rel in _tracked_files():
        if not _is_scannable(rel):
            continue
        path = REPO / rel
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, IsADirectoryError):
            continue
        if fragment in text:
            offenders.append(rel)
    assert not offenders, (
        f"'{fragment}' ({description}) reappeared in tracked file(s): {offenders}. "
        f"This string was removed from the tracked tree in the 2026-08-25 "
        f"privacy/security audit; if it is back, something reintroduced it."
    )
