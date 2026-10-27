
# Cold Chain Monitoring System

A Python-based cold-chain monitoring project for analyzing shipment sensor readings, identifying temperature and humidity threshold violations, and reporting temperature excursion events.

## Features

- Synthetic cold-chain dataset generation
- Product-specific temperature and humidity thresholds
- Sensor reading validation
- Temperature and humidity visualizations
- Excursion event detection and reporting
- Automated unit tests
- SQLite database models

## Project Structure

- `app/` — data generation, database models, rules, validation, and reporting
- `dashboard/` — Streamlit dashboard
- `data/` — generated CSV datasets and excursion report
- `tests/` — automated tests
- `cold_chain.db` — local SQLite database

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

```powershell
python -m app.excursion_report
```

## Validate the Dataset

```powershell
python -m app.validate_data
```

## Run Tests

```powershell
python -m pytest -q
```

## Current Validation Results

The current generated dataset contains:

- 2 products
- 10 shipments
- 10 containers
- 20 sensors
- 23,592 sensor readings
- 12 ground-truth labels

The currently implemented validation checks pass, and all 5 existing tests pass.

## Limitations

These results describe the current implementation only. They do not establish that every possible cold-chain scenario or every project requirement has been implemented.
