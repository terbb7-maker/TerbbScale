from datetime import timedelta

from app.workers.insights import (
    HOT_INSIGHTS_RECAPTURE_AFTER,
    METRICS_BY_PUBLICATION_TYPE,
    parse_insights,
)


def test_parse_insights_supports_total_and_values_shapes() -> None:
    payload = {
        "data": [
            {"name": "views", "total_value": {"value": 123}},
            {"name": "likes", "values": [{"value": 7}]},
            {"name": "unsupported", "values": [{"value": {"nested": True}}]},
        ]
    }

    parsed = parse_insights(payload)

    assert [(metric, value) for metric, value, _ in parsed] == [
        ("views", 123.0),
        ("likes", 7.0),
    ]


def test_story_insights_only_request_supported_metrics() -> None:
    assert METRICS_BY_PUBLICATION_TYPE["story"] == ("views", "reach", "shares")
    assert "likes" in METRICS_BY_PUBLICATION_TYPE["reel"]
    assert "saved" in METRICS_BY_PUBLICATION_TYPE["feed"]


def test_hot_insights_are_recaptured_quickly() -> None:
    assert HOT_INSIGHTS_RECAPTURE_AFTER == timedelta(minutes=5)
