## ADDED Requirements

### Requirement: Analytics reporting SHALL compute total return
The analytics module SHALL compute total return as (final_equity - initial_equity) / initial_equity * 100 and return it as a percentage.

#### Scenario: Compute total return
- **WHEN** initial cash was 1000000 and final equity is 1200000
- **THEN** total_return = 20.0%

### Requirement: Analytics reporting SHALL compute Sharpe ratio
The analytics module SHALL compute annualized Sharpe ratio as (mean_daily_return / std_daily_return) * sqrt(252) using daily equity returns, assuming risk-free rate = 0.

#### Scenario: Compute Sharpe ratio
- **WHEN** daily returns are [0.01, -0.005, 0.02, 0.01]
- **THEN** Sharpe = (mean / std) * sqrt(252)

### Requirement: Analytics reporting SHALL compute maximum drawdown
The analytics module SHALL compute maximum drawdown as the maximum peak-to-trough decline in equity curve, expressed as a percentage.

#### Scenario: Compute max drawdown
- **WHEN** equity curve peaks at 1200000 then drops to 900000
- **THEN** max_drawdown = (1200000 - 900000) / 1200000 * 100 = 25.0%

### Requirement: Analytics reporting SHALL compute win rate
The analytics module SHALL compute win rate as number of profitable trades / total trades * 100.

#### Scenario: Compute win rate
- **WHEN** there are 10 trades, 7 profitable and 3 losing
- **THEN** win_rate = 70.0%

### Requirement: Analytics reporting SHALL generate a summary report
The analytics module SHALL provide a `generate_report(backtest_result) -> dict` function returning all metrics (total_return, Sharpe, max_drawdown, win_rate, total_trades, final_equity).

#### Scenario: Generate report
- **WHEN** user calls `generate_report(result)`
- **THEN** system returns dict with keys: total_return, Sharpe_ratio, max_drawdown, win_rate, total_trades, final_equity, initial_equity