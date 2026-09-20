# Daily Brent Futures vs S&P 500 Log Returns

- prompt: scatterplot of Brent returns vs S&P 500 returns
- chart_type: scatter
- codegen: template
- folder: 20260920-003-scatter_brent-log-return-sp500-log-return

## Series

- `finance.BZ=F.log_return` — BZ=F log_return (2025-01-03..2026-09-18, n=430)
- `finance.^GSPC.log_return` — ^GSPC log_return (2025-01-03..2026-09-18, n=428)

Notes: Scatterplot with Brent front-month futures daily log returns on the x-axis and S&P 500 (^GSPC) daily log returns on the y-axis. Use the intersection of dates where both series have data, and consider adding a fitted regression line and correlation coefficient in annotations.
Rationale: User requested a scatterplot of Brent returns vs S&P 500 returns. The catalogue provides daily log return series for Brent futures (finance.BZ=F.log_return) and the S&P 500 index (finance.^GSPC.log_return), which are appropriate for a return-vs-return scatter chart to analyze co-movement and correlation.

Files: `plan.json`, `prompt.txt`, `chart.py`, `data/*.csv`, `iran_timeline.csv`, `thumbnail.png`.