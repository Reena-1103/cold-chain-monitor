
from datetime import datetime, timedelta

import pytest

from app.rules import (
    check_temperature,
    check_humidity,
    check_reading_gap,
    detect_excursions,
)


# Temperature tests

def test_temperature_too_high():
    result = check_temperature(10, 2, 8)
    assert result["is_excursion"] is True
    assert result["reason"] == "TEMPERATURE_TOO_HIGH"


def test_temperature_too_low():
    result = check_temperature(1, 2, 8)
    assert result["is_excursion"] is True
    assert result["reason"] == "TEMPERATURE_TOO_LOW"


def test_temperature_within_range():
    result = check_temperature(5, 2, 8)
    assert result["is_excursion"] is False


def test_temperature_at_boundaries():
    assert check_temperature(2, 2, 8)["is_excursion"] is False
    assert check_temperature(8, 2, 8)["is_excursion"] is False


# Humidity tests

def test_invalid_humidity():
    result = check_humidity(110, 20, 80)
    assert result["reason"] == "INVALID_HUMIDITY"


def test_humidity_too_low():
    result = check_humidity(10, 20, 80)
    assert result["is_excursion"] is True
    assert result["reason"] == "HUMIDITY_TOO_LOW"


def test_humidity_too_high():
    result = check_humidity(90, 20, 80)
    assert result["is_excursion"] is True
    assert result["reason"] == "HUMIDITY_TOO_HIGH"


def test_humidity_within_range():
    result = check_humidity(50, 20, 80)
    assert result["is_excursion"] is False


def test_humidity_at_boundaries():
    assert check_humidity(20, 20, 80)["is_excursion"] is False
    assert check_humidity(80, 20, 80)["is_excursion"] is False


# Missing-reading tests

def test_missing_readings():
    start = datetime(2026, 10, 27, 10, 0)
    end = start + timedelta(minutes=15)

    result = check_reading_gap(start, end)

    assert result["has_gap"] is True
    assert result["reason"] == "MISSING_SENSOR_READINGS"


def test_normal_reading_interval():
    start = datetime(2026, 10, 27, 10, 0)
    end = start + timedelta(minutes=5)

    result = check_reading_gap(start, end)

    assert result["has_gap"] is False


def test_out_of_order_timestamp():
    start = datetime(2026, 10, 27, 10, 5)
    earlier = start - timedelta(minutes=5)

    result = check_reading_gap(start, earlier)

    assert result["has_gap"] is False
    assert result["reason"] == "OUT_OF_ORDER_TIMESTAMP"


# Excursion detection tests

def test_excursion_duration():
    start = datetime(2026, 10, 27, 10, 0)

    readings = [
        {"recorded_at": start, "value": 9},
        {
            "recorded_at": start + timedelta(minutes=5),
            "value": 10,
        },
        {
            "recorded_at": start + timedelta(minutes=10),
            "value": 5,
        },
    ]

    result = detect_excursions(
        readings,
        min_value=2,
        max_value=8,
    )

    assert len(result) == 1
    assert result[0]["reading_count"] == 2
    assert result[0]["duration_minutes"] == 5
    assert result[0]["reason"] == "TEMPERATURE_TOO_HIGH"


def test_separate_excursion_events():
    start = datetime(2026, 10, 27, 10, 0)

    readings = [
        {"recorded_at": start, "value": 9},
        {
            "recorded_at": start + timedelta(minutes=5),
            "value": 5,
        },
        {
            "recorded_at": start + timedelta(minutes=10),
            "value": 10,
        },
    ]

    result = detect_excursions(
        readings,
        min_value=2,
        max_value=8,
    )

    assert len(result) == 2
    assert result[0]["reading_count"] == 1
    assert result[1]["reading_count"] == 1


def test_out_of_range_thresholds_raise_error():
    with pytest.raises(ValueError):
        detect_excursions(
            [],
            min_value=8,
            max_value=2,
        )


def test_invalid_expected_interval_raises_error():
    with pytest.raises(ValueError):
        detect_excursions(
            [],
            min_value=2,
            max_value=8,
            expected_interval_minutes=0,
        )


def test_readings_are_sorted_by_timestamp():
    start = datetime(2026, 10, 27, 10, 0)

    readings = [
        {
            "recorded_at": start + timedelta(minutes=5),
            "value": 10,
        },
        {"recorded_at": start, "value": 9},
    ]

    result = detect_excursions(
        readings,
        min_value=2,
        max_value=8,
    )

    assert len(result) == 1
    assert result[0]["reading_count"] == 2
    assert result[0]["started_at"] == start
