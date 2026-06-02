"""
Minimal Eurostat dissemination API client (JSON-stat 2.0).

API docs: https://wikis.ec.europa.eu/display/EUROSTAT/API+Statistics+-+data+query
No API key required.  Raw JSON responses are cached on disk under
``data/raw/european_panel/eurostat/`` so the panel build is reproducible
offline after a first online fetch.

This module is dependency-light (stdlib urllib only) so it runs on the HPC
nodes without extra packages.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

_BASE = Path(__file__).resolve().parents[4]
RAW_DIR = _BASE / "data/raw/european_panel/eurostat"

_API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
_TIMEOUT = 60


def _cache_path(dataset: str, params: dict) -> Path:
    geo = params.get("geo", "ALL")
    key_bits = [dataset, str(geo)]
    # include the discriminating dimension codes so different indicators of the
    # same dataset (e.g. ei_bssi indic=BS-ESI-I) do not collide on disk.
    for k in sorted(params):
        if k in ("geo", "format", "lang", "sinceTimePeriod", "untilTimePeriod"):
            continue
        key_bits.append(f"{k}-{params[k]}")
    safe = "_".join(str(b).replace("/", "-") for b in key_bits)
    return RAW_DIR / f"{safe}.json"


def fetch(dataset: str, params: dict, *, use_cache: bool = True,
          refresh: bool = False) -> dict:
    """Fetch one Eurostat dataset slice as a JSON-stat dict, with disk cache."""
    cache = _cache_path(dataset, params)
    if use_cache and cache.exists() and not refresh:
        return json.loads(cache.read_text())

    query = dict(params)
    query.setdefault("format", "JSON")
    query.setdefault("lang", "EN")
    url = f"{_API}/{dataset}?" + urllib.parse.urlencode(query, doseq=True)

    req = urllib.request.Request(url, headers={"User-Agent": "HERALD-panel/1.0"})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        payload = resp.read().decode("utf-8")
    data = json.loads(payload)
    if "error" in data:
        raise RuntimeError(f"Eurostat error for {dataset} {params}: {data['error']}")

    if use_cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(payload)
    return data


def parse_time_series(data: dict) -> dict[str, float]:
    """
    Decode a JSON-stat response where ``time`` is the only multi-valued
    dimension (all other dimensions filtered to a single category).

    Returns {time_label: value}, e.g. {"2019": 5.5} or {"2019-06": 97.2}.
    NaN/suppressed cells are simply absent from the result.
    """
    dims = data["id"]               # ordered dimension names
    sizes = data["size"]            # parallel sizes
    time_pos = dims.index("time")

    # stride for the time dimension in the flattened value index
    stride = 1
    for s in sizes[time_pos + 1:]:
        stride *= s

    time_cat = data["dimension"]["time"]["category"]["index"]  # {label: idx}
    values = data["value"]          # {str(flat_idx): value}

    out: dict[str, float] = {}
    for label, t_idx in time_cat.items():
        flat = t_idx * stride
        v = values.get(str(flat))
        if v is not None:
            out[label] = float(v)
    return out
