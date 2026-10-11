-- Q3. Corridor scorecard: volume, reliability, speed and revenue, ranked
SELECT
    corridor,
    payout_method,
    COUNT(*)                                                    AS payouts,
    ROUND(SUM(send_amount_usd) / 1e6, 2)                        AS volume_usd_m,
    ROUND(100.0 * SUM(is_failed) / SUM(is_final), 2)            AS failure_rate_pct,
    ROUND(MEDIAN(processing_seconds), 0)                        AS p50_processing_sec,
    ROUND(QUANTILE_CONT(processing_seconds, 0.9) / 60, 1)       AS p90_processing_min,
    ROUND(SUM(revenue_usd) / 1e3, 1)                            AS revenue_usd_k,
    RANK() OVER (ORDER BY SUM(is_failed) * 1.0 / SUM(is_final) DESC) AS worst_reliability_rank
FROM transactions
GROUP BY corridor, payout_method
HAVING COUNT(*) >= 500
ORDER BY worst_reliability_rank;
