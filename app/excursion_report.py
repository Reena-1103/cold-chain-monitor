
import argparse
from pathlib import Path

import pandas as pd

from app.rules import detect_excursions


def generate_excursion_report(data_dir: str = "data"):
    data_path = Path(data_dir)

    required_files = [
        "sensor_readings.csv",
        "sensors.csv",
        "containers.csv",
        "shipments.csv",
        "products.csv",
        "ground_truth.csv",
    ]

    for filename in required_files:
        if not (data_path / filename).exists():
            raise FileNotFoundError(
                f"Required file not found: {data_path / filename}"
            )

    print(f"Reading dataset from: {data_path.resolve()}")

    readings = pd.read_csv(data_path / "sensor_readings.csv")
    sensors = pd.read_csv(data_path / "sensors.csv")
    containers = pd.read_csv(data_path / "containers.csv")
    shipments = pd.read_csv(data_path / "shipments.csv")
    products = pd.read_csv(data_path / "products.csv")
    ground_truth = pd.read_csv(data_path / "ground_truth.csv")

    readings["recorded_at"] = pd.to_datetime(
        readings["recorded_at"], errors="raise"
    )

    data = readings.merge(
        sensors, on="sensor_code", validate="many_to_one"
    )
    data = data.merge(
        containers, on="container_code", validate="many_to_one"
    )
    data = data.merge(
        shipments, on="shipment_code", validate="many_to_one"
    )
    data = data.merge(
        products, on="product_code", validate="many_to_one"
    )

    events = []

    for sensor_code, group in data.groupby("sensor_code", sort=False):
        group = group.sort_values("recorded_at")
        sensor_type = group["sensor_type"].iloc[0]

        if sensor_type == "TEMP":
            minimum = group["min_temperature"].iloc[0]
            maximum = group["max_temperature"].iloc[0]
        elif sensor_type == "HUMIDITY":
            minimum = group["min_humidity"].iloc[0]
            maximum = group["max_humidity"].iloc[0]
        else:
            continue

        detected_events = detect_excursions(
            [
                {
                    "recorded_at": row.recorded_at,
                    "value": row.value,
                }
                for row in group.itertuples()
            ],
            min_value=minimum,
            max_value=maximum,
            expected_interval_minutes=5,
        )

        shipment_code = group["shipment_code"].iloc[0]

        for event in detected_events:
            events.append({
                "shipment_code": shipment_code,
                "sensor_code": sensor_code,
                "sensor_type": sensor_type,
                "reason": event["reason"],
                "started_at": event["started_at"].isoformat(),
                "ended_at": event["ended_at"].isoformat(),
                "duration_minutes": event["duration_minutes"],
                "reading_count": event["reading_count"],
                "minimum_value": event["min_value"],
                "maximum_value": event["max_value"],
            })

    columns = [
        "shipment_code",
        "sensor_code",
        "sensor_type",
        "reason",
        "started_at",
        "ended_at",
        "duration_minutes",
        "reading_count",
        "minimum_value",
        "maximum_value",
    ]

    report = pd.DataFrame(events, columns=columns)

    output_file = data_path / "excursion_events.csv"
    report.to_csv(output_file, index=False)

    print(f"\nTotal sensor readings: {len(readings):,}")
    print(f"Excursion events detected: {len(report):,}")
    print(f"Report saved to: {output_file.resolve()}")

    if not report.empty:
        print("\nFirst five detected events:")
        print(report.head().to_string(index=False))

    # Compare ground-truth labels with the actual readings and detected events.
    required_truth_columns = {
        "reading_code",
        "expected_issue",
        "shipment_code",
    }

    if required_truth_columns.issubset(ground_truth.columns):
        labeled_readings = ground_truth.merge(
            readings[["reading_code", "sensor_code", "recorded_at"]],
            on="reading_code",
            how="left",
            validate="many_to_one",
        )

        matched_labels = 0
        unmatched_labels = 0

        for label in labeled_readings.itertuples():
            candidates = report[
                (report["shipment_code"] == label.shipment_code)
                & (report["sensor_code"] == label.sensor_code)
                & (report["reason"] == label.expected_issue)
            ]

            timestamp = label.recorded_at

            if pd.isna(timestamp):
                unmatched_labels += 1
                continue

            matched = False

            for event in candidates.itertuples():
                start = pd.Timestamp(event.started_at)
                end = pd.Timestamp(event.ended_at)

                if start <= timestamp <= end:
                    matched = True
                    break

            if matched:
                matched_labels += 1
            else:
                unmatched_labels += 1

        print("\n--- GROUND-TRUTH CHECK ---")
        print(f"Ground-truth labels: {len(labeled_readings):,}")
        print(f"Labels inside matching detected events: {matched_labels:,}")
        print(f"Labels not matched to detected events: {unmatched_labels:,}")

        if len(labeled_readings):
            coverage = 100 * matched_labels / len(labeled_readings)
            print(f"Ground-truth label coverage: {coverage:.2f}%")
    else:
        print(
            "\nGround-truth comparison skipped: "
            "required columns were not found."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate cold-chain excursion reports."
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Folder containing the dataset CSV files.",
    )
    args = parser.parse_args()

    generate_excursion_report(args.data_dir)
