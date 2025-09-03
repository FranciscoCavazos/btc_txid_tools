#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, List

import pandas as pd
from dotenv import load_dotenv

# Allow importing helpers from src/
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str((ROOT / 'src').resolve()))
from bq_utils import get_bigquery_client, fetch_tx_timestamps  # type: ignore


def normalize_txid(x: str) -> str:
    if pd.isna(x):
        return ''
    s = str(x).strip()
    if s.lower().startswith('0x'):
        s = s[2:]
    return s.upper()


def read_spreadsheet(path: Path, sheet_name: Optional[str | int] = None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f'Input not found: {path}')
    if path.suffix.lower() == '.csv':
        return pd.read_csv(path)
    if path.suffix.lower() in ('.xlsx', '.xls'):
        return pd.read_excel(path, sheet_name=0 if sheet_name is None else sheet_name)
    raise ValueError(f'Unsupported file type: {path.suffix}')


def write_output(df: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.suffix.lower() == '.csv':
        df.to_csv(out_path, index=False)
        return
    if out_path.suffix.lower() in ('.xlsx', '.xls'):
        df.to_excel(out_path, index=False)
        return
    # Default to CSV if no recognized extension
    csv_path = out_path.with_suffix('.csv') if out_path.suffix == '' else out_path
    df.to_csv(csv_path, index=False)


def enrich_with_timestamps(
    df: pd.DataFrame,
    project_id: Optional[str],
    batch_size: int,
    timestamp_col: str = 'timestamp',
    disable_bq: bool = False,
) -> pd.DataFrame:
    if 'txid' not in df.columns:
        raise KeyError("Input must contain a 'txid' column")

    df = df.copy()
    df['txid_norm'] = df['txid'].apply(normalize_txid)
    unique_txids: List[str] = sorted(set(t for t in df['txid_norm'].tolist() if t))

    txid_to_ts: dict[str, str] = {}
    client = None
    if not disable_bq:
        try:
            client = get_bigquery_client(project_id)
            # Lightweight query to verify auth
            _ = client.query('SELECT 1').result()
            print(f'BigQuery client ready (project={project_id or client.project})')
        except Exception as e:
            print(f'BigQuery not available: {e}')
            client = None

    if unique_txids and client is not None:
        print(f'Querying timestamps for {len(unique_txids)} unique txids in batches of {batch_size}...')
        txid_to_ts = fetch_tx_timestamps(client, unique_txids, batch_size=batch_size)
        print(f'Fetched {len(txid_to_ts)} timestamps')
    else:
        if not unique_txids:
            print('No valid txids found after normalization.')
        else:
            print('Skipping BigQuery; timestamps will be blank.')

    df[timestamp_col] = df['txid_norm'].map(txid_to_ts).fillna('')
    df.drop(columns=['txid_norm'], inplace=True)
    return df


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Enrich a spreadsheet with Bitcoin txid timestamps from BigQuery.')
    p.add_argument('--input', '-i', type=Path, default=ROOT / 'data' / 'input' / 'transactions.csv', help='Input CSV/XLSX path')
    p.add_argument('--output', '-o', type=Path, default=ROOT / 'data' / 'output' / 'transactions_with_timestamps.csv', help='Output path (.csv or .xlsx)')
    p.add_argument('--sheet-name', type=str, default=None, help='Sheet name or index (for Excel). If omitted, uses first sheet')
    p.add_argument('--batch-size', type=int, default=5000, help='BigQuery batch size')
    p.add_argument('--timestamp-col', type=str, default='timestamp', help='Name of the output timestamp column')
    p.add_argument('--project-id', type=str, default=None, help='BigQuery project ID (optional; uses ADC default if not set)')
    p.add_argument('--no-bq', action='store_true', help='Disable BigQuery lookup (leave timestamp column blank)')
    return p.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()

    # Allow env var override
    project_id = args.project_id or os.getenv('BQ_PROJECT_ID')

    print(f'Reading: {args.input}')
    df = read_spreadsheet(args.input, args.sheet_name)

    enriched = enrich_with_timestamps(
        df,
        project_id=project_id,
        batch_size=args.batch_size,
        timestamp_col=args.timestamp_col,
        disable_bq=args.no_bq,
    )

    print(f'Writing: {args.output}')
    write_output(enriched, args.output)
    print('Done.')


if __name__ == '__main__':
    main()
