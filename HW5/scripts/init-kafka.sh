#!/bin/bash
set -e

echo "=== Creating Kafka topic movie-events ==="
kafka-topics --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" \
  --create \
  --topic movie-events \
  --partitions 3 \
  --replication-factor 1 \
  --if-not-exists

echo "=== Topic created ==="
kafka-topics --bootstrap-server "$KAFKA_BOOTSTRAP_SERVERS" --describe --topic movie-events

echo "=== Registering Avro schema in Schema Registry ==="
SCHEMA=$(cat /schemas/movie_event.avsc | sed 's/"/\\"/g' | tr -d '\n')

curl -s -X POST "$SCHEMA_REGISTRY_URL/subjects/movie-events-value/versions" \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d "{\"schemaType\": \"AVRO\", \"schema\": \"$SCHEMA\"}"

echo ""
echo "=== Schema registered. Versions: ==="
curl -s "$SCHEMA_REGISTRY_URL/subjects/movie-events-value/versions"
echo ""
echo "=== Kafka init complete ==="
