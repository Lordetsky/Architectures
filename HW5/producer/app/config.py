from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    kafka_bootstrap_servers: str = "kafka:29092"
    schema_registry_url: str = "http://schema-registry:8081"
    kafka_topic: str = "movie-events"
    generator_enabled: bool = True
    generator_interval_sec: float = 2.0
    generator_num_users: int = 20
    generator_num_movies: int = 10
    backfill_days: int = 10
    kafka_acks: str = "all"
    kafka_retries: int = 5


settings = Settings()
