import json
import time
import logging
from confluent_kafka import Producer as KafkaProducer
from app.config import settings
from app.schemas import MovieEvent

logger = logging.getLogger("producer")


class Producer:
    def __init__(self):
        self._producer = KafkaProducer({
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "acks": settings.kafka_acks,
            "retries": settings.kafka_retries,
            "retry.backoff.ms": 500,
            "enable.idempotence": True,
        })

    def _on_delivery(self, err, msg):
        if err:
            logger.error("delivery failed: %s", err)
        else:
            logger.info(
                "delivered event_id=%s event_type=%s topic=%s partition=%s",
                msg.key().decode() if msg.key() else "N/A",
                json.loads(msg.value()).get("event_type"),
                msg.topic(),
                msg.partition(),
            )

    def send(self, event: MovieEvent) -> str:
        value = json.dumps(event.model_dump(), ensure_ascii=False).encode("utf-8")
        key = event.user_id.encode("utf-8")

        max_attempts = settings.kafka_retries
        for attempt in range(1, max_attempts + 1):
            try:
                self._producer.produce(
                    topic=settings.kafka_topic,
                    key=key,
                    value=value,
                    callback=self._on_delivery,
                )
                self._producer.flush(timeout=10)
                logger.info(
                    "published event_id=%s event_type=%s timestamp=%s",
                    event.event_id, event.event_type.value, event.timestamp,
                )
                return event.event_id
            except Exception as exc:
                wait = min(2 ** attempt, 30)
                logger.warning(
                    "publish attempt %d/%d failed: %s — retrying in %ds",
                    attempt, max_attempts, exc, wait,
                )
                time.sleep(wait)

        raise RuntimeError(f"failed to publish event after {max_attempts} attempts")

    def close(self):
        self._producer.flush(timeout=30)


producer = Producer()
