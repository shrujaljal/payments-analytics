-- Q2. Monthly trend with month-over-month growth (window function: LAG)
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', created_at)                         AS month,
        COUNT(*)                                                AS payouts,
        COUNT(*) * 1.0 / COUNT(DISTINCT CAST(created_at AS DATE)) AS payouts_per_day,
        SUM(send_amount_usd)                                    AS volume_usd,
        SUM(revenue_usd)                                        AS revenue_usd,
        100.0 * SUM(is_failed) / SUM(is_final)                  AS failure_rate_pct
    FROM transactions
    GROUP BY 1
)
SELECT
    STRFTIME(month, '%Y-%m')                                    AS month,
    payouts,
    ROUND(payouts_per_day, 0)                                   AS payouts_per_day,
    ROUND(volume_usd / 1e6, 2)                                  AS volume_usd_m,
    ROUND(revenue_usd / 1e3, 1)                                 AS revenue_usd_k,
    ROUND(failure_rate_pct, 2)                                  AS failure_rate_pct,
    ROUND(100.0 * (payouts_per_day / LAG(payouts_per_day) OVER (ORDER BY month) - 1), 1) AS daily_payouts_mom_pct,
    ROUND(100.0 * (revenue_usd / LAG(revenue_usd) OVER (ORDER BY month) - 1), 1) AS revenue_mom_pct
FROM monthly
ORDER BY month;
