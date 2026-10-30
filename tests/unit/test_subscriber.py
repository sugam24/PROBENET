import json

from probenet.collectors.subscriber import load_measurements


def test_measurement_configuration():
    measurement_ids = load_measurements()

    assert measurement_ids == [1001, 1004, 1005]
    assert len(measurement_ids) == len(set(measurement_ids))


def test_subscription_message_structure():
    measurement_id = 1001

    subscription = [
        "atlas_subscribe",
        {
            "streamType": "result",
            "msm": measurement_id,
        },
    ]

    encoded = json.dumps(subscription)
    decoded = json.loads(encoded)

    assert decoded[0] == "atlas_subscribe"
    assert decoded[1]["streamType"] == "result"
    assert decoded[1]["msm"] == 1001