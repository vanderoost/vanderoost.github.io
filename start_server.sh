#!/bin/bash

# Build the image if it doesn't exist
if ! docker image inspect mkdocs-site >/dev/null 2>&1; then
    echo "Building Docker image..."
    docker build -t mkdocs-site .
fi

echo "Starting MkDocs server..."
docker run --rm -it \
    -p 8000:8000 \
    -v $(pwd):/docs \
    mkdocs-site