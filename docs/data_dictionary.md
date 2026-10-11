# Data Dictionary

One agreed definition for every field and metric, so every query, chart and dashboard reports the same number.

## Tables

### `transactions` (fact table, one row per payout)

| Field | Type | Description |
|---|---|---|
| transaction_id | text | Unique payout id (primary key) |
| created_at | timestamp (UTC) | When the member submitted the payout |
| completed_at | timestamp (UTC) | When the payout reached a final status. Empty while pending |
| member_id | text | Business that sent the payout (joins to `members`) |
| send_country / receive_country | text | ISO 2-letter country codes |
| corridor | text | `send_country-receive_country`, e.g. `GB-NG` |
| send_currency / payout_currency | text | ISO currency codes |
| payout_method | text | `Mobile wallet` or `Bank account` |
| partner_id | text | Local partner that delivered the payout (joins to `payout_partners`) |
| send_amount_usd | number | Payout value in USD |
| fx_rate | number | Payout currency units per 1 USD at the time of the payout |
| payout_amount | number | Amount received, in payout currency |
| fee_usd | number | Fee charged to the member. 0 for failed payouts |
| fx_margin_usd | number | FX margin earned. 0 for failed or reversed payouts |
| status | text | `Completed`, `Failed`, `Reversed` (returned after completion) or `Pending` |
| failure_reason | text | Why a payout failed. Only filled when `status = Failed` |
| processing_seconds | number | Seconds from `created_at` to `completed_at` |

Derived in `clean_data.py`:

| Field | Definition |
|---|---|
| revenue_usd | `fee_usd + fx_margin_usd` |
| is_failed | 1 if `status = 'Failed'`, else 0 |
| is_final | 1 if status is `Completed`, `Failed` or `Reversed` (not `Pending`) |

### `members`

| Field | Description |
|---|---|
| member_id | Primary key |
| member_name | Fictional business name |
| segment | `Gig economy`, `Remittance (MTO)`, `Fintech`, `PSP` or `Bank` |
| onboarded_date | Date the member went live |

### `payout_partners`

| Field | Description |
|---|---|
| partner_id | Primary key |
| partner_name | Fictional partner name, e.g. `PH Wallet Partner A` |
| country | Country the partner pays out in |
| payout_method | `Mobile wallet` or `Bank account` |

## Metric definitions

| Metric | Definition | Notes |
|---|---|---|
| Payouts | `COUNT(transaction_id)` | All statuses |
| Volume (USD) | `SUM(send_amount_usd)` | All statuses |
| Success rate | Completed ÷ final payouts | Pending payouts excluded, since they have no outcome yet |
| Failure rate | Failed ÷ final payouts | Same denominator as success rate |
| Revenue | `SUM(fee_usd + fx_margin_usd)` | Failed payouts earn nothing |
| Take rate (bps) | Revenue ÷ volume × 10,000 | Basis points |
| Processing time | Median (p50) and 90th percentile (p90) of `processing_seconds` | Median rather than average because a few delayed payouts would skew an average |
| Payouts per day | Payouts ÷ days in the month | Used for month-over-month growth, so a 28-day February isn't read as a drop |
| Incident day | A partner's daily failure rate > 3× its trailing 28-day failure rate, with ≥ 30 payouts and ≥ 8 failures that day | Minimums stop small days from raising false alarms |
| Revenue lost to failures | Failed payouts × average revenue of a completed payout in the same corridor and payout method | An estimate of direct revenue only. It doesn't include churn or support cost |

## Failure reasons

| Reason | Meaning | Usually fixed by |
|---|---|---|
| Invalid account details | Account or wallet number is wrong | Sender (pre-validation) |
| Name mismatch | Recipient name doesn't match the account holder | Sender (pre-validation) |
| Wallet not registered | Phone number has no wallet | Sender |
| Recipient limit exceeded | Wallet balance or transaction limit reached | Recipient / smaller payouts |
| Partner timeout | Payout partner didn't respond | Operations (rerouting) |
| Compliance rejection | Blocked by screening | Compliance |
| Insufficient prefunding | Not enough balance in that payout country | Treasury |
| Other | Anything else | Case by case |
