# Cold Chain Monitoring System

- `app/` - data generation, database models, rules, validation, and reporting
- `dashboard/` - Streamlit dashboard

## Features

- Synthetic cold-chain dataset generation
- Product-specific temperature and humidity thresholds
- Sensor reading validation
- Temperature and humidity visualizations
- Excursion event detection and CSV reporting
- Automated unit tests
- SQLite database models
- Streamlit dashboard for exploring shipment data

## Project Structure

- `app/` — data generation, database models, rules, validation, and reporting
- `dashboard/` — Streamlit dashboard
- `tests/` — automated unit tests
- `requirements.txt` — Python dependencies
- `README.md` — project documentation

Generated datasets, database files, and reports are created locally and are not required to be committed to the repository.

## Setup

Python 3.10 or newer is recommended.

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Run the Dashboard

```powershell
streamlit run dashboard/app.py
```

## Generate the Excursion Report

For the large dataset:

```powershell
python -m app.excursion_report --data-dir data_large_30days
```

## Validate the Dataset

Run the large-dataset validation script:

```powershell
python -m app.validate_large_data
```

## Run Tests

```powershell
python -m pytest -v
```

## Latest Large-Dataset Validation

The latest recorded large-dataset validation reported:

- Products: 2
- Shipments: 1,000
- Containers: 1,000
- Sensors: 2,000
- Sensor readings: 1,983,168
- Ground-truth labels: 1,500
- Calibrated sensors: 2,000
- Duplicate reading IDs: 0
- Invalid reading units: 0
- Invalid humidity values: 0
- Invalid timestamps: 0

The latest recorded unit-test run passed all 17 tests.

The excursion report recorded 250 events, with all 1,500 ground-truth labels matching an event. This coverage result does not, by itself, establish overall detection precision or recall.

## Limitations

Validation results describe the tested datasets and implemented checks. They do not establish that every possible cold-chain scenario or every project requirement has been implemented.
