import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from app.schemas import MovieEvent
from app.producer import producer
from app.config import settings
from app.generator import backfill_historical, run_realtime_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("main")

stop_event = threading.Event()
generator_thread = None


@asynccontextmanager
async def lifespan(application: FastAPI):
    global generator_thread
    if settings.generator_enabled:
        logger.info("generator enabled — starting backfill + real-time loop")
        backfill_thread = threading.Thread(target=backfill_historical, daemon=True)
        backfill_thread.start()
        generator_thread = threading.Thread(target=run_realtime_loop, args=(stop_event,), daemon=True)
        generator_thread.start()
    yield
    logger.info("shutting down")
    stop_event.set()
    producer.close()


app = FastAPI(title="Cinema Event Producer", lifespan=lifespan)


@app.post("/events")
def publish_event(payload: dict):
    try:
        event = MovieEvent(**payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors())

    try:
        event_id = producer.send(event)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"status": "ok", "event_id": event_id}


@app.get("/health")
def health():
    return {"status": "healthy"}
