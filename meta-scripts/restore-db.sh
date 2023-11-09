#!/bin/bash

show_usage() {
  echo "Usage: $0 <path_to_backup_directory>"
  exit 1
}

if [ "$#" -ne 1 ]; then
  show_usage
fi

MONGO_CONTAINER="chess-insights-mongodb-1"

docker-compose up -d
docker cp "$1"/. "$MONGO_CONTAINER":/backup
docker exec -it "$MONGO_CONTAINER" mongorestore --db chess-insights /backup
