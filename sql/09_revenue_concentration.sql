-- Q9. Revenue concentration (Pareto): how dependent are we on our top members?
WITH rev AS (
    SELECT m.member_name, m.segment, SUM(t.revenue_usd) AS revenue_usd
    FROM transactions t
    JOIN members m USING (member_id)
    GROUP BY 1, 2
)
SELECT
    ROW_NUMBER() OVER (ORDER BY revenue_usd DESC)               AS rank,
    member_name,
    segment,
    ROUND(revenue_usd / 1e3, 1)                                 AS revenue_usd_k,
    ROUND(100 * revenue_usd / SUM(revenue_usd) OVER (), 1)      AS share_pct,
    ROUND(100 * SUM(revenue_usd) OVER (ORDER BY revenue_usd DESC)
          / SUM(revenue_usd) OVER (), 1)                        AS cumulative_share_pct
FROM rev
ORDER BY rank
LIMIT 10;
