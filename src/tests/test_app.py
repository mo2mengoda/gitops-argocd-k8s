import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["ERROR_RATE"] = "0"
os.environ["LATENCY_MS"] = "0"

from main import app  # noqa: E402


def test_health_endpoints():
    c = app.test_client()
    assert c.get("/healthz").status_code == 200
    assert c.get("/readyz").status_code == 200


def test_orders_and_metrics():
    c = app.test_client()
    assert c.get("/api/orders").status_code == 200
    metrics = c.get("/metrics").get_data(as_text=True)
    assert 'http_requests_total{method="GET",route="/api/orders",status="200"}' in metrics
