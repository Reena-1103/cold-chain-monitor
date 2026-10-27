
import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


def generate_data(
    shipment_count: int = 10,
    seed: int = 20261022,
    output_dir: str = "data",
    departure_window_days: int = 30,
):
    if shipment_count < 1:
        raise ValueError("shipment_count must be at least 1")

    if departure_window_days < 1:
        raise ValueError("departure_window_days must be at least 1")

    rng = random.Random(seed)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    products = [
        {
            "product_code": "PRD-000001",
            "name": "Chilled Medicine",
            "min_temperature": 2.0,
            "max_temperature": 8.0,
            "min_humidity": 20.0,
            "max_humidity": 80.0,
        },
        {
            "product_code": "PRD-000002",
            "name": "Frozen Food",
            "min_temperature": -25.0,
            "max_temperature": -15.0,
            "min_humidity": 20.0,
            "max_humidity": 85.0,
        },
    ]

    shipments = []
    containers = []
    sensors = []
    readings = []
    ground_truth = []

    base_time = datetime(2026, 10, 1, 8, 0)

    for index in range(1, shipment_count + 1):
        shipment_code = f"SHP-2026-{index:06d}"
        container_code = f"CNT-{index:06d}"
        product = products[(index - 1) % len(products)]

        # Spread departure dates over the requested window.
        departure_day = (
            (index - 1) * departure_window_days
        ) // shipment_count
        departure = base_time + timedelta(days=departure_day)

        duration_days = rng.randint(2, 5)
        delivery = departure + timedelta(days=duration_days)

        shipments.append({
            "shipment_code": shipment_code,
            "product_code": product["product_code"],
            "departure_time": departure.isoformat(),
            "delivery_time": delivery.isoformat(),
            "status": "DELIVERED",
        })

        containers.append({
            "container_code": container_code,
            "shipment_code": shipment_code,
        })

        shipment_has_excursion = index % 4 == 0
        shipment_has_dropout = index % 5 == 0

        for sensor_type in ("TEMP", "HUMIDITY"):
            sensor_code = f"SNS-{container_code}-{sensor_type}"

            sensors.append({
                "sensor_code": sensor_code,
                "container_code": container_code,
                "sensor_type": sensor_type,
                "calibrated": "true",
            })

            current_time = departure
            reading_index = 0

            while current_time <= delivery:
                reading_index += 1

                # Skip one expected reading to simulate a sensor dropout.
                if shipment_has_dropout and reading_index % 100 == 0:
                    current_time += timedelta(minutes=5)
                    continue

                if sensor_type == "TEMP":
                    value = rng.uniform(
                        product["min_temperature"] + 0.5,
                        product["max_temperature"] - 0.5,
                    )

                    # Inject six consecutive high-temperature readings.
                    if (
                        shipment_has_excursion
                        and 50 <= reading_index < 56
                    ):
                        value = product["max_temperature"] + 3.0

                    unit = "C"

                else:
                    value = rng.uniform(
                        product["min_humidity"] + 2,
                        product["max_humidity"] - 2,
                    )
                    unit = "%RH"

                reading_code = (
                    f"RDG-{sensor_code}-"
                    f"{current_time.strftime('%Y%m%d%H%M')}"
                )

                readings.append({
                    "reading_code": reading_code,
                    "sensor_code": sensor_code,
                    "recorded_at": current_time.isoformat(),
                    "value": round(value, 2),
                    "unit": unit,
                })

                if (
                    sensor_type == "TEMP"
                    and shipment_has_excursion
                    and 50 <= reading_index < 56
                ):
                    ground_truth.append({
                        "shipment_code": shipment_code,
                        "reading_code": reading_code,
                        "expected_issue": "TEMPERATURE_TOO_HIGH",
                    })

                current_time += timedelta(minutes=5)

    write_csv(output_path / "products.csv", products)
    write_csv(output_path / "shipments.csv", shipments)
    write_csv(output_path / "containers.csv", containers)
    write_csv(output_path / "sensors.csv", sensors)
    write_csv(output_path / "sensor_readings.csv", readings)
    write_csv(output_path / "ground_truth.csv", ground_truth)

    print(f"Generated {shipment_count} shipments.")
    print(f"Generated {len(readings)} sensor readings.")
    print(f"Generated {len(ground_truth)} ground-truth labels.")
    print(f"Departure window: {departure_window_days} days.")
    print(f"Output directory: {output_path.resolve()}")


def write_csv(file_path: Path, rows: list[dict]):
    if not rows:
        file_path.write_text("", encoding="utf-8")
        return

    with file_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate synthetic cold-chain monitoring data."
    )
    parser.add_argument("--shipments", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20261022)
    parser.add_argument("--output-dir", default="data")
    parser.add_argument("--departure-window-days", type=int, default=30)

    args = parser.parse_args()

    if args.shipments < 1:
        parser.error("--shipments must be at least 1")

    if args.departure_window_days < 1:
        parser.error("--departure-window-days must be at least 1")

    generate_data(
        shipment_count=args.shipments,
        seed=args.seed,
        output_dir=args.output_dir,
        departure_window_days=args.departure_window_days,
    )
