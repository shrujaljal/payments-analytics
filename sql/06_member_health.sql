-- Q6. Member health: which members' failure rates got worse after July 1?
WITH by_period AS (
    SELECT
        m.member_name,
        m.segment,
        CASE WHEN t.created_at < DATE '2026-07-01' THEN 'H1' ELSE 'Q3' END AS period,
        COUNT(*)                                                AS payouts,
        SUM(t.is_failed) * 1.0 / SUM(t.is_final)                AS failure_rate
    FROM transactions t
    JOIN members m USING (member_id)
    GROUP BY 1, 2, 3
)
SELECT
    h1.member_name,
    h1.segment,
    h1.payouts + q3.payouts                                     AS payouts,
    ROUND(100 * h1.failure_rate, 2)                             AS h1_failure_rate_pct,
    ROUND(100 * q3.failure_rate, 2)                             AS q3_failure_rate_pct,
    ROUND(100 * (q3.failure_rate - h1.failure_rate), 2)         AS change_pts
FROM by_period h1
JOIN by_period q3
  ON h1.member_name = q3.member_name AND h1.period = 'H1' AND q3.period = 'Q3'
WHERE h1.payouts >= 300
ORDER BY change_pts DESC
LIMIT 10;
