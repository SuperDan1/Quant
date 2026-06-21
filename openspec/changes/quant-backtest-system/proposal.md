## Why

A quantitative trading system needs reliable historical market data and a framework to test trading strategies before deploying them live. Currently, there's no unified system to download, store, and backtest with historical data. This project provides a modular framework supporting both full and incremental data downloads alongside a flexible backtesting engine.

## What Changes

- **Data Download Module**: Support full snapshot and incremental (delta) historical data download from public market data sources (Tushare, BaoStock)
- **Data Storage Layer**: Local SQLite/Parquet storage with versioning for historical data
- **Backtesting Engine**: Event-driven backtesting framework with strategy plug-in support
- **Portfolio & Risk Analytics**: Basic performance metrics (Sharpe ratio, max drawdown, total return)
- **CLI Interface**: Unified command-line interface for data download and backtesting tasks

## Capabilities

### New Capabilities

- `market-data-downloader`: Download historical OHLCV, fundamental, and index data from Tushare/BaoStock APIs. Supports full initial download and incremental daily updates.
- `data-storage`: Local storage layer using Parquet files partitioned by symbol and date range, with manifest tracking for incremental sync state.
- `backtest-engine`: Event-driven backtesting framework that processes historical bars, executes strategy-generated signals, tracks positions, and computes performance metrics.
- `strategy-framework`: Abstract strategy class with on-bar and signal callbacks, allowing users to implement custom strategies in Python.
- `analytics-reporting`: Generate backtest reports with equity curve, trade log, and metrics (total return, Sharpe, max drawdown, win rate).

### Modified Capabilities

- (none - greenfield project)

## Impact

- New Python package structure under `src/` with modular components
- Dependencies: `tushare`, `baostock`, `pandas`, `pyarrow`, `sqlalchemy` for data; `matplotlib` for visualization
- CLI entry point via `click` or `typer`
- Configuration via YAML files for data sources and strategy parameters