-- Q5. Automatic incident detection: flag days where a payout partner's failure rate
-- is far above its own trailing 28-day baseline (rolling window function)
WITH daily AS (
    SELECT
        t.partner_id,
        p.partner_name,
        CAST(t.created_at AS DATE)                              AS day,
        COUNT(*)                                                AS payouts,
        SUM(t.is_failed)                                        AS failures
    FROM transactions t
    JOIN partners p USING (partner_id)
    GROUP BY 1, 2, 3
),
baseline AS (
    SELECT
        *,
        SUM(failures) OVER w / NULLIF(SUM(payouts) OVER w, 0)   AS baseline_failure_rate
    FROM daily
    WINDOW w AS (PARTITION BY partner_id ORDER BY day
                 ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING)
)
SELECT
    partner_name,
    day,
    payouts,
    failures,
    ROUND(100.0 * failures / payouts, 1)                        AS failure_rate_pct,
    ROUND(100.0 * baseline_failure_rate, 1)                     AS baseline_pct,
    ROUND(failures * 1.0 / payouts / NULLIF(baseline_failure_rate, 0), 1) AS times_baseline
FROM baseline
WHERE payouts >= 30
  AND failures >= 8
  AND failures * 1.0 / payouts > 3 * baseline_failure_rate
ORDER BY day, partner_name;
