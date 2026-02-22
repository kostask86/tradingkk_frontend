# Tradingkk Frontend

Streamlit frontend for the TradingKK trading session manager.

## Prerequisites

- Python 3.11+
- TradingKK backend running on `http://localhost:8000`

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501` by default.

## Features

- **Sessions** — Create, start, pause, end, edit, and delete trading sessions
- Live status indicators and filtering by status/symbol
- Inline editing of session parameters (timeframe, hysteresis K, persistence window/threshold)
