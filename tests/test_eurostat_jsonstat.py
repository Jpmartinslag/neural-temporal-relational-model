from src.data.european_panel.eurostat_jsonstat import decode_jsonstat


def test_decode_respects_dimension_order() -> None:
    payload = {
        "id": ["time", "unit", "geo"],
        "size": [2, 1, 2],
        "dimension": {
            "time": {"category": {"index": {"2020": 0, "2021": 1}}},
            "unit": {"category": {"index": {"NR": 0}}},
            "geo": {"category": {"index": {"AA1": 0, "AA2": 1}}},
        },
        # C-order: (time=1, unit=0, geo=0) -> flat index 2.
        "value": {"1": 11, "2": 20},
    }

    frame = decode_jsonstat(payload)

    assert frame.to_dict(orient="records") == [
        {"time": "2020", "unit": "NR", "geo": "AA2", "value": 11.0},
        {"time": "2021", "unit": "NR", "geo": "AA1", "value": 20.0},
    ]
