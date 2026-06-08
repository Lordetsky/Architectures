import logging
import time
from datetime import date, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.clickhouse_queries import (
    get_client,
    query_dau,
    query_avg_watch_time,
    query_top_movies,
    query_conversion,
    query_retention,
    save_metrics_to_clickhouse,
)
from app.postgres_client import save_metrics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("aggregator")

scheduler = BackgroundScheduler()


def run_aggregation(target_date: str | None = None):
    if target_date is None:
        target_date = str(date.today() - timedelta(days=1))

    logger.info("aggregation started for date=%s", target_date)
    start = time.time()

    ch = get_client()
    rows = []
    records_processed = 0

    try:
        dau = query_dau(ch, target_date)
        rows.append((target_date, "dau", dau, {}))
        records_processed += 1

        avg_wt = query_avg_watch_time(ch, target_date)
        rows.append((target_date, "avg_watch_time_sec", avg_wt, {}))
        records_processed += 1

        top = query_top_movies(ch, target_date, limit=10)
        rows.append((target_date, "top_movies", len(top), {"ranking": top}))
        records_processed += 1

        conv = query_conversion(ch, target_date)
        rows.append((target_date, "view_conversion", conv, {}))
        records_processed += 1

        ret_d1 = query_retention(ch, target_date, days_ago=1)
        rows.append((target_date, "retention_d1", ret_d1, {}))
        records_processed += 1

        ret_d7 = query_retention(ch, target_date, days_ago=7)
        rows.append((target_date, "retention_d7", ret_d7, {}))
        records_processed += 1

        save_metrics_to_clickhouse(ch, rows)
        save_metrics(rows)
    except Exception:
        logger.exception("aggregation failed for date=%s", target_date)
        raise
    finally:
        ch.close()

    elapsed = time.time() - start
    logger.info(
        "aggregation complete: date=%s, records=%d, time=%.2fs",
        target_date, records_processed, elapsed,
    )
    return {"date": target_date, "records": records_processed, "elapsed_sec": round(elapsed, 2)}


def scheduled_job():
    try:
        run_aggregation()
    except Exception:
        logger.exception("scheduled aggregation failed")


@asynccontextmanager
async def lifespan(application: FastAPI):
    scheduler.add_job(
        scheduled_job,
        trigger="interval",
        seconds=settings.schedule_interval_sec,
        id="aggregation_job",
    )
    scheduler.start()
    logger.info("scheduler started, interval=%ds", settings.schedule_interval_sec)
    yield
    scheduler.shutdown()
    logger.info("scheduler stopped")


app = FastAPI(title="Cinema Aggregation Service", lifespan=lifespan)


@app.post("/aggregate")
def aggregate(target_date: str = Query(default=None, description="YYYY-MM-DD")):
    result = run_aggregation(target_date)
    return result


@app.get("/health")
def health():
    return {"status": "healthy"}
