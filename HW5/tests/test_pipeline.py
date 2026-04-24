import os
import time
import uuid
import requests
import clickhouse_connect
import pytest

PRODUCER_URL = os.getenv("PRODUCER_URL", "http://localhost:8000")
CH_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CH_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
CH_DB = os.getenv("CLICKHOUSE_DB", "cinema")

POLL_INTERVAL = 2
POLL_TIMEOUT = 60


@pytest.fixture
def ch_client():
    client = clickhouse_connect.get_client(host=CH_HOST, port=CH_PORT, database=CH_DB)
    yield client
    client.close()


def wait_for_event(ch_client, event_id: str) -> dict | None:
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        result = ch_client.query(
            "SELECT event_id, user_id, movie_id, event_type, device_type, "
            "session_id, progress_seconds "
            "FROM events WHERE event_id = {eid:UUID}",
            parameters={"eid": event_id},
        )
        if result.result_rows:
            row = result.result_rows[0]
            return {
                "event_id": str(row[0]),
                "user_id": row[1],
                "movie_id": row[2],
                "event_type": row[3],
                "device_type": row[4],
                "session_id": row[5],
                "progress_seconds": row[6],
            }
        time.sleep(POLL_INTERVAL)
    return None


def test_event_flows_from_producer_to_clickhouse(ch_client):
    event_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    payload = {
        "event_id": event_id,
        "user_id": "test_user_001",
        "movie_id": "test_movie_001",
        "event_type": "VIEW_STARTED",
        "device_type": "DESKTOP",
        "session_id": session_id,
        "progress_seconds": 0,
    }

    resp = requests.post(f"{PRODUCER_URL}/events", json=payload, timeout=10)
    assert resp.status_code == 200, f"producer returned {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["event_id"] == event_id

    found = wait_for_event(ch_client, event_id)
    assert found is not None, f"event {event_id} not found in ClickHouse within {POLL_TIMEOUT}s"
    assert found["user_id"] == "test_user_001"
    assert found["movie_id"] == "test_movie_001"
    assert found["event_type"] == "VIEW_STARTED"
    assert found["device_type"] == "DESKTOP"
    assert found["session_id"] == session_id
    assert found["progress_seconds"] == 0


def test_invalid_event_rejected():
    payload = {
        "user_id": "test_user",
        "movie_id": "test_movie",
        "event_type": "INVALID_TYPE",
        "device_type": "DESKTOP",
        "session_id": "s1",
        "progress_seconds": 0,
    }
    resp = requests.post(f"{PRODUCER_URL}/events", json=payload, timeout=10)
    assert resp.status_code == 422


def test_multiple_events_same_session(ch_client):
    session_id = str(uuid.uuid4())
    events_data = [
        ("VIEW_STARTED", 0),
        ("VIEW_PAUSED", 300),
        ("VIEW_RESUMED", 300),
        ("VIEW_FINISHED", 900),
    ]

    sent_ids = []
    for event_type, progress in events_data:
        eid = str(uuid.uuid4())
        sent_ids.append(eid)
        payload = {
            "event_id": eid,
            "user_id": "test_user_session",
            "movie_id": "test_movie_session",
            "event_type": event_type,
            "device_type": "TV",
            "session_id": session_id,
            "progress_seconds": progress,
        }
        resp = requests.post(f"{PRODUCER_URL}/events", json=payload, timeout=10)
        assert resp.status_code == 200

    for eid in sent_ids:
        found = wait_for_event(ch_client, eid)
        assert found is not None, f"event {eid} not found in ClickHouse"


def test_producer_health():
    resp = requests.get(f"{PRODUCER_URL}/health", timeout=5)
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
