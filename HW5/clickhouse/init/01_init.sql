CREATE DATABASE IF NOT EXISTS cinema;

CREATE TABLE IF NOT EXISTS cinema.kafka_events (
    event_id String,
    user_id String,
    movie_id String,
    event_type String,
    timestamp String,
    device_type String,
    session_id String,
    progress_seconds Int32
) ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'movie-events',
    kafka_group_name = 'clickhouse_consumer',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE TABLE IF NOT EXISTS cinema.events (
    event_id UUID,
    user_id String,
    movie_id String,
    event_type String,
    timestamp DateTime,
    device_type String,
    session_id String,
    progress_seconds Int32,
    event_date Date DEFAULT toDate(timestamp)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (user_id, event_date, timestamp);

CREATE MATERIALIZED VIEW IF NOT EXISTS cinema.kafka_to_events TO cinema.events AS
SELECT
    toUUID(event_id) AS event_id,
    user_id,
    movie_id,
    event_type,
    parseDateTimeBestEffort(timestamp) AS timestamp,
    device_type,
    session_id,
    progress_seconds
FROM cinema.kafka_events;

CREATE TABLE IF NOT EXISTS cinema.daily_event_stats (
    event_date Date,
    event_type String,
    event_count UInt64,
    unique_users UInt64,
    sum_progress UInt64
) ENGINE = SummingMergeTree()
ORDER BY (event_date, event_type);

CREATE MATERIALIZED VIEW IF NOT EXISTS cinema.mv_daily_event_stats
TO cinema.daily_event_stats AS
SELECT
    toDate(timestamp) AS event_date,
    event_type,
    count() AS event_count,
    uniq(user_id) AS unique_users,
    sum(progress_seconds) AS sum_progress
FROM cinema.events
GROUP BY event_date, event_type;

CREATE TABLE IF NOT EXISTS cinema.daily_metrics (
    event_date Date,
    metric_name String,
    metric_value Float64,
    computed_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(computed_at)
ORDER BY (event_date, metric_name);
