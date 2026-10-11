-- Q4. What drives failures in each corridor?
-- Share of each reason within a corridor, and the #1 reason per corridor (ROW_NUMBER)
WITH reasons AS (
    SELECT corridor, failure_reason, COUNT(*) AS failures
    FROM transactions
    WHERE status = 'Failed'
    GROUP BY corridor, failure_reason
),
ranked AS (
    SELECT
        *,
        ROUND(100.0 * failures / SUM(failures) OVER (PARTITION BY corridor), 1) AS share_of_corridor_failures_pct,
        ROW_NUMBER() OVER (PARTITION BY corridor ORDER BY failures DESC)        AS reason_rank
    FROM reasons
)
SELECT corridor, failure_reason AS top_failure_reason, failures, share_of_corridor_failures_pct
FROM ranked
WHERE reason_rank = 1
ORDER BY failures DESC;
