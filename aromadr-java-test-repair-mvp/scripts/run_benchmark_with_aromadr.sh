#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export MAVEN_BIN="${MAVEN_BIN:-$(cd .. && pwd)/tools/apache-maven-3.9.16/bin/mvn}"
export AROMADR_API_URL="${AROMADR_API_URL:-http://localhost:3000}"

python3 -m test_repair_mvp \
  --benchmark demo/config/benchmark.json \
  --run-dir .mvp_runs/benchmark-aromadr
