-- Q10. What do failures cost? Estimate revenue lost per failure reason using
-- the average revenue of a completed payout in the same corridor and method
WITH unit_rev AS (
    SELECT corridor, payout_method, AVG(revenue_usd) AS avg_rev
    FROM transactions
    WHERE status = 'Completed'
    GROUP BY 1, 2
)
SELECT
    t.failure_reason,
    COUNT(*)                                                    AS failures,
    ROUND(SUM(t.send_amount_usd) / 1e3, 0)                      AS failed_volume_usd_k,
    ROUND(SUM(u.avg_rev), 0)                                    AS est_revenue_lost_usd,
    ROUND(100 * SUM(u.avg_rev) / SUM(SUM(u.avg_rev)) OVER (), 1) AS share_of_lost_revenue_pct
FROM transactions t
JOIN unit_rev u USING (corridor, payout_method)
WHERE t.status = 'Failed'
GROUP BY 1
ORDER BY est_revenue_lost_usd DESC;
