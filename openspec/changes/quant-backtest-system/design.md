## Context

This is a greenfield quantitative trading system supporting historical market data download and strategy backtesting. The system targets individual quant traders who need a local, reproducible workflow for data acquisition and strategy validation.

**Current State**: No existing system — this is a new project.

**Constraints**:
- Python 3.10+ with type annotations
- Data stored locally (no cloud dependencies)
- Public data sources only (Tushare, BaoStock) — no paid feeds
- CLI-first interface with programmatic Python API available

**Stakeholders**: Individual quantitative traders, finance students, algorithmic trading researchers.

## Goals / Non-Goals

**Goals:**
- Provide a modular Python package for market data acquisition (full + incremental)
- Build an event-driven backtesting engine with strategy plug-in support
- Generate performance analytics (return, Sharpe, drawdown, win rate)
- Support A-share market data (stocks, indices) via Tushare/BaoStock
- Maintain clean separation: data layer, backtest engine, strategy framework, analytics

**Non-Goals:**
- Live trading execution (not a production trading system)
- Multi-asset portfolio optimization
- Machine learning or alpha generation
- Web UI or API server
- High-frequency trading strategies

## Decisions

### Decision 1: Parquet + SQLite for data storage (over HDF5 or CSV)

**Choice**: Use PyArrow Parquet for OHLCV data and SQLite for manifest tracking.

**Rationale**: Parquet offers efficient columnar storage with compression, ideal for time-series OHLCV data. SQLite requires no separate server and is portable. Alternative HDF5 has weaker Python 3.10+ support and CSV is too slow for large datasets.

**Alternatives considered**:
- CSV: Simple but slow I/O, no schema enforcement, large file sizes
- HDF5: Good but less maintained in Python ecosystem, less efficient compression
- PostgreSQL: Over-engineered for single-user local storage

### Decision 2: Event-driven backtest architecture (over vectorized)

**Choice**: Event-driven backtest that iterates bar-by-bar and calls strategy callbacks.

**Rationale**: Event-driven allows strategies to react to each bar with full information (position, cash, signals), which matches how live trading works. Vectorized backtests are faster but less realistic for complex strategies with state.

**Alternatives considered**:
- Vectorized (pandas-based): Faster but cannot model order execution realism or intrabar state
- Full discrete-event simulation: Over-engineered for this use case

### Decision 3: Tushare as primary data source with BaoStock fallback

**Choice**: Tushare is the primary API; BaoStock used when Tushare fails or for data gaps.

**Rationale**: Tushare has better data quality and coverage for A-shares but requires token. BaoStock is free and has reasonable coverage. Having both provides resilience.

**Alternatives considered**:
- Tushare only: Single point of failure, rate limits
- BaoStock only: Lower data quality and coverage
- JoinQuant: Requires GUI signup, not CLI-friendly

### Decision 4: Strategy pattern with abstract base class

**Choice**: `Strategy` ABC with `on_bar(bar)` and `on_signal(signal)` methods.

**Rationale**: Standard GoF Strategy pattern allows users to implement arbitrary strategies by subclassing. Clean interface, easy to test, familiar pattern.

**Alternatives considered**:
- Function-based (pure functions): Less flexible for stateful strategies
- Config-driven rules engine: Too limiting for complex strategies

### Decision 5: Click for CLI framework

**Choice**: Use `click` library for CLI interface.

**Rationale**: Mature, well-documented, composable commands. `typer` is a reasonable alternative but adds dependency on `tyro` which can cause issues.

**Alternatives considered**:
- `argparse`: Too low-level, verbose
- `typer`: Higher-level but adds dependency complexity

## Risks / Trade-offs

[Risk] Data source API changes or rate limits → **Mitigation**: Implement retry with exponential backoff, cache aggressively, support offline mode with cached data.

[Risk] Backtest look-ahead bias if strategy uses future data → **Mitigation**: Document clearly that strategies must only use data up to current bar date. Engine enforces bar-by-bar iteration with no future peeking.

[Risk] Large data volume (years of minute-level data) → **Mitigation**: Partition Parquet by symbol and date range. Use PyArrow for efficient columnar reads. Offer data pruning CLI command.

[Risk] User implements buggy strategy causing infinite loops → **Mitigation**: Set timeout on backtest run. Provide max_bars parameter.

[Trade-off] Simplicity vs. Features: Keep the core lean (single-symbol backtest) rather than adding multi-symbol portfolio too early. Can extend later.

## Migration Plan

N/A — greenfield project. Initial release is v0.1.0 with core functionality only.

**Rollback**: Not applicable. Local data storage means no external state to revert.

## Open Questions

1. Should we support minute-level data or daily only? (Start with daily; minute adds 240x storage)
2. Do we need to support fundamental data (financial statements)? (Defer to v0.2)
3. What is the minimum Python version? (3.10 for type union syntax `str | None`)
4. Should strategies be picklable for parallel backtesting? (Defer parallelization to later)
5. Do we need a configuration file format? (YAML-based config in `config.yaml`)