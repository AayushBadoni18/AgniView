from agniview.firms import normalize_row


def test_normalizes_firms_csv_row():
    result = normalize_row({
        "latitude": "20.5", "longitude": "78.2", "acq_date": "2026-09-08",
        "acq_time": "1432", "satellite": "N", "instrument": "VIIRS",
        "confidence": "nominal", "frp": "12.4", "bright_ti4": "331.2",
        "scan": "0.42", "track": "0.38",
    })
    assert result["latitude"] == 20.5
    assert result["detected_at"] == "2026-09-08T14:32:00+00:00"
    assert result["identity"]
    assert result["scan"] == .42 and result["track"] == .38


def test_rejects_invalid_coordinates():
    try:
        normalize_row({"latitude": "91", "longitude": "0", "acq_date": "2026-09-08", "acq_time": "0100"})
    except ValueError as error:
        assert "coordinates" in str(error)
    else:
        raise AssertionError("invalid coordinates accepted")
