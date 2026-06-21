## ADDED Requirements

### Requirement: Data storage layer SHALL use Parquet partitioned by symbol and date range
The storage layer SHALL store OHLCV data in Parquet files using PyArrow, with directory structure `data/ohlcv/symbol=<code>/<code>_<start>_<end>.parquet`.

#### Scenario: Store daily bars in Parquet
- **WHEN** storage receives 100 daily bars for symbol "000001.SZ"
- **THEN** storage writes a Parquet file with schema: date (date), open (float64), high (float64), low (float64), close (float64), volume (int64), amount (float64)

### Requirement: Data storage SHALL maintain a manifest for sync state
The storage layer SHALL maintain a SQLite database at `data/manifest.db` with table `sync_state(code TEXT PRIMARY KEY, last_sync_date TEXT, row_count INTEGER, created_at TEXT, updated_at TEXT)` to track incremental sync progress per symbol.

#### Scenario: Query sync state for a symbol
- **WHEN** code calls `get_sync_state("000001.SZ")`
- **THEN** storage returns a dict with keys (code, last_sync_date, row_count) or None if symbol never synced

### Requirement: Data storage SHALL update manifest after successful download
The storage layer SHALL insert or replace the sync_state row for a symbol after a successful download completes, setting last_sync_date to the maximum date in the downloaded data and row_count to total rows stored.

#### Scenario: Update manifest after download
- **WHEN** download completes storing 500 new bars for "000001.SZ" with max date 2024-06-30
- **THEN** manifest row for "000001.SZ" is upserted with last_sync_date="2024-06-30", row_count=500

### Requirement: Data storage SHALL support reading data by symbol and date range
The storage layer SHALL provide a `read_ohlcv(symbol: str, start_date: str, end_date: str) -> pd.DataFrame` function returning bars where date is within [start_date, end_date] inclusive, with date as index.

#### Scenario: Read data within date range
- **WHEN** user calls `read_ohlcv("000001.SZ", "2024-01-01", "2024-06-30")`
- **THEN** storage returns DataFrame filtered to that date range, sorted by date ascending

### Requirement: Data storage SHALL handle missing data gracefully
The storage layer SHALL return an empty DataFrame with correct schema when reading a symbol/date range with no stored data, rather than raising an exception.

#### Scenario: Read non-existent symbol returns empty DataFrame
- **WHEN** user calls `read_ohlcv("999999.SZ", "2024-01-01", "2024-06-30")`
- **THEN** storage returns empty DataFrame with columns [date, open, high, low, close, volume, amount] and date index type