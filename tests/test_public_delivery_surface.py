"""Guard the public GitHub delivery surface: the entry README, the 5 canonical
`docs/*.md` documents, and the 5 top-level directory READMEs a reader is pointed to
from there.

This test does not judge scientific content. It checks four purely structural
properties of that surface, so a future edit cannot silently reintroduce a problem
this delivery branch fixed:

1. The public surface is written in English (no French/Portuguese prose).
2. No personal filesystem path (this author's home directory, or a fragment of it)
   appears in the public surface.
3. Every local file reference on the public surface -- Markdown links and
   backtick-quoted paths alike -- resolves to a real file or directory in this repo.
4. The historical internal name ("HERALD") never appears as the project's public
   name -- only as a technical identifier (a filename, a path, an `HERALD_NN`
   document id) or, in `docs/EXPERIMENT_PROVENANCE.md`, as prose explicitly
   explaining that history.

A short, explicit allowlist covers the few unavoidable exceptions (an official
French dataset title quoted verbatim, a frozen technical identifier). The allowlist
is intentionally small: if a check needs a broad or fuzzy exception to pass, that is
a sign the underlying file needs fixing, not the allowlist growing.
"""
from __future__ import annotations

import re
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]

# ── The public surface ───────────────────────────────────────────────────────────

CANONICAL_DOCS = [
    "docs/DATA_AND_PROVENANCE.md",
    "docs/EXPERIMENT_PROVENANCE.md",
    "docs/PROJECT_OVERVIEW.md",
    "docs/REPRODUCIBILITY.md",
    "docs/RESULTS_AND_LIMITATIONS.md",
]

DIRECTORY_READMES = [
    "data/README.md",
    "src/README.md",
    "hpc/README.md",
    "hpc_results/README.md",
    "reports/README.md",
]

PUBLIC_SURFACE = ["README.md", *CANONICAL_DOCS, *DIRECTORY_READMES]

# Files where "HERALD" prose (not just a technical identifier) is allowed, because
# they are the designated place to explain the project's naming history.
NAME_EXPLANATION_ALLOWED = {"docs/EXPERIMENT_PROVENANCE.md"}

# Files where the project's historical name must not appear at all, in any form --
# the purest public-identity surface (entry point + the two docs with no reason to
# ever cite an internal filename).
NAME_FREE_FILES = {
    "README.md",
    "docs/PROJECT_OVERVIEW.md",
    "docs/RESULTS_AND_LIMITATIONS.md",
}

# Personal path fragments this cleanup removed. Kept as a short, explicit list
# rather than a bare "/home/" match, so a legitimate remote-cluster "~/..." path
# (which is not this author's local filesystem) is never a false positive.
PERSONAL_PATH_FRAGMENTS = [
    "/home/jpdark",
    "/home/jpmartinsd",
    "Downloads/project_recomm",
]

# French/Portuguese stopwords common enough that their presence, as whole words,
# reliably indicates non-English prose rather than an English sentence that happens
# to contain the substring. Deliberately short and high-precision over recall: this
# guard's job is to catch a regression, not to perform translation QA.
NON_ENGLISH_STOPWORDS = re.compile(
    r"\b("
    r"le|la|les|des|une|est|pour|dans|avec|sur|entre|ainsi|aussi|donc|"
    r"não|são|para|sobre|também|então|ainda|deve|todos|foram|desta|esta|"
    r"nesta|neste|português|française?"
    r")\b",
    re.IGNORECASE,
)
# "un" (French "a/an") is deliberately excluded above: it collides too often with
# English compounds this prose actually uses (un-lettered, un-run, un-flagged...).

# A handful of official French dataset/API terms this delivery deliberately keeps
# quoted verbatim (metadata/CATALOGUE_INSEE_DATASETS.md's own stated exception).
# Lines consisting only of a table row built from these are not "prose" and are
# skipped by the language check for that one file.
OFFICIAL_FRENCH_TITLE_FILE_ALLOWLIST = {
    "metadata/CATALOGUE_INSEE_DATASETS.md",
}

# Path-shaped references that are not files in this repo: URLs, CLI flags, and a
# small set of documented placeholders/env-var patterns used in command examples.
_URL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")
_PLACEHOLDER_RE = re.compile(r"[<>{}]|\$\{|\bOUT_ROOT\b|\bRUN_ID\b|CLUSTER_(USER|HOST)")

BACKTICK_SPAN_RE = re.compile(r"`([^`]+)`")
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")

# Only strings that open with one of this repo's actual top-level entries are
# treated as "presented as a path into this repo." This is what tells a real
# reference (`src/data/foo.py`) apart from things that merely look path-shaped in
# text: a git branch name (`delivery/repository-cleanup`), or compact multi-variant
# shorthand (`train_herald_v6/v7/semi_v2/regime_experiment`).
_REPO_TOP_LEVEL = {
    p.name for p in REPO.iterdir() if not p.name.startswith(".")
}

# A backtick or link target "looks like a path" if it contains a `/` and is not a
# flag, a URL, a placeholder, or an inline shell/Python snippet.
_LOOKS_LIKE_PATH_RE = re.compile(
    r"^[A-Za-z0-9_.][A-Za-z0-9_./-]*/[A-Za-z0-9_./-]+$"
)


def _public_surface_paths() -> list[pathlib.Path]:
    return [REPO / rel for rel in PUBLIC_SURFACE]


def _iter_backtick_and_link_paths(text: str):
    for m in BACKTICK_SPAN_RE.finditer(text):
        yield m.group(1), m.start(1)
    for m in MD_LINK_RE.finditer(text):
        yield m.group(1), m.start(1)


def _candidate_repo_paths(text: str) -> set[str]:
    """Every backtick-quoted or Markdown-linked string presented as a path into this
    repo -- i.e. one that opens with a name that is actually a top-level entry here.
    That one requirement is what tells a real reference (`src/data/foo.py`) apart
    from things that only look path-shaped in prose: a git branch name
    (`delivery/repository-cleanup`), or compact multi-variant shorthand
    (`train_herald_v6/v7/semi_v2/regime_experiment`).
    """
    out = set()
    for target, _pos in _iter_backtick_and_link_paths(text):
        target = target.strip()
        if not target or _URL_RE.match(target) or _PLACEHOLDER_RE.search(target):
            continue
        # Strip a trailing markdown anchor or query-like suffix, and any leading "./".
        target = target.split("#", 1)[0].rstrip("/")
        if target.startswith("./"):
            target = target[2:]
        if not target or not _LOOKS_LIKE_PATH_RE.match(target):
            continue
        # Command-line looking content (spaces, flags) is not a single path.
        if " " in target or target.startswith("-"):
            continue
        first_segment = target.split("/", 1)[0]
        if first_segment not in _REPO_TOP_LEVEL:
            continue
        out.add(target)
    return out


_FENCE_RE = re.compile(r"^\s*```")


def _non_fenced_lines(text: str):
    """Yield (lineno, line) for every line outside a ``` ... ``` fenced block."""
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), start=1):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        yield lineno, line


# ── 1. English-only public surface ───────────────────────────────────────────────

@pytest.mark.parametrize("rel", PUBLIC_SURFACE)
def test_public_surface_file_exists(rel):
    assert (REPO / rel).is_file(), f"public surface file missing: {rel}"


@pytest.mark.parametrize("rel", PUBLIC_SURFACE)
def test_public_surface_is_english(rel):
    path = REPO / rel
    text = path.read_text(encoding="utf-8")
    skip_official_titles = rel in OFFICIAL_FRENCH_TITLE_FILE_ALLOWLIST
    offending = []
    for lineno, line in _non_fenced_lines(text):
        if skip_official_titles and ("|" in line or line.strip().startswith("#")):
            # Table rows (which carry the quoted official titles) and headings in
            # the INSEE catalogue are not free prose; skip them for this one file.
            continue
        if NON_ENGLISH_STOPWORDS.search(line):
            offending.append((lineno, line.strip()))
    assert not offending, (
        f"{rel} appears to contain non-English prose (French/Portuguese stopwords "
        f"found) on line(s): {offending[:5]}"
    )


# ── 2. No personal filesystem paths ──────────────────────────────────────────────

@pytest.mark.parametrize("rel", PUBLIC_SURFACE)
def test_public_surface_has_no_personal_paths(rel):
    text = (REPO / rel).read_text(encoding="utf-8")
    found = [frag for frag in PERSONAL_PATH_FRAGMENTS if frag in text]
    assert not found, f"{rel} contains personal path fragment(s): {found}"


# ── 3 & 5. Every local reference resolves; nothing points at a removed file ──────

# docs/EXPERIMENT_PROVENANCE.md is deliberately excluded here. Unlike the rest of the
# public surface, its job is to account for files that are intentionally *not* in
# this tree -- protected directories (Pesquisa_stage/, presentation/), the external
# reversible archive (_delivery_cleanup_archive/), and primary-worktree-only
# candidates it explicitly classifies as absent from this branch. "Does this path
# exist here" is the wrong question for most of that content; the personal-path,
# language, and name-as-technical-identifier checks still apply to it below.
REFERENCE_CHECK_SURFACE = [r for r in PUBLIC_SURFACE if r != "docs/EXPERIMENT_PROVENANCE.md"]


@pytest.mark.parametrize("rel", REFERENCE_CHECK_SURFACE)
def test_public_surface_local_references_resolve(rel):
    text = (REPO / rel).read_text(encoding="utf-8")
    doc_dir = (REPO / rel).parent
    missing = []
    for target in sorted(_candidate_repo_paths(text)):
        # Resolve relative to the referencing document's own directory first (the
        # convention most links in this repo use), falling back to repo-root.
        candidates = [doc_dir / target, REPO / target]
        if not any(c.exists() for c in candidates):
            missing.append(target)
    assert not missing, f"{rel} references path(s) that do not exist: {missing}"


# ── 4. Historical name is never the public identity ─────────────────────────────

@pytest.mark.parametrize("rel", sorted(NAME_FREE_FILES))
def test_name_free_files_never_mention_herald(rel):
    text = (REPO / rel).read_text(encoding="utf-8")
    assert "herald" not in text.lower(), (
        f"{rel} is a pure public-identity document and must never mention the "
        f"historical internal name, in any casing"
    )


@pytest.mark.parametrize("rel", [r for r in PUBLIC_SURFACE if r not in NAME_FREE_FILES])
def test_herald_only_appears_as_a_technical_identifier(rel):
    path = REPO / rel
    text = path.read_text(encoding="utf-8")
    if rel in NAME_EXPLANATION_ALLOWED:
        # This document's whole purpose is to explain the historical name; prose
        # mentions are expected and correct here, not a violation to flag.
        return

    offending_lines = []
    for lineno, line in _non_fenced_lines(text):
        if "herald" not in line.lower():
            continue
        # Every "HERALD" occurrence on this line must fall inside a backtick span
        # (a filename, path, or document id), not in running prose.
        spans = [
            (m.start(1), m.end(1)) for m in BACKTICK_SPAN_RE.finditer(line)
        ]
        for m in re.finditer(r"herald", line, re.IGNORECASE):
            if not any(start <= m.start() < end for start, end in spans):
                offending_lines.append((lineno, line.strip()))
                break
    assert not offending_lines, (
        f"{rel} uses 'HERALD' outside a backtick-quoted technical identifier "
        f"(i.e. as if it were the project's public name) on line(s): "
        f"{offending_lines[:5]}"
    )


# ── 6. The 5 canonical docs remain accessible from the entry README ─────────────

def test_canonical_docs_are_all_linked_from_readme():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    linked = {m.group(1).split("#", 1)[0] for m in MD_LINK_RE.finditer(readme)}
    missing = [doc for doc in CANONICAL_DOCS if doc not in linked and f"./{doc}" not in linked]
    assert not missing, (
        f"README.md no longer links to canonical doc(s): {missing} -- the 6-document "
        f"public reading route must stay reachable from the entry point"
    )


def test_canonical_docs_exist():
    for rel in CANONICAL_DOCS:
        assert (REPO / rel).is_file(), f"canonical doc missing: {rel}"
