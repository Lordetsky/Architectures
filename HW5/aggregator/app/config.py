from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    clickhouse_host: str = "clickhouse"
    clickhouse_port: int = 8123
    clickhouse_db: str = "cinema"
    postgres_dsn: str = "postgresql://postgres:postgres@postgres:5432/cinema_aggregates"
    schedule_interval_sec: int = 60


settings = Settings()
