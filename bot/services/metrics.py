import structlog
from prometheus_client import Counter, Histogram, start_http_server

logger = structlog.get_logger(__name__)

messages_received_total = Counter(
    "messages_received_total",
    "Total number of incoming Telegram messages",
    ["handler"],
)

kafka_publish_errors_total = Counter(
    "kafka_publish_errors_total",
    "Total number of Kafka publish errors",
)

response_latency_seconds = Histogram(
    "response_latency_seconds",
    "Latency between request publish and worker response",
    buckets=(0.5, 1, 2, 5, 10, 30, 60, 120),
)


def start_metrics_server(port: int) -> None:
    try:
        start_http_server(port)
        logger.info("metrics_server_started", port=port)
    except OSError as exc:
        logger.warning("metrics_server_unavailable", port=port, error=str(exc))
