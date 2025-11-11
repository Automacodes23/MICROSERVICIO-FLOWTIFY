from app.integrations.wialon.parser import (
    normalize_wialon_event,
    parse_wialon_event,
)


def test_parse_wialon_event_with_speed_units():
    body = (
        "unit_name=Unidad+1&unit_id=12345&latitude=21.1398&longitude=-101.6847"
        "&speed=4%20km%2Fh&geofence_name=RUTA&event_time=1762896339"
    )

    parsed = parse_wialon_event(body, content_type="application/x-www-form-urlencoded")

    assert parsed["speed"] == 4
    assert parsed["latitude"] == 21.1398
    assert parsed["longitude"] == -101.6847

    normalized = normalize_wialon_event(parsed)
    assert normalized["speed"] == 4.0


def test_parse_wialon_event_sanitizes_placeholders():
    body = "geofence_name=%25ZONE%25&speed=0%20km%2Fh&event_time=1762896505"

    parsed = parse_wialon_event(body, content_type="application/x-www-form-urlencoded")
    assert parsed["geofence_name"] == "%ZONE%"
    assert parsed["speed"] == 0

    normalized = normalize_wialon_event(parsed)
    assert normalized["geofence_name"] is None
    assert normalized["speed"] == 0.0

