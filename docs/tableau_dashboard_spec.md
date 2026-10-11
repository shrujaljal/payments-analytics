# Tableau Dashboard Spec: Payout Network Health

**Data source:** `tableau/payments_tableau.csv` (one flat file, one row per payout, no joins needed)
**Audience:** Operations, Product, Treasury and Account Management leads
**Question it answers:** *Is the network healthy today, and if not, where and why?*
**Size:** 1400 × 1000 px, fixed

## Calculated fields

| Name | Formula |
|---|---|
| Final Payouts | `SUM([Is Final])` |
| Failure Rate | `SUM([Is Failed]) / SUM([Is Final])` (format as % with 1 decimal) |
| Success Rate | `SUM(IF [Status] = "Completed" THEN 1 ELSE 0 END) / SUM([Is Final])` (matches the data dictionary: reversed payouts are not successes) |
| Revenue | `SUM([Revenue Usd])` |
| Take Rate (bps) | `SUM([Revenue Usd]) / SUM([Send Amount Usd]) * 10000` |
| Median Minutes | `MEDIAN([Processing Minutes])` |
| Network Failure Rate | `{FIXED : SUM([Is Failed])} / {FIXED : SUM([Is Final])}` (LOD for the reference line) |
| Is Weekend | `DATEPART('weekday', [Created At]) = 1 OR DATEPART('weekday', [Created At]) = 7` |

## Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Title: Payout Network Health · Jan to Sep 2026        [Filters ▾▾▾]      │
├──────────────┬──────────────┬──────────────┬──────────────┬─────────────┤
│ Payouts      │ Volume       │ Success rate │ Revenue      │ Median time │  ← KPI row
├──────────────┴──────────────┴──────┬───────┴──────────────┴─────────────┤
│ Map: failure rate by receive country│ Bar: failure rate by corridor ×   │
│ (circle size = payouts)             │ method, network average line      │
├─────────────────────────────────────┼───────────────────────────────────┤
│ Line: weekly failure rate           │ Bar: failure reasons (share)      │
│ (click a corridor to filter)        │                                   │
└─────────────────────────────────────┴───────────────────────────────────┘
```

## Sheets

1. **KPI tiles (5 sheets).** One big number each: payouts, volume (USD M), success rate, revenue, median processing minutes.
2. **Map.** `Receive Country Name` on detail (geographic role: Country). Color = Failure Rate (one blue sequential palette, light to dark). Size = Final Payouts.
3. **Corridor bars.** Rows = Corridor, Payout Method. Columns = Failure Rate. Sort descending. Reference line = Network Failure Rate. Highlight GB-NG bank.
4. **Weekly trend.** Columns = WEEK(Created At). Rows = Failure Rate. Annotate the June 8–13 PH partner outage.
5. **Failure reasons.** Rows = Failure Reason. Columns = COUNT of failed payouts, shown as % of total. Filter to Status = Failed.

## Interactivity

- **Filters (top row):** Created At (date range), Segment, Payout Method, Corridor. Apply them to all sheets that use this data source.
- **Dashboard action:** click a corridor bar or map country to filter the trend and reasons charts.
- **Tooltips:** corridor, payouts, failure rate, top failure reason, median minutes.

## Build order (our Tableau modules)

1. Connect to the CSV, check data types, set Country fields' geographic role
2. Create the calculated fields above
3. Build the KPI tiles
4. Build the corridor bars and map
5. Build the weekly trend and failure reasons
6. Assemble the dashboard, add filters and actions
7. Publish to Tableau Public and add the link to this README
