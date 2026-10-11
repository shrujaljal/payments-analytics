-- Q7. Treasury check: do prefunding failures cluster at month end, and where?
SELECT
    receive_country,
    CASE WHEN DAY(created_at) >= DAY(LAST_DAY(created_at)) - 2
         THEN 'Last 3 days' ELSE 'Rest of month' END            AS time_of_month,
    COUNT(*)                                                    AS payouts,
    SUM(CASE WHEN failure_reason = 'Insufficient prefunding' THEN 1 ELSE 0 END) AS prefunding_failures,
    ROUND(100.0 * SUM(CASE WHEN failure_reason = 'Insufficient prefunding' THEN 1 ELSE 0 END)
          / COUNT(*), 2)                                        AS prefunding_failure_pct
FROM transactions
GROUP BY 1, 2
HAVING SUM(CASE WHEN failure_reason = 'Insufficient prefunding' THEN 1 ELSE 0 END) > 0
ORDER BY prefunding_failures DESC;
