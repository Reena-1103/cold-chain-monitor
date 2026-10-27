
from pathlib import Path
import pandas as pd

DATA_DIR = Path("data_large_30days")
CHUNK_SIZE = 100_000


def require_columns(df, required, filename):
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(
            f"{filename} is missing columns: {sorted(missing)}"
        )


def main():
    print("\n--- LARGE DATA VALIDATION ---")

    if not DATA_DIR.exists():
        raise SystemExit(f"Data directory not found: {DATA_DIR}")

    products = pd.read_csv(DATA_DIR / "products.csv")
    shipments = pd.read_csv(DATA_DIR / "shipments.csv")
    containers = pd.read_csv(DATA_DIR / "containers.csv")
    sensors = pd.read_csv(DATA_DIR / "sensors.csv")
    truth = pd.read_csv(DATA_DIR / "ground_truth.csv")

    require_columns(
        products,
        [
            "product_code", "min_temperature", "max_temperature",
            "min_humidity", "max_humidity",
        ],
        "products.csv",
    )
    require_columns(
        shipments,
        [
            "shipment_code", "product_code", "departure_time",
            "delivery_time", "status",
        ],
        "shipments.csv",
    )
    require_columns(
        containers,
        ["container_code", "shipment_code"],
        "containers.csv",
    )
    require_columns(
        sensors,
        ["sensor_code", "container_code", "sensor_type", "calibrated"],
        "sensors.csv",
    )
    require_columns(
        truth,
        ["shipment_code", "reading_code", "expected_issue"],
        "ground_truth.csv",
    )

    errors = []

    # Check required IDs and duplicate IDs.
    for name, df, key in [
        ("products", products, "product_code"),
        ("shipments", shipments, "shipment_code"),
        ("containers", containers, "container_code"),
        ("sensors", sensors, "sensor_code"),
    ]:
        if df[key].isna().any():
            errors.append(f"{name}: missing {key}")
        if df[key].duplicated().any():
            errors.append(f"{name}: duplicate {key} values")

    # Check product-specific thresholds.
    for column in [
        "min_temperature", "max_temperature",
        "min_humidity", "max_humidity",
    ]:
        products[column] = pd.to_numeric(
            products[column], errors="coerce"
        )

    if products[
        [
            "min_temperature", "max_temperature",
            "min_humidity", "max_humidity",
        ]
    ].isna().any().any():
        errors.append("Products contain invalid threshold values.")

    if (
        products["min_temperature"] > products["max_temperature"]
    ).any():
        errors.append("Some products have invalid temperature thresholds.")

    if (
        products["min_humidity"] > products["max_humidity"]
    ).any():
        errors.append("Some products have invalid humidity thresholds.")

    if (
        (products["min_humidity"] < 0)
        | (products["max_humidity"] > 100)
    ).any():
        errors.append("Product humidity thresholds must be within 0–100%.")

    # Check foreign-key relationships.
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

    if not truth["shipment_code"].isin(
        shipments["shipment_code"]
    ).all():
        errors.append("Ground-truth labels reference unknown shipments.")

    # Check shipment status and timing.
    allowed_statuses = {"IN_TRANSIT", "DELIVERED", "CANCELLED"}
    if not shipments["status"].isin(allowed_statuses).all():
        errors.append("Unexpected shipment status values found.")

    shipments["departure_time"] = pd.to_datetime(
        shipments["departure_time"], errors="coerce"
    )
    shipments["delivery_time"] = pd.to_datetime(
        shipments["delivery_time"], errors="coerce"
    )

    if shipments[
        ["departure_time", "delivery_time"]
    ].isna().any().any():
        errors.append("Invalid shipment timestamps found.")

    valid_times = shipments.dropna(
        subset=["departure_time", "delivery_time"]
    )

    if (
        valid_times["delivery_time"] <= valid_times["departure_time"]
    ).any():
        errors.append("Some deliveries occur at or before departure.")

    # Check sensor definitions.
    if not sensors["sensor_type"].isin(["TEMP", "HUMIDITY"]).all():
        errors.append("Unexpected sensor types found.")

    sensor_codes = set(sensors["sensor_code"])
    reading_codes = set()
    reading_count = 0
    duplicate_readings = 0
    invalid_values = 0
    invalid_timestamps = 0
    invalid_units = 0
    invalid_sensor_refs = 0
    missing_reading_ids = 0
    invalid_humidity_values = 0
    reading_time_min = None
    reading_time_max = None

    # Read the large sensor file in chunks to limit memory use.
    for chunk in pd.read_csv(
        DATA_DIR / "sensor_readings.csv",
        chunksize=CHUNK_SIZE,
    ):
        require_columns(
            chunk,
            [
                "reading_code", "sensor_code",
                "recorded_at", "value", "unit",
            ],
            "sensor_readings.csv",
        )

        reading_count += len(chunk)

        missing_reading_ids += int(chunk["reading_code"].isna().sum())

        duplicate_readings += int(
            chunk["reading_code"].duplicated().sum()
        )
        duplicate_readings += sum(
            code in reading_codes
            for code in chunk["reading_code"].dropna()
        )
        reading_codes.update(chunk["reading_code"].dropna())

        invalid_sensor_refs += int(
            (~chunk["sensor_code"].isin(sensor_codes)).sum()
        )

        values = pd.to_numeric(chunk["value"], errors="coerce")

        invalid_values += int(
            (
                values.isna()
                | (values < -100)
                | (values > 100)
            ).sum()
        )

        # Humidity has the additional physical constraint 0–100%.
        humidity_rows = chunk["sensor_code"].str.endswith(
            "-HUMIDITY", na=False
        )
        invalid_humidity_values += int(
            (
                humidity_rows
                & (
                    values.isna()
                    | (values < 0)
                    | (values > 100)
                )
            ).sum()
        )

        timestamps = pd.to_datetime(
            chunk["recorded_at"], errors="coerce"
        )
        invalid_timestamps += int(timestamps.isna().sum())

        valid_timestamps = timestamps.dropna()
        if not valid_timestamps.empty:
            chunk_min = valid_timestamps.min()
            chunk_max = valid_timestamps.max()

            if reading_time_min is None or chunk_min < reading_time_min:
                reading_time_min = chunk_min
            if reading_time_max is None or chunk_max > reading_time_max:
                reading_time_max = chunk_max

        # Match units to the generator's actual conventions.
        sensor_types = chunk["sensor_code"].str.endswith(
            "-TEMP", na=False
        )
        humidity_types = chunk["sensor_code"].str.endswith(
            "-HUMIDITY", na=False
        )
        units = chunk["unit"].fillna("").astype(str).str.strip()

        correct_units = (
            (sensor_types & units.eq("C"))
            | (humidity_types & units.eq("%RH"))
        )

        invalid_units += int((~correct_units).sum())

    if missing_reading_ids:
        errors.append(
            f"Readings missing IDs: {missing_reading_ids}"
        )
    if duplicate_readings:
        errors.append(
            f"Duplicate reading codes: {duplicate_readings}"
        )
    if invalid_sensor_refs:
        errors.append(
            f"Readings with unknown sensors: {invalid_sensor_refs}"
        )
    if invalid_values:
        errors.append(
            f"Invalid sensor values outside -100 to 100 or nonnumeric: "
            f"{invalid_values}"
        )
    if invalid_humidity_values:
        errors.append(
            f"Humidity readings outside 0–100%: {invalid_humidity_values}"
        )
    if invalid_timestamps:
        errors.append(
            f"Invalid reading timestamps: {invalid_timestamps}"
        )
    if invalid_units:
        errors.append(
            f"Sensor readings with unexpected units: {invalid_units}"
        )

    # Check ground-truth reading references and duplicate labels.
    truth_reading_refs = set(truth["reading_code"].dropna())
    missing_truth_refs = truth["reading_code"].isna().sum()
    if missing_truth_refs:
        errors.append(
            f"Ground-truth rows missing reading IDs: {missing_truth_refs}"
        )

    unknown_truth_refs = truth_reading_refs - reading_codes
    if unknown_truth_refs:
        errors.append(
            f"Ground-truth labels reference unknown readings: "
            f"{len(unknown_truth_refs)}"
        )

    if truth.duplicated(
        subset=["shipment_code", "reading_code", "expected_issue"]
    ).any():
        errors.append("Duplicate ground-truth labels found.")

    # Summary.
    print(f"Products: {len(products):,}")
    print(f"Shipments: {len(shipments):,}")
    print(f"Containers: {len(containers):,}")
    print(f"Sensors: {len(sensors):,}")
    print(f"Sensor readings: {reading_count:,}")
    print(f"Ground-truth labels: {len(truth):,}")
    print(
        "Calibrated sensors: "
        f"{sensors['calibrated'].astype(str).str.lower().eq('true').sum():,}"
    )
    print(f"Duplicate reading IDs: {duplicate_readings:,}")
    print(f"Invalid reading units: {invalid_units:,}")
    print(f"Invalid humidity values: {invalid_humidity_values:,}")
    print(f"Invalid reading timestamps: {invalid_timestamps:,}")

    if reading_time_min is not None:
        print(f"Earliest reading: {reading_time_min}")
        print(f"Latest reading: {reading_time_max}")

    if errors:
        print("\nVALIDATION FAILED:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("\nSUCCESS: All implemented large-data checks passed.")
    print(
        "Note: This does not yet verify every product-specific reading "
        "threshold or the correctness of every ground-truth label."
    )


if __name__ == "__main__":
    main()
