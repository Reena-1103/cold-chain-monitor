
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# --------------------------------------------------
# Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="Cold Chain Monitor",
    page_icon="🌡️",
    layout="wide",
)

st.title("🌡️ Cold Chain Monitoring System")
st.caption("Shipment, sensor, and excursion monitoring dashboard")

PROJECT_DIR = Path(__file__).resolve().parent.parent

DATASETS = {
    "Small dataset (10 shipments)": PROJECT_DIR / "data",
    "Large dataset (1,000 shipments)": PROJECT_DIR / "data_large_30days",
}

CHUNK_SIZE = 100_000
MAX_CHART_ROWS = 20_000
MAX_VIOLATION_ROWS = 5_000


# --------------------------------------------------
# Dataset selector
# --------------------------------------------------

st.sidebar.header("Settings")

dataset_name = st.sidebar.selectbox(
    "Select dataset",
    list(DATASETS.keys()),
)

DATA_DIR = DATASETS[dataset_name]

st.sidebar.caption(f"Data folder: {DATA_DIR.name}")


# --------------------------------------------------
# Load metadata and process readings in chunks
# --------------------------------------------------

@st.cache_data(show_spinner="Loading and analyzing sensor data...")
def load_dashboard_data(data_dir_string):
    data_dir = Path(data_dir_string)

    products = pd.read_csv(data_dir / "products.csv")
    shipments = pd.read_csv(data_dir / "shipments.csv")
    containers = pd.read_csv(data_dir / "containers.csv")
    sensors = pd.read_csv(data_dir / "sensors.csv")
    truth = pd.read_csv(data_dir / "ground_truth.csv")

    required = {
        "products": {
            "product_code",
            "min_temperature",
            "max_temperature",
            "min_humidity",
            "max_humidity",
        },
        "shipments": {
            "shipment_code",
            "product_code",
            "departure_time",
            "delivery_time",
            "status",
        },
        "containers": {"container_code", "shipment_code"},
        "sensors": {
            "sensor_code",
            "container_code",
            "sensor_type",
        },
    }

    frames = {
        "products": products,
        "shipments": shipments,
        "containers": containers,
        "sensors": sensors,
    }

    for name, columns in required.items():
        missing = columns - set(frames[name].columns)
        if missing:
            raise ValueError(
                f"{name}.csv is missing columns: {sorted(missing)}"
            )

    sensor_details = sensors.merge(
        containers,
        on="container_code",
        how="left",
        validate="many_to_one",
    )

    sensor_details = sensor_details.merge(
        shipments,
        on="shipment_code",
        how="left",
        validate="many_to_one",
    )

    sensor_details = sensor_details.merge(
        products,
        on="product_code",
        how="left",
        validate="many_to_one",
    )

    reading_file = data_dir / "sensor_readings.csv"

    reading_count = 0
    temperature_violations = 0
    humidity_violations = 0
    chart_parts = []
    violation_parts = []

    for chunk in pd.read_csv(
        reading_file,
        chunksize=CHUNK_SIZE,
        usecols=[
            "reading_code",
            "sensor_code",
            "recorded_at",
            "value",
            "unit",
        ],
    ):
        reading_count += len(chunk)

        chunk["recorded_at"] = pd.to_datetime(
            chunk["recorded_at"], errors="coerce"
        )
        chunk["value"] = pd.to_numeric(
            chunk["value"], errors="coerce"
        )

        details = chunk.merge(
            sensor_details,
            on="sensor_code",
            how="left",
            validate="many_to_one",
        )

        temperature = details["sensor_type"].eq("TEMP")
        humidity = details["sensor_type"].eq("HUMIDITY")

        temperature_violation = temperature & (
            details["value"].lt(details["min_temperature"])
            | details["value"].gt(details["max_temperature"])
        )

        humidity_violation = humidity & (
            details["value"].lt(details["min_humidity"])
            | details["value"].gt(details["max_humidity"])
        )

        details["is_threshold_violation"] = (
            temperature_violation | humidity_violation
        )

        details["violation_reason"] = None

        details.loc[
            temperature & details["value"].lt(
                details["min_temperature"]
            ),
            "violation_reason",
        ] = "TEMPERATURE_TOO_LOW"

        details.loc[
            temperature & details["value"].gt(
                details["max_temperature"]
            ),
            "violation_reason",
        ] = "TEMPERATURE_TOO_HIGH"

        details.loc[
            humidity & details["value"].lt(
                details["min_humidity"]
            ),
            "violation_reason",
        ] = "HUMIDITY_TOO_LOW"

        details.loc[
            humidity & details["value"].gt(
                details["max_humidity"]
            ),
            "violation_reason",
        ] = "HUMIDITY_TOO_HIGH"

        temperature_violations += int(
            temperature_violation.sum()
        )
        humidity_violations += int(humidity_violation.sum())

        # Keep a bounded, evenly spaced sample from each chunk.
        sample_step = max(1, len(details) // 1000)
        chart_parts.append(details.iloc[::sample_step].copy())

        violating = details[details["is_threshold_violation"]]

        if not violating.empty:
            violation_parts.append(violating.head(1000).copy())

    chart_data = (
        pd.concat(chart_parts, ignore_index=True)
        if chart_parts
        else pd.DataFrame()
    )

    if not chart_data.empty:
        chart_data = chart_data.dropna(
            subset=["recorded_at", "value"]
        )
        chart_data = chart_data.sort_values("recorded_at")

        if len(chart_data) > MAX_CHART_ROWS:
            chart_data = chart_data.iloc[
                ::max(1, len(chart_data) // MAX_CHART_ROWS)
            ].head(MAX_CHART_ROWS)

    violation_data = (
        pd.concat(violation_parts, ignore_index=True)
        if violation_parts
        else pd.DataFrame()
    )

    if not violation_data.empty:
        violation_data = violation_data.drop_duplicates(
            subset=["reading_code"]
        ).head(MAX_VIOLATION_ROWS)

    event_file = data_dir / "excursion_events.csv"

    events = (
        pd.read_csv(event_file)
        if event_file.exists()
        else pd.DataFrame()
    )

    return {
        "products": products,
        "shipments": shipments,
        "containers": containers,
        "sensors": sensors,
        "truth": truth,
        "chart_data": chart_data,
        "violation_data": violation_data,
        "events": events,
        "reading_count": reading_count,
        "temperature_violations": temperature_violations,
        "humidity_violations": humidity_violations,
    }


# --------------------------------------------------
# Load selected dataset
# --------------------------------------------------

if not DATA_DIR.exists():
    st.error(f"Dataset folder not found: {DATA_DIR}")
    st.stop()

try:
    result = load_dashboard_data(str(DATA_DIR))
except (FileNotFoundError, ValueError, KeyError) as error:
    st.error(f"Unable to load dataset: {error}")
    st.stop()

shipments = result["shipments"]
containers = result["containers"]
sensors = result["sensors"]
truth = result["truth"]
chart_data = result["chart_data"]
violation_data = result["violation_data"]
events = result["events"]


# --------------------------------------------------
# Sidebar filters
# --------------------------------------------------

st.sidebar.header("Filters")

shipment_options = ["All"] + sorted(
    shipments["shipment_code"].dropna().unique().tolist()
)

selected_shipment = st.sidebar.selectbox(
    "Select shipment",
    shipment_options,
)

sensor_options = ["All"] + sorted(
    sensors["sensor_type"].dropna().unique().tolist()
)

selected_sensor = st.sidebar.selectbox(
    "Sensor type",
    sensor_options,
)


def apply_filters(frame):
    filtered = frame

    if not filtered.empty and selected_shipment != "All":
        filtered = filtered[
            filtered["shipment_code"] == selected_shipment
        ]

    if not filtered.empty and selected_sensor != "All":
        filtered = filtered[
            filtered["sensor_type"] == selected_sensor
        ]

    return filtered


filtered_chart = apply_filters(chart_data)
filtered_violations = apply_filters(violation_data)
filtered_events = apply_filters(events)


# --------------------------------------------------
# Summary metrics
# --------------------------------------------------

total_violations = (
    result["temperature_violations"]
    + result["humidity_violations"]
)

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Shipments", f"{len(shipments):,}")
col2.metric("Containers", f"{len(containers):,}")
col3.metric("Sensors", f"{len(sensors):,}")
col4.metric("Sensor readings", f"{result['reading_count']:,}")
col5.metric("Violating readings", f"{total_violations:,}")

st.caption(
    f"Temperature violations: "
    f"{result['temperature_violations']:,} · "
    f"Humidity violations: "
    f"{result['humidity_violations']:,}"
)

st.info(
    "Summary metrics use all readings. Charts use a sample for performance, "
    "and the violation table displays at most 5,000 rows."
)

st.divider()


# --------------------------------------------------
# Temperature and humidity charts
# --------------------------------------------------

for sensor_type, heading, unit_label in [
    ("TEMP", "🌡️ Temperature readings", "Temperature (°C)"),
    ("HUMIDITY", "💧 Humidity readings", "Humidity (%RH)"),
]:
    st.subheader(heading)

    plot_data = filtered_chart[
        filtered_chart["sensor_type"] == sensor_type
    ].copy()

    if plot_data.empty:
        st.info("No readings match the selected filters.")
    else:
        figure = px.line(
            plot_data,
            x="recorded_at",
            y="value",
            color="sensor_code",
            labels={
                "recorded_at": "Recorded at",
                "value": unit_label,
                "sensor_code": "Sensor",
            },
        )

        figure.update_layout(
            hovermode="x unified",
            legend_title_text="Sensor",
        )

        st.plotly_chart(figure, width="stretch")


# --------------------------------------------------
# Threshold violations
# --------------------------------------------------

st.subheader("🚨 Detected threshold violations")

if filtered_violations.empty:
    st.success("No displayed violations match these filters.")
else:
    columns = [
        "shipment_code",
        "sensor_code",
        "sensor_type",
        "recorded_at",
        "value",
        "unit",
        "violation_reason",
    ]

    st.dataframe(
        filtered_violations[columns].sort_values("recorded_at"),
        width="stretch",
        hide_index=True,
    )

    st.caption(
        "The table is a sample capped at 5,000 rows. "
        "The total violation metric counts all readings."
    )


# --------------------------------------------------
# Excursion events
# --------------------------------------------------

st.subheader("⏱️ Excursion Events")

if events.empty:
    st.warning(
        "Excursion report not found. Generate it with: "
        "`python -m app.excursion_report --data-dir "
        + DATA_DIR.name
        + "`"
    )
else:
    event_col1, event_col2 = st.columns(2)

    event_col1.metric(
        "Filtered excursion events",
        f"{len(filtered_events):,}",
    )

    if not filtered_events.empty:
        duration = pd.to_numeric(
            filtered_events["duration_minutes"],
            errors="coerce",
        ).fillna(0).sum()
    else:
        duration = 0

    event_col2.metric(
        "Total estimated duration",
        f"{duration:,.0f} minutes",
    )

    if filtered_events.empty:
        st.info("No events match the selected filters.")
    else:
        st.dataframe(
            filtered_events.sort_values(
                "started_at", ascending=False
            ),
            width="stretch",
            hide_index=True,
        )

    st.caption(
        "Durations are estimates from sampled readings. "
        "Missing data does not establish that conditions were safe."
    )


# --------------------------------------------------
# Shipment overview and ground truth
# --------------------------------------------------

st.subheader("🚚 Shipment overview")

shipment_overview = shipments

if selected_shipment != "All":
    shipment_overview = shipments[
        shipments["shipment_code"] == selected_shipment
    ]

st.dataframe(
    shipment_overview,
    width="stretch",
    hide_index=True,
)

with st.expander("View synthetic ground-truth labels"):
    st.caption(
        "Synthetic evaluation labels are separate from monitoring inputs."
    )
    st.dataframe(truth, width="stretch", hide_index=True)
