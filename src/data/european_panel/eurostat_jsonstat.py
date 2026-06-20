"""Small JSON-stat decoder for Eurostat dissemination responses."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


def _codes_by_position(index: dict | list) -> list[str]:
    if isinstance(index, list):
        return [str(value) for value in index]
    return [
        str(code)
        for code, _ in sorted(index.items(), key=lambda item: int(item[1]))
    ]


def decode_jsonstat(
    payload: dict,
    dimensions: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Decode sparse JSON-stat values without assuming dimension order.

    Eurostat stores values under flattened C-order indices. ``id`` and ``size``
    define dimension order and shape; category indices map positions to codes.
    """

    ids = [str(value) for value in payload["id"]]
    sizes = [int(value) for value in payload["size"]]
    if len(ids) != len(sizes):
        raise ValueError("JSON-stat id/size length mismatch")
    requested = ids if dimensions is None else [str(value) for value in dimensions]
    unknown = sorted(set(requested) - set(ids))
    if unknown:
        raise ValueError(f"Unknown JSON-stat dimensions: {unknown}")

    codes = {
        dim: _codes_by_position(
            payload["dimension"][dim]["category"]["index"]
        )
        for dim in ids
    }
    rows = []
    for flat_index, value in payload.get("value", {}).items():
        coordinates = np.unravel_index(int(flat_index), tuple(sizes), order="C")
        row = {
            dim: codes[dim][coordinates[position]]
            for position, dim in enumerate(ids)
            if dim in requested
        }
        row["value"] = float(value)
        rows.append(row)
    return pd.DataFrame(rows, columns=requested + ["value"])
