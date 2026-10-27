
import pandas as pd
from pathlib import Path


DATA_DIR = Path("data")


def validate_data():
    products = pd.read_csv(DATA_DIR / "products.csv")
    shipments = pd.read_csv(DATA_DIR / "shipments.csv")
    containers = pd.read_csv(DATA_DIR / "containers.csv")
    sensors = pd.read_csv(DATA_DIR / "sensors.csv")
    readings = pd.read_csv(DATA_DIR / "sensor_readings.csv")
    truth = pd.read_csv(DATA_DIR / "ground_truth.csv")

    errors = []

    # 1. Check primary-key uniqueness
    unique_checks = [
        (products, "product_code"),
        (shipments, "shipment_code"),
        (containers, "container_code"),
        (sensors, "sensor_code"),
        (readings, "reading_code"),
    ]

    for frame, column in unique_checks:
        if frame[column].isna().any():
            errors.append(f"{column} contains missing values.")

        if frame[column].duplicated().any():
            errors.append(f"{column} contains duplicate values.")

    # 2. Check foreign-key references
    if not shipments["product_code"].isin(
        products["product_code"]
    ).all():
        errors.append("Some shipments reference unknown products.")

    if not containers["shipment_code"].isin(
        shipments["shipment_code"]
    ).all():
        errors.append("Some containers reference unknown shipments.")

    if not sensors["container_code"].isin(
        containers["container_code"]
    ).all():
        errors.append("Some sensors reference unknown containers.")

    if not readings["sensor_code"].isin(
        sensors["sensor_code"]
    ).all():
        errors.append("Some readings reference unknown sensors.")

    if not truth["reading_code"].isin(
        readings["reading_code"]
    ).all():
        errors.append("Some ground-truth labels reference unknown readings.")

    # 3. Validate sensor types and measurement units
    if not sensors["sensor_type"].isin(
        ["TEMP", "HUMIDITY"]
    ).all():
        errors.append("Unexpected sensor type found.")

    reading_sensor_types = readings.merge(
        sensors[["sensor_code", "sensor_type"]],
        on="sensor_code",
        how="left",
        validate="many_to_one",
    )

    expected_units = reading_sensor_types["sensor_type"].map({
        "TEMP": "C",
        "HUMIDITY": "%RH",
    })

    if not readings["unit"].eq(expected_units).all():
        errors.append("Some readings have incorrect measurement units.")

    # 4. Check physical measurement ranges
    temperature_readings = reading_sensor_types[
        reading_sensor_types["sensor_type"] == "TEMP"
    ]

    humidity_readings = reading_sensor_types[
        reading_sensor_types["sensor_type"] == "HUMIDITY"
    ]

    if not temperature_readings["value"].between(
        -100, 100
    ).all():
        errors.append("Temperature contains physically invalid values.")

    if not humidity_readings["value"].between(
        0, 100
    ).all():
        errors.append("Humidity must be between 0 and 100.")

    # 5. Check shipment timestamps
    shipments["departure_time"] = pd.to_datetime(
        shipments["departure_time"]
    )
    shipments["delivery_time"] = pd.to_datetime(
        shipments["delivery_time"]
    )

    if not (
        shipments["delivery_time"] > shipments["departure_time"]
    ).all():
        errors.append("Some shipments have invalid delivery timestamps.")

    # 6. Check that readings fall within their shipment journeys
    reading_journeys = (
        readings
        .merge(
            sensors[["sensor_code", "container_code"]],
            on="sensor_code",
            validate="many_to_one",
        )
        .merge(
            containers[["container_code", "shipment_code"]],
            on="container_code",
            validate="many_to_one",
        )
        .merge(
            shipments[
                ["shipment_code", "departure_time", "delivery_time"]
            ],
            on="shipment_code",
            validate="many_to_one",
        )
    )

    reading_journeys["recorded_at"] = pd.to_datetime(
        reading_journeys["recorded_at"]
    )

    outside_journey = (
        (reading_journeys["recorded_at"]
         < reading_journeys["departure_time"])
        |
        (reading_journeys["recorded_at"]
         > reading_journeys["delivery_time"])
    )

    if outside_journey.any():
        errors.append("Some readings fall outside their shipment journeys.")

    # 7. Report results
    print("\n--- DATA VALIDATION REPORT ---")
    print(f"Products: {len(products)}")
    print(f"Shipments: {len(shipments)}")
    print(f"Containers: {len(containers)}")
    print(f"Sensors: {len(sensors)}")
    print(f"Sensor readings: {len(readings)}")
    print(f"Ground-truth labels: {len(truth)}")

    if errors:
        print(f"\nFAILED: {len(errors)} validation issue(s)")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("\nSUCCESS: All implemented validation checks passed.")


if __name__ == "__main__":
    validate_data()
