
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class NormalizedPing(BaseModel):
    """Canonical representation of one RIPE Atlas ping observation."""

    model_config = ConfigDict(extra="forbid")

    measurement_id: int = Field(gt=0)
    probe_id: int = Field(gt=0)

    event_time: datetime
    received_at: datetime

    address_family: Literal[4, 6] | None = None

    packets_sent: int = Field(ge=0)
    packets_received: int = Field(ge=0)

    packet_loss_ratio: float = Field(ge=0, le=1)

    average_rtt_ms: float | None = Field(default=None, ge=0)
    minimum_rtt_ms: float | None = Field(default=None, ge=0)
    maximum_rtt_ms: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_consistency(self):
        if self.packets_received > self.packets_sent:
            raise ValueError("Received packets cannot exceed sent packets")

        if self.packets_received == 0 and self.average_rtt_ms is not None:
            raise ValueError("Average RTT must be null when no packets reply")

        return self
