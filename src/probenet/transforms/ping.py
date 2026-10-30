
from datetime import datetime, timezone

from probenet.contracts.atlas import AtlasPingResult
from probenet.contracts.normalized import NormalizedPing


def normalize_ping(
    source: AtlasPingResult,
    received_at: datetime,
) -> NormalizedPing:
    """Convert one RIPE Atlas ping result into ProbeNet's schema."""

    # Calculate packet loss.
    if source.sent == 0:
        packet_loss_ratio = None
    else:
        packet_loss_ratio = (source.sent - source.rcvd) / source.sent

    # RIPE Atlas may use -1 for unavailable RTT statistics.
    def clean_rtt(value: float | None) -> float | None:
        if value is None or value < 0:
            return None
        return value

    return NormalizedPing(
        measurement_id=source.msm_id,
        probe_id=source.prb_id,
        event_time=datetime.fromtimestamp(source.timestamp, tz=timezone.utc),
        received_at=received_at,
        address_family=getattr(source, "af", None),
        packets_sent=source.sent,
        packets_received=source.rcvd,
        packet_loss_ratio=packet_loss_ratio,
        average_rtt_ms=clean_rtt(source.avg),
        minimum_rtt_ms=clean_rtt(source.min),
        maximum_rtt_ms=clean_rtt(source.max),
    )
