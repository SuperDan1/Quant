## ADDED Requirements

### Requirement: Strategy framework SHALL provide an abstract Strategy base class
The strategy framework SHALL provide a `Strategy` abstract base class with methods `on_bar(bar)` and `on_signal(signal)` that user-defined strategies override.

#### Scenario: User implements custom strategy
- **WHEN** user subclasses `Strategy` and implements `on_bar(self, bar)`
- **THEN** the backtest engine calls `on_bar` for each historical bar

### Requirement: Strategy framework SHALL provide buy and sell signal methods
The strategy framework SHALL provide `self.buy(symbol, quantity)` and `self.sell(symbol, quantity)` methods that generate signal dicts ({"action": "buy"|"sell", "symbol", "quantity"}) consumed by the backtest engine.

#### Scenario: Strategy generates buy signal
- **WHEN** strategy's `on_bar` decides to buy 100 shares of "000001.SZ"
- **THEN** strategy calls `self.buy("000001.SZ", 100)` which creates a signal

### Requirement: Strategy framework SHALL allow accessing current bar data
The strategy framework SHALL provide `self.current_date`, `self.current_price`, `self.position(symbol)` to let strategies make decisions based on current market state.

#### Scenario: Check current position
- **WHEN** strategy holds 200 shares of "000001.SZ"
- **THEN** `self.position("000001.SZ")` returns 200

### Requirement: Strategy framework SHALL support parameterized strategies via __init__
The strategy framework SHALL allow strategies to accept custom parameters in `__init__` (e.g., lookback period, threshold) that are stored as instance attributes and used in `on_bar`.

#### Scenario: Parameterized moving average strategy
- **WHEN** user implements `MAStrategy(lookback=20)` with `__init__(self, lookback=20)`
- **THEN** strategy uses self.lookback=20 in `on_bar` calculations