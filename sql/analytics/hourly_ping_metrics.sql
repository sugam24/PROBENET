
-- ProbeNet M2.07
-- Hourly ping statistics grouped by measurement.
-- Event time determines the hourly bucket.
-- NULL RTT values are excluded from AVG.

SELECT
    measurement_id,

    date_trunc(
        'hour',
        event_time AT TIME ZONE 'UTC'
    ) AS hour_utc,

    COUNT(*) AS observation_count,

    COUNT(average_rtt_ms) AS observations_with_rtt,

    COUNT(DISTINCT probe_id) AS unique_probes,

    SUM(packets_sent) AS total_packets_sent,

    SUM(packets_received) AS total_packets_received,

    SUM(packets_sent - packets_received) AS total_packets_lost,

    ROUND(
        AVG(average_rtt_ms)::numeric,
        2
    ) AS average_rtt_ms,

    ROUND(
        (
            SUM(packets_sent - packets_received)::numeric
            / NULLIF(SUM(packets_sent), 0)
        ),
        4
    ) AS packet_loss_ratio

FROM fact_ping

GROUP BY
    measurement_id,
    hour_utc

ORDER BY
    hour_utc DESC,
    measurement_id;
