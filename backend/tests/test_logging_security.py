import logging

from app.core.logging import suppress_sensitive_transport_logs


def test_sensitive_http_transport_logs_are_suppressed() -> None:
    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("httpcore").setLevel(logging.INFO)

    suppress_sensitive_transport_logs()

    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING
