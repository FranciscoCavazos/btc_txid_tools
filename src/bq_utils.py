from __future__ import annotations
from typing import List, Dict, Optional

try:
    from google.cloud import bigquery
except Exception:  # pragma: no cover
    bigquery = None  # type: ignore


def get_bigquery_client(project_id: Optional[str] = None):
    """Return a BigQuery client using ADC. If google-cloud-bigquery is missing, return None."""
    if bigquery is None:
        return None
    if project_id:
        return bigquery.Client(project=project_id)
    return bigquery.Client()


def fetch_tx_timestamps(
    client,
    txids: List[str],
    batch_size: int = 5000,
    *,
    location: Optional[str] = None,
    timeout: Optional[int] = None,
) -> Dict[str, str]:
    """Fetch block timestamps for txids using BigQuery public dataset.

    Returns a mapping: txid (UPPERCASE hex) -> ISO8601 UTC timestamp string.
    """
    if client is None or bigquery is None:
        return {}

    # Normalize txids once
    txids_norm = []
    for t in txids:
        if not t:
            continue
        t = str(t).strip()
        if t.lower().startswith('0x'):
            t = t[2:]
        txids_norm.append(t.upper())

    if not txids_norm:
        return {}

    # Note: `hash` is a reserved keyword; escape with backticks.
    sql = (
        """
        SELECT TO_HEX(`hash`) AS txid, block_timestamp
        FROM `bigquery-public-data.crypto_bitcoin.transactions`
        WHERE TO_HEX(`hash`) IN UNNEST(@txid_list)
        """
    )

    results: Dict[str, str] = {}
    for i in range(0, len(txids_norm), batch_size):
        batch = txids_norm[i : i + batch_size]
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("txid_list", "STRING", batch)
            ]
        )
        query_job = client.query(sql, job_config=job_config, location=location)
        rows = query_job.result(timeout=timeout) if timeout is not None else query_job.result()
        for row in rows:
            ts = row["block_timestamp"]
            results[row["txid"]] = ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)
    return results
