def calculate_packet_loss(sent: int, received: int) -> float:
    """Calculate the percentage of packets that failed."""
    return ((sent - received) / sent) * 100


def test_packet_loss():
    result = calculate_packet_loss(sent=3, received=2)

    assert round(result, 2) == 33.33