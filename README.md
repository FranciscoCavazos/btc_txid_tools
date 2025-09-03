# BTC TXID Tools

Simple, focused utilities to enrich a spreadsheet that contains Bitcoin `txid` values by adding the on-chain timestamp from BigQuery.

## Structure
- notebooks/01_txid_timestamp_enrich.ipynb — main notebook to add timestamps
- src/bq_utils.py — helper to query BigQuery in batches
- data/input/ — put your spreadsheet here (CSV or XLSX)
- data/output/ — enriched outputs (CSV/XLSX)

## Quick Start
1) Copy your spreadsheet (columns: txid, from, to, amount) to `data/input/transactions.csv` (or `.xlsx`).
2) Install deps in your env: `pip install -r requirements.txt`.
3) Ensure BigQuery auth is available (e.g., `gcloud auth application-default login`).
4) Open `notebooks/01_txid_timestamp_enrich.ipynb` and run cells.

Notes:
- If BigQuery auth isn’t set up, the notebook still runs and writes an output with a blank `timestamp` column.
- You can add more on-chain fields later (e.g., block_height, fee) by extending the query in `src/bq_utils.py`.

## CLI Usage (Python)

- Install deps: `pip install -r requirements.txt`
- Example (CSV in/out):
  - `python scripts/enrich_txid_timestamps.py --input data/input/transactions.csv --output data/output/transactions_with_timestamps.csv`
- Example (Excel in/out):
  - `python scripts/enrich_txid_timestamps.py --input data/input/transactions.xlsx --output data/output/transactions_with_timestamps.xlsx --sheet-name 0`
- Disable BigQuery and just pass through (blank timestamps):
  - `python scripts/enrich_txid_timestamps.py --no-bq`
- Specify project explicitly:
  - `python scripts/enrich_txid_timestamps.py --project-id YOUR_PROJECT`

Notes:
- Only the `txid` column is required; `from`, `to`, and `amount` are preserved.
- `BQ_PROJECT_ID` in an `.env` file at project root is also supported.
