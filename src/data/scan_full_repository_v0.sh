#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCAN_DIR="${ROOT_DIR}/scan_output"
BUNDLE_PATH="${ROOT_DIR}/scan_output_bundle.tar.gz"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3 || true)"
fi

mkdir -p "${SCAN_DIR}"

log_step() {
  local message="$1"
  local stamp
  stamp="$(date -Iseconds)"
  echo "[${stamp}] ${message}" | tee -a "${SCAN_DIR}/progress.log"
}

echo "Repository scan started at $(date -Iseconds)" > "${SCAN_DIR}/scan_run_info.txt"
echo "root_dir=${ROOT_DIR}" >> "${SCAN_DIR}/scan_run_info.txt"
: > "${SCAN_DIR}/progress.log"

cd "${ROOT_DIR}"

PRUNE_PATHS=(
  "./.git/*"
  "./.venv/*"
  "./scan_output/*"
  "./scan_output_bundle.tar.gz"
)

FIND_EXCLUDES=(
  -not -path "./.git/*"
  -not -path "./.venv/*"
  -not -path "./scan_output/*"
  -not -path "./scan_output_bundle.tar.gz"
)

log_step "step 1/8: building general file inventory"
find . -type f "${FIND_EXCLUDES[@]}" | sort > "${SCAN_DIR}/files_all.txt"
du -sh . > "${SCAN_DIR}/project_size.txt"
find . -type f "${FIND_EXCLUDES[@]}" -printf "%s\t%p\n" | sort -nr > "${SCAN_DIR}/files_by_size.tsv"

log_step "step 2/8: computing sha256 checksums"
find . -type f "${FIND_EXCLUDES[@]}" -exec sha256sum "{}" \; > "${SCAN_DIR}/sha256_all.txt"

log_step "step 3/8: collecting zip inventory"
find . -type f "${FIND_EXCLUDES[@]}" -name "*.zip" | sort > "${SCAN_DIR}/zip_files.txt"
: > "${SCAN_DIR}/zip_listing.txt"
: > "${SCAN_DIR}/zip_test.txt"
while IFS= read -r file_path; do
  log_step "zip list/test: ${file_path}"
  echo "### ${file_path}" >> "${SCAN_DIR}/zip_listing.txt"
  unzip -l "${file_path}" >> "${SCAN_DIR}/zip_listing.txt" 2>&1 || true
  echo >> "${SCAN_DIR}/zip_listing.txt"

  echo "### ${file_path}" >> "${SCAN_DIR}/zip_test.txt"
  unzip -t "${file_path}" >> "${SCAN_DIR}/zip_test.txt" 2>&1 || true
  echo >> "${SCAN_DIR}/zip_test.txt"
done < "${SCAN_DIR}/zip_files.txt"

log_step "step 4/8: previewing csv files"
find . -type f "${FIND_EXCLUDES[@]}" -name "*.csv" | sort > "${SCAN_DIR}/csv_files.txt"
: > "${SCAN_DIR}/csv_preview.txt"
while IFS= read -r file_path; do
  log_step "csv preview: ${file_path}"
  echo "### ${file_path}" >> "${SCAN_DIR}/csv_preview.txt"
  head -n 4 "${file_path}" >> "${SCAN_DIR}/csv_preview.txt" 2>&1 || true
  echo >> "${SCAN_DIR}/csv_preview.txt"
done < "${SCAN_DIR}/csv_files.txt"

if [[ -n "${PYTHON_BIN}" ]]; then
  log_step "step 5/8: reading parquet schemas"
  "${PYTHON_BIN}" - <<'PY' > "${SCAN_DIR}/parquet_schema.txt" || true
from pathlib import Path
try:
    import pandas as pd
except Exception as exc:
    print(f"ERROR: pandas import failed: {exc}")
    raise SystemExit(0)

excluded_roots = {".git", ".venv", "scan_output"}

for path in sorted(Path(".").rglob("*.parquet")):
    if any(part in excluded_roots for part in path.parts):
        continue
    print(f"### {path}")
    try:
        df = pd.read_parquet(path)
        print("rows=", len(df), "cols=", len(df.columns))
        print("columns=", list(df.columns))
    except Exception as exc:
        print("ERROR:", exc)
    print()
PY

  log_step "step 6/8: reading xlsx sheet names"
  "${PYTHON_BIN}" - <<'PY' > "${SCAN_DIR}/excel_sheets.txt" || true
from pathlib import Path
try:
    import openpyxl
except Exception as exc:
    print(f"ERROR: openpyxl import failed: {exc}")
    raise SystemExit(0)

excluded_roots = {".git", ".venv", "scan_output"}

for path in sorted(Path(".").rglob("*.xlsx")):
    if any(part in excluded_roots for part in path.parts):
        continue
    print(f"### {path}")
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        print(wb.sheetnames)
    except Exception as exc:
        print("ERROR:", exc)
    print()
PY
else
  echo "ERROR: no python interpreter available" > "${SCAN_DIR}/parquet_schema.txt"
  echo "ERROR: no python interpreter available" > "${SCAN_DIR}/excel_sheets.txt"
fi

log_step "step 7/8: searching territorial and temporal keywords"
rg -n "ZE2020|zone|commune|codgeo|codeCommune|date|annee|mois|year|month" \
  metadata reports src data -g '!**/.venv/**' > "${SCAN_DIR}/territorial_temporal_hits.txt" || true

log_step "step 8/8: creating output bundle"
tar -czf "${BUNDLE_PATH}" scan_output

echo "Repository scan finished at $(date -Iseconds)" >> "${SCAN_DIR}/scan_run_info.txt"
echo "bundle_path=${BUNDLE_PATH}" >> "${SCAN_DIR}/scan_run_info.txt"

log_step "scan complete"
echo "Output directory: ${SCAN_DIR}"
echo "Bundle: ${BUNDLE_PATH}"
