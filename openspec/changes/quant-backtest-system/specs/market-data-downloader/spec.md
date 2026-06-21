## ADDED Requirements

### Requirement: Market data downloader SHALL support full data download
The system SHALL provide a function to download full historical OHLCV data for a given list of stock codes from Tushare/BaoStock API, storing results in Parquet format partitioned by symbol and date.

#### Scenario: Full download of single stock
- **WHEN** user invokes download with stock code "000001.SZ" and date range 2020-01-01 to 2024-12-31
- **THEN** system fetches all daily OHLCV bars and saves to `data/ohlcv/symbol=000001.SZ/000001.SZ_20200101_20241231.parquet`

#### Scenario: Full download with progress reporting
- **WHEN** user invokes download for multiple stocks
- **THEN** system reports progress as percentage complete and count of symbols processed

### Requirement: Market data downloader SHALL support incremental data download
The system SHALL track the last downloaded date per symbol in a manifest table and only fetch new data beyond that date on subsequent runs.

#### Scenario: Incremental download detects last sync point
- **WHEN** user runs incremental download for stock "000001.SZ" where last sync was 2024-01-01
- **THEN** system fetches only data from 2024-01-02 onwards

#### Scenario: Incremental download creates manifest entry on first run
- **WHEN** user runs incremental download for a symbol with no manifest entry
- **THEN** system performs a full download and creates manifest entry with today's date as last_sync

### Requirement: Market data downloader SHALL support multiple data sources
The system SHALL expose a unified interface that can switch between Tushare and BaoStock providers via configuration.

#### Scenario: Switch data source via config
- **WHEN** user sets `data_source: baostock` in config and requests download
- **THEN** system uses BaoStock API for data retrieval

### Requirement: Market data downloader SHALL validate downloaded data
The system SHALL verify that downloaded bars have valid fields (open > 0, high >= open, low <= open, close > 0, volume >= 0) and log warnings for invalid records without failing the entire download.

#### Scenario: Invalid bar is logged and skipped
- **WHEN** downloaded bar has high < low
- **THEN** system logs warning with symbol, date, and invalid fields and excludes bar from output

## ADDED Requirements

### Requirement: Data storage SHALL use Parquet partitioned by symbol and date range
The system SHALL store OHLCV data in Parquet files using PyArrow, with directory structure `data/ohlcv/symbol=<code>/<code>_<start>_<end>.parquet`.

#### Scenario: Store daily bars in Parquet
- **WHEN** system receives 100 daily bars for symbol "000001.SZ"
- **THEN** system writes a Parquet file with columns: date, open, high, low, close, volume, amount

### Requirement: Data storage SHALL maintain a manifest for sync state
The system SHALL store a SQLite database at `data/manifest.db` with table `sync_state(code, last_sync_date, row_count, created_at, updated_at)` to track incremental sync progress.

#### Scenario: Query sync state for a symbol
- **WHEN** code requests last sync date for "000001.SZ"
- **THEN** system returns (code, last_sync_date, row_count) or NULL if never synced

### Requirement: Data storage SHALL support reading data by date range
The system SHALL provide a `read_ohlcv(symbol, start_date, end_date)` function that returns a pandas DataFrame with date index, filtered to the specified range.

#### Scenario: Read data within date range
- **WHEN** user calls `read_ohlcv("000001.SZ", "2024-01-01", "2024-06-30")`
- **THEN** system returns DataFrame with only bars where date is within [2024-01-01, 2024-06-30]