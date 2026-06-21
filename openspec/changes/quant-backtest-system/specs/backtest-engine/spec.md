## ADDED Requirements

### Requirement: Backtest engine SHALL process historical bars in chronological order
The backtest engine SHALL load stored OHLCV data for a given symbol and date range and iterate through bars in ascending date order, dispatching each bar to registered strategies.

#### Scenario: Process bars in order
- **WHEN** backtest starts with data from 2024-01-01 to 2024-01-10
- **THEN** engine iterates bars in strict chronological order, calling `on_bar(bar)` for each strategy

### Requirement: Backtest engine SHALL maintain positions and cash
The backtest engine SHALL maintain an internal position register (symbol -> quantity) and cash balance (float). Initial cash is configurable with default 1000000.0.

#### Scenario: Track long position
- **WHEN** strategy calls `buy(symbol, quantity, price)` and quantity=100, price=10.0
- **THEN** engine deducts 1000.0 from cash and adds 100 shares to position register

### Requirement: Backtest engine SHALL execute buy/sell orders with transaction costs
The backtest engine SHALL provide `buy(symbol, quantity, price)` and `sell(symbol, quantity, price)` methods that update positions and cash, applying a configurable transaction cost rate (default 0.0003 = 0.03%).

#### Scenario: Buy with transaction cost
- **WHEN** strategy calls `buy("000001.SZ", 100, 10.0)` with commission_rate=0.0003
- **THEN** engine deducts 1000.0 + 0.3 = 1000.3 from cash and adds 100 shares to position

### Requirement: Backtest engine SHALL record all trades
The backtest engine SHALL maintain a trade log (list of dicts with keys: date, symbol, side, quantity, price, commission, amount) for later analysis.

#### Scenario: Record buy trade
- **WHEN** buy order executes on 2024-01-05 for 100 shares at 10.0
- **THEN** trade log appends {"date": "2024-01-05", "symbol": "000001.SZ", "side": "buy", "quantity": 100, "price": 10.0, "commission": 0.3, "amount": 1000.0}

### Requirement: Backtest engine SHALL compute equity curve
The backtest engine SHALL calculate equity value at each bar as cash + sum(position_quantity * current_price) for all positions, storing as a time series for reporting.

#### Scenario: Compute equity at bar
- **WHEN** engine is at bar with close price 10.5 for 100 shares held
- **THEN** equity = cash + 100 * 10.5

### Requirement: Backtest engine SHALL run a backtest with a given strategy and symbol/date range
The backtest engine SHALL expose a `run(strategy, symbol, start_date, end_date)` method that initializes state, processes all bars, and returns a BacktestResult object containing trades, equity_curve, and final metrics.

#### Scenario: Run backtest
- **WHEN** user calls `engine.run(MyStrategy(), "000001.SZ", "2024-01-01", "2024-12-31")`
- **THEN** engine returns BacktestResult with trades, equity_curve (dict date->equity), and metrics