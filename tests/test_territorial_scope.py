from src.data.european_panel.territorial_scope import is_in_scope


def test_continental_mainland_scope() -> None:
    included = {
        ("PT", "PT_111"),
        ("IT", "ITC11"),
        ("FR", "FR101"),
        ("ES", "ES111"),
        ("AT", "AT111"),
    }
    excluded = {
        ("PT", "PT_200"),
        ("PT", "PT_300"),
        ("IT", "ITG11"),
        ("IT", "ITG2H"),
        ("FR", "FRM01"),
        ("FR", "FRY10"),
        ("ES", "ES531"),
        ("ES", "ES703"),
    }

    assert all(is_in_scope(country, region) for country, region in included)
    assert not any(is_in_scope(country, region) for country, region in excluded)
