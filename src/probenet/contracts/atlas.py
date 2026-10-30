
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PingPacket(BaseModel):
    """One ping packet result from RIPE Atlas."""

    model_config = ConfigDict(extra="allow")

    rtt: float | None = Field(default=None, ge=0)
    x: str | None = None
    ttl: int | None = None


class AtlasPingResult(BaseModel):
    """Source-level RIPE Atlas ping observation."""

    model_config = ConfigDict(extra="allow")

    msm_id: int = Field(gt=0)
    prb_id: int = Field(gt=0)
    timestamp: int = Field(ge=0)

    type: Literal["ping"]

    sent: int = Field(ge=0)
    rcvd: int = Field(ge=0)

    result: list[PingPacket]

    min: float | None = None
    max: float | None = None
    avg: float | None = None

    @model_validator(mode="after")
    def validate_packet_counts(self):
        if self.rcvd > self.sent:
            raise ValueError(
                "Received packets cannot exceed sent packets"
            )

        return self


class AtlasResultEnvelope(BaseModel):
    """A live RIPE Atlas measurement-result message."""

    event_type: Literal["atlas_result"]
    payload: AtlasPingResult

    @classmethod
    def from_message(cls, message: list):
        """Validate a two-element RIPE Atlas result message."""
        if len(message) != 2:
            raise ValueError("Expected a two-element WebSocket message")

        return cls(
            event_type=message[0],
            payload=message[1],
        )
