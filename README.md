# Plot Portfolio

Simple analysis package for ETrade portfolio

## Getting Started

1) Install [uv](https://docs.astral.sh/uv/)
2) Run `make setup-local-dev`
3) Download your positions from ETrade as a CSV, and put the file in `\in`. Ensure that the view you export has the columns `symbol`, `last_price`, `quantity`, and `price_paid` (columns may be flexibly named per the `COLUMN_MAPPER` in `portfolio_analysis.parsing.etrade.ETradeParser`)