
from datetime import datetime


def check_temperature(
    temperature: float,
    min_temperature: float,
    max_temperature: float,
) -> dict:
    """Check whether temperature is within the permitted range."""

    if temperature < min_temperature:
        return {
            "is_excursion": True,
            "reason": "TEMPERATURE_TOO_LOW",
            "message": (
                f"Temperature {temperature}°C is below "
                f"the minimum of {min_temperature}°C."
            ),
        }

    if temperature > max_temperature:
        return {
            "is_excursion": True,
            "reason": "TEMPERATURE_TOO_HIGH",
            "message": (
                f"Temperature {temperature}°C is above "
                f"the maximum of {max_temperature}°C."
            ),
        }

    return {
        "is_excursion": False,
        "reason": None,
        "message": "Temperature is within the permitted range.",
    }


def check_humidity(
    humidity: float,
    min_humidity: float,
    max_humidity: float,
) -> dict:
    """Check whether humidity is within the permitted range."""

    if not 0 <= humidity <= 100:
        return {
            "is_excursion": True,
            "reason": "INVALID_HUMIDITY",
            "message": "Humidity must be between 0% and 100%.",
        }

    if humidity < min_humidity:
        return {
            "is_excursion": True,
            "reason": "HUMIDITY_TOO_LOW",
            "message": (
                f"Humidity {humidity}% is below "
                f"the minimum of {min_humidity}%."
            ),
        }

    if humidity > max_humidity:
        return {
            "is_excursion": True,
            "reason": "HUMIDITY_TOO_HIGH",
            "message": (
                f"Humidity {humidity}% is above "
                f"the maximum of {max_humidity}%."
            ),
        }

    return {
        "is_excursion": False,
        "reason": None,
        "message": "Humidity is within the permitted range.",
    }


def check_reading_gap(
    previous_time: datetime,
    current_time: datetime,
    expected_interval_minutes: int = 5,
) -> dict:
    """Detect missing readings or timestamps out of order."""

    gap_minutes = (
        current_time - previous_time
    ).total_seconds() / 60

    if gap_minutes <= 0:
        return {
            "has_gap": False,
            "reason": "OUT_OF_ORDER_TIMESTAMP",
            "gap_minutes": gap_minutes,
        }

    if gap_minutes > expected_interval_minutes:
        return {
            "has_gap": True,
            "reason": "MISSING_SENSOR_READINGS",
            "gap_minutes": gap_minutes,
        }

    return {
        "has_gap": False,
        "reason": None,
        "gap_minutes": gap_minutes,
    }


def detect_excursions(
    readings: list[dict],
    min_value: float,
    max_value: float,
    expected_interval_minutes: int = 5,
) -> list[dict]:
    """
    Group consecutive out-of-range readings into excursion events.

    Each reading must contain:
        recorded_at: datetime
        value: numeric measurement

    A gap longer than the expected interval ends the current
    event. Missing data is not treated as proof of safety.
    """

    if expected_interval_minutes <= 0:
        raise ValueError("Expected interval must be positive.")

    if min_value > max_value:
        raise ValueError("Minimum cannot exceed maximum.")

    ordered = sorted(readings, key=lambda item: item["recorded_at"])

    excursions = []
    current = None
    previous_time = None

    for reading in ordered:
        timestamp = reading["recorded_at"]
        value = float(reading["value"])

        if not isinstance(timestamp, datetime):
            raise TypeError("recorded_at must be a datetime.")

        out_of_range = value < min_value or value > max_value

        has_gap = (
            previous_time is not None
            and (timestamp - previous_time).total_seconds()
            > expected_interval_minutes * 60
        )

        if has_gap and current is not None:
            current["ended_at"] = previous_time
            current["duration_minutes"] = (
                previous_time - current["started_at"]
            ).total_seconds() / 60
            excursions.append(current)
            current = None

        if not out_of_range:
            if current is not None:
                current["ended_at"] = previous_time
                current["duration_minutes"] = (
                    previous_time - current["started_at"]
                ).total_seconds() / 60
                excursions.append(current)
                current = None
        else:
            reason = (
                "TEMPERATURE_TOO_LOW"
                if value < min_value
                else "TEMPERATURE_TOO_HIGH"
            )

            if current is None:
                current = {
                    "started_at": timestamp,
                    "ended_at": timestamp,
                    "min_value": value,
                    "max_value": value,
                    "reason": reason,
                    "reading_count": 1,
                    "duration_minutes": 0.0,
                }
            else:
                current["ended_at"] = timestamp
                current["min_value"] = min(
                    current["min_value"], value
                )
                current["max_value"] = max(
                    current["max_value"], value
                )
                current["reading_count"] += 1

        previous_time = timestamp

    if current is not None:
        current["ended_at"] = previous_time
        current["duration_minutes"] = (
            previous_time - current["started_at"]
        ).total_seconds() / 60
        excursions.append(current)

    return excursions
