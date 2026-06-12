"""Territorial scope rules for harmonized European subpanels.

The canonical country panels keep their official national coverage. Harmonized
Path-H experiments use a separate mainland-continental scope to avoid mixing
mainland labor-market systems with islands and overseas territories. Exclusions
are declared before model evaluation and never inferred from target values.
"""

from __future__ import annotations

from collections.abc import Iterable


SCOPE_NAME = "continental_mainland"

# NUTS3 codes or prefixes excluded from the harmonized mainland panel.
# Prefix matching is intentional because NUTS revisions may change child codes.
EXCLUDED_PREFIXES = {
    "PT": ("PT20", "PT30", "PT_20", "PT_30"),  # Azores, Madeira
    "IT": ("ITG",),  # Sicily and Sardinia
    "FR": ("FRM", "FRY"),  # Corsica and French overseas territories
    "ES": ("ES53", "ES63", "ES64", "ES70"),  # Balearic, Ceuta, Melilla, Canaries
    "AT": (),
    "CZ": (),
}


def is_in_scope(country: str, region_id: str) -> bool:
    prefixes = EXCLUDED_PREFIXES.get(country.upper(), ())
    return not any(str(region_id).startswith(prefix) for prefix in prefixes)


def split_scope(
    country: str,
    region_ids: Iterable[str],
) -> tuple[list[str], list[str]]:
    included, excluded = [], []
    for region_id in sorted(set(map(str, region_ids))):
        (included if is_in_scope(country, region_id) else excluded).append(region_id)
    return included, excluded
