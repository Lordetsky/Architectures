import random
import logging
import threading
import time
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from app.schemas import MovieEvent, EventType, DeviceType
from app.producer import producer
from app.config import settings

logger = logging.getLogger("generator")

MOVIES = [f"movie_{i:03d}" for i in range(1, settings.generator_num_movies + 1)]
USERS = [f"user_{i:03d}" for i in range(1, settings.generator_num_users + 1)]
DEVICES = list(DeviceType)
MOVIE_DURATIONS = {m: random.randint(3600, 10800) for m in MOVIES}


def _generate_session(user_id: str, movie_id: str, device: DeviceType, base_time: datetime):
    session_id = str(uuid4())
    duration = MOVIE_DURATIONS[movie_id]
    events = []
    progress = 0

    ts = base_time
    events.append(MovieEvent(
        user_id=user_id, movie_id=movie_id, event_type=EventType.VIEW_STARTED,
        timestamp=ts.strftime("%Y-%m-%d %H:%M:%S"),
        device_type=device, session_id=session_id, progress_seconds=progress,
    ))

    while progress < duration:
        chunk = random.randint(60, 600)
        progress = min(progress + chunk, duration)
        ts += timedelta(seconds=chunk)

        if random.random() < 0.3 and progress < duration:
            events.append(MovieEvent(
                user_id=user_id, movie_id=movie_id, event_type=EventType.VIEW_PAUSED,
                timestamp=ts.strftime("%Y-%m-%d %H:%M:%S"),
                device_type=device, session_id=session_id, progress_seconds=progress,
            ))
            pause = random.randint(30, 300)
            ts += timedelta(seconds=pause)
            events.append(MovieEvent(
                user_id=user_id, movie_id=movie_id, event_type=EventType.VIEW_RESUMED,
                timestamp=ts.strftime("%Y-%m-%d %H:%M:%S"),
                device_type=device, session_id=session_id, progress_seconds=progress,
            ))

        if random.random() < 0.15:
            break

    events.append(MovieEvent(
        user_id=user_id, movie_id=movie_id, event_type=EventType.VIEW_FINISHED,
        timestamp=ts.strftime("%Y-%m-%d %H:%M:%S"),
        device_type=device, session_id=session_id, progress_seconds=progress,
    ))

    if random.random() < 0.4:
        ts += timedelta(seconds=random.randint(1, 30))
        events.append(MovieEvent(
            user_id=user_id, movie_id=movie_id, event_type=EventType.LIKED,
            timestamp=ts.strftime("%Y-%m-%d %H:%M:%S"),
            device_type=device, session_id=session_id, progress_seconds=progress,
        ))

    return events


def _generate_search(user_id: str, device: DeviceType, ts: datetime):
    return MovieEvent(
        user_id=user_id, movie_id=random.choice(MOVIES),
        event_type=EventType.SEARCHED,
        timestamp=ts.strftime("%Y-%m-%d %H:%M:%S"),
        device_type=device, session_id=str(uuid4()), progress_seconds=0,
    )


def backfill_historical():
    logger.info("generating historical data for %d days", settings.backfill_days)
    now = datetime.now(timezone.utc)
    total = 0

    for day_offset in range(settings.backfill_days, 0, -1):
        day_start = (now - timedelta(days=day_offset)).replace(hour=0, minute=0, second=0, microsecond=0)
        active_users = random.sample(USERS, k=random.randint(len(USERS) // 2, len(USERS)))

        for user_id in active_users:
            device = random.choice(DEVICES)
            num_sessions = random.randint(1, 3)

            for _ in range(num_sessions):
                ts = day_start + timedelta(seconds=random.randint(0, 72000))
                movie = random.choice(MOVIES)
                events = _generate_session(user_id, movie, device, ts)
                for ev in events:
                    producer.send(ev)
                    total += 1

            if random.random() < 0.5:
                ts = day_start + timedelta(seconds=random.randint(0, 86000))
                producer.send(_generate_search(user_id, device, ts))
                total += 1

    logger.info("backfill complete: %d events sent", total)


def run_realtime_loop(stop_event: threading.Event):
    logger.info("starting real-time generator, interval=%ss", settings.generator_interval_sec)
    while not stop_event.is_set():
        user_id = random.choice(USERS)
        device = random.choice(DEVICES)
        now = datetime.now(timezone.utc)

        action = random.random()
        if action < 0.7:
            movie = random.choice(MOVIES)
            events = _generate_session(user_id, movie, device, now)
            for ev in events:
                producer.send(ev)
        elif action < 0.9:
            producer.send(_generate_search(user_id, device, now))
        else:
            movie = random.choice(MOVIES)
            producer.send(MovieEvent(
                user_id=user_id, movie_id=movie, event_type=EventType.LIKED,
                timestamp=now.strftime("%Y-%m-%d %H:%M:%S"),
                device_type=device, session_id=str(uuid4()), progress_seconds=0,
            ))

        stop_event.wait(settings.generator_interval_sec)
