import clickhouse_connect
from app.config import settings


def get_client():
    return clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        database=settings.clickhouse_db,
    )


def query_dau(client, target_date: str) -> float:
    result = client.query(
        "SELECT uniq(user_id) FROM events WHERE event_date = {d:String}",
        parameters={"d": target_date},
    )
    return float(result.result_rows[0][0])


def query_avg_watch_time(client, target_date: str) -> float:
    result = client.query(
        "SELECT avg(progress_seconds) FROM events "
        "WHERE event_date = {d:String} AND event_type = 'VIEW_FINISHED'",
        parameters={"d": target_date},
    )
    val = result.result_rows[0][0]
    return float(val) if val else 0.0


def query_top_movies(client, target_date: str, limit: int = 10) -> list[dict]:
    result = client.query(
        "SELECT movie_id, "
        "  uniq(user_id) AS viewers, "
        "  countIf(event_type = 'VIEW_STARTED') AS views "
        "FROM events "
        "WHERE event_date = {d:String} "
        "GROUP BY movie_id "
        "ORDER BY views DESC "
        "LIMIT {lim:UInt32}",
        parameters={"d": target_date, "lim": limit},
    )
    return [
        {"movie_id": r[0], "viewers": int(r[1]), "views": int(r[2])}
        for r in result.result_rows
    ]


def query_conversion(client, target_date: str) -> float:
    result = client.query(
        "SELECT "
        "  countIf(event_type = 'VIEW_FINISHED') / "
        "  greatest(countIf(event_type = 'VIEW_STARTED'), 1) "
        "FROM events WHERE event_date = {d:String}",
        parameters={"d": target_date},
    )
    return float(result.result_rows[0][0])


def query_retention(client, target_date: str, days_ago: int) -> float:
    result = client.query(
        "WITH cohort AS ("
        "  SELECT user_id, toDate(min(timestamp)) AS first_date "
        "  FROM events WHERE event_type = 'VIEW_STARTED' "
        "  GROUP BY user_id "
        "  HAVING first_date = toDate({d:String}) - {n:UInt32}"
        "), "
        "returned AS ("
        "  SELECT DISTINCT ca.user_id "
        "  FROM cohort ca INNER JOIN events e ON ca.user_id = e.user_id "
        "  WHERE e.event_date = toDate({d:String})"
        ") "
        "SELECT count() / greatest((SELECT count() FROM cohort), 1) FROM returned",
        parameters={"d": target_date, "n": days_ago},
    )
    return float(result.result_rows[0][0])


def save_metrics_to_clickhouse(client, rows: list[tuple]):
    for metric_date, metric_name, metric_value, _ in rows:
        client.command(
            "INSERT INTO daily_metrics (event_date, metric_name, metric_value) VALUES "
            "(%(d)s, %(n)s, %(v)s)",
            parameters={"d": metric_date, "n": metric_name, "v": metric_value},
        )
