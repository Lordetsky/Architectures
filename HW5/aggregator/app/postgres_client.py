import json
import logging
import psycopg2
from psycopg2.extras import execute_values
from app.config import settings

logger = logging.getLogger("postgres")

UPSERT_SQL = """
    INSERT INTO metrics (metric_date, metric_name, metric_value, details, computed_at)
    VALUES (%s, %s, %s, %s, NOW())
    ON CONFLICT (metric_date, metric_name)
    DO UPDATE SET metric_value = EXCLUDED.metric_value,
                  details      = EXCLUDED.details,
                  computed_at  = NOW()
"""


def save_metrics(rows: list[tuple]):
    conn = None
    try:
        conn = psycopg2.connect(settings.postgres_dsn)
        with conn.cursor() as cur:
            for metric_date, metric_name, metric_value, details in rows:
                cur.execute(UPSERT_SQL, (
                    metric_date,
                    metric_name,
                    metric_value,
                    json.dumps(details, ensure_ascii=False),
                ))
        conn.commit()
        logger.info("saved %d metric rows to postgres", len(rows))
    except Exception:
        logger.exception("failed to save metrics")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
