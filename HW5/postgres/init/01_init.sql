CREATE TABLE IF NOT EXISTS metrics (
    metric_date  DATE NOT NULL,
    metric_name  VARCHAR(100) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    details      JSONB DEFAULT '{}',
    computed_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (metric_date, metric_name)
);
