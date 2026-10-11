-- Q1. Headline KPIs for the whole period (Jan to Sep 2026)
-- Success rate = completed / final payouts (pending payouts are excluded)
SELECT
    COUNT(*)                                                    AS payouts,
    ROUND(SUM(send_amount_usd) / 1e6, 2)                        AS volume_usd_m,
    ROUND(AVG(send_amount_usd), 2)                              AS avg_ticket_usd,
    ROUND(100.0 * SUM(CASE WHEN status = 'Completed' THEN 1 END)
          / SUM(is_final), 2)                                   AS success_rate_pct,
    ROUND(100.0 * SUM(is_failed) / SUM(is_final), 2)            AS failure_rate_pct,
    ROUND(SUM(revenue_usd) / 1e3, 1)                            AS revenue_usd_k,
    ROUND(10000.0 * SUM(revenue_usd) / SUM(send_amount_usd), 1) AS take_rate_bps,
    ROUND(MEDIAN(processing_seconds), 1)                        AS median_processing_sec,
    COUNT(DISTINCT member_id)                                   AS active_members,
    COUNT(DISTINCT corridor)                                    AS corridors
FROM transactions;
