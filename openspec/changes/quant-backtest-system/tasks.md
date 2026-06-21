## 1. Project Setup

- [ ] 1.1 Create `src/newquant/` package directory with `__init__.py`
- [ ] 1.2 Create `src/newquant/py.typed` marker for type checking support
- [ ] 1.3 Add `pyproject.toml` with dependencies: `pandas`, `pyarrow`, `sqlalchemy`, `click`, `tushare`, `baostock`, `matplotlib`, `pytest`
- [ ] 1.4 Create `config.yaml` template with `data_source`, `tushare_token`, `data_dir`, `commission_rate` fields
- [ ] 1.5 Create `src/newquant/config.py` to load and validate `config.yaml`

## 2. Data Storage Layer

- [ ] 2.1 Create `src/newquant/storage/__init__.py` with public API exports
- [ ] 2.2 Create `src/newquant/storage/manifest.py` with `SyncState` dataclass and `ManifestDB` class (SQLite)
- [ ] 2.3 Create `src/newquant/storage/parquet_store.py` with `ParquetStore` class for reading/writing OHLCV Parquet files
- [ ] 2.4 Create `src/newquant/storage/api.py` with `read_ohlcv(symbol, start_date, end_date)` and `get_sync_state(symbol)` public functions
- [ ] 2.5 Write unit tests in `tests/storage/test_manifest.py` and `tests/storage/test_parquet_store.py`

## 3. Market Data Downloader

- [ ] 3.1 Create `src/newquant/data_source/__init__.py` with public API exports
- [ ] 3.2 Create `src/newquant/data_source/base.py` with abstract `DataSource` base class and `MarketBar` dataclass
- [ ] 3.3 Create `src/newquant/data_source/tushare_source.py` implementing `TushareDataSource` with token auth and retry logic
- [ ] 3.4 Create `src/newquant/data_source/baostock_source.py` implementing `BaoStockDataSource` as fallback
- [ ] 3.5 Create `src/newquant/data_source/downloader.py` with `download_full()` and `download_incremental()` functions
- [ ] 3.6 Create `src/newquant/data_source/cli.py` with `download` click command (full/incremental modes)
- [ ] 3.7 Write unit tests in `tests/data_source/test_downloader.py`

## 4. Strategy Framework

- [ ] 4.1 Create `src/newquant/strategy/__init__.py` with public API exports
- [ ] 4.2 Create `src/newquant/strategy/base.py` with abstract `Strategy` base class containing `on_bar()`, `on_signal()`, `buy()`, `sell()`, `current_date`, `current_price`, `position()` methods
- [ ] 4.3 Create `src/newquant/strategy/context.py` with `StrategyContext` holding current bar, positions, signals
- [ ] 4.4 Write unit tests in `tests/strategy/test_base.py` with mock Strategy subclass

## 5. Backtest Engine

- [ ] 5.1 Create `src/newquant/backtest/__init__.py` with public API exports
- [ ] 5.2 Create `src/newquant/backtest/engine.py` with `BacktestEngine` class with `run()`, `buy()`, `sell()`, equity tracking, trade logging
- [ ] 5.3 Create `src/newquant/backtest/result.py` with `BacktestResult` dataclass (trades, equity_curve, metrics)
- [ ] 5.4 Create `src/newquant/backtest/cli.py` with `backtest` click command (strategy, symbol, start_date, end_date params)
- [ ] 5.5 Write integration test in `tests/backtest/test_engine.py` with simple moving average strategy

## 6. Analytics Reporting

- [ ] 6.1 Create `src/newquant/analytics/__init__.py` with public API exports
- [ ] 6.2 Create `src/newquant/analytics/metrics.py` with `compute_total_return()`, `compute_sharpe_ratio()`, `compute_max_drawdown()`, `compute_win_rate()` functions
- [ ] 6.3 Create `src/newquant/analytics/report.py` with `generate_report(backtest_result)` returning metrics dict
- [ ] 6.4 Create `src/newquant/analytics/cli.py` with `report` click command to display formatted backtest results
- [ ] 6.5 Write unit tests in `tests/analytics/test_metrics.py`

## 7. CLI Integration

- [ ] 7.1 Create `src/newquant/cli.py` as the main click group entry point with commands: `download`, `backtest`, `report`
- [ ] 7.2 Add `newquant` console script entry point in `pyproject.toml`
- [ ] 7.3 Verify CLI help works: `python -m newquant --help`

## 8. Example Strategy

- [ ] 8.1 Create `examples/strategy/ma_cross.py` with a simple moving average crossover strategy (SMA 5 vs SMA 20)
- [ ] 8.2 Add `examples/README.md` explaining how to run example strategies