#!/bin/bash
set -e

echo "Starting Catalogue Industriel..."
python -m uvicorn catalogue.server:app --host 0.0.0.0 --port 8010
