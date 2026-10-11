-- Q8. Speed: how much slower are bank payouts created on weekends?
SELECT
    receive_country,
    COUNT(*) FILTER (WHERE DAYOFWEEK(created_at) IN (0, 6))               AS weekend_payouts,
    ROUND(MEDIAN(processing_seconds) FILTER (WHERE DAYOFWEEK(created_at) NOT IN (0, 6)) / 60, 1) AS weekday_p50_min,
    ROUND(MEDIAN(processing_seconds) FILTER (WHERE DAYOFWEEK(created_at) IN (0, 6)) / 60, 1)     AS weekend_p50_min,
    ROUND(100.0 * AVG(CASE WHEN processing_seconds > 3600 THEN 1 ELSE 0 END)
          FILTER (WHERE DAYOFWEEK(created_at) IN (0, 6)), 1)              AS weekend_over_1h_pct
FROM transactions
WHERE payout_method = 'Bank account' AND status = 'Completed'
GROUP BY receive_country
ORDER BY weekend_p50_min DESC;
