#!/usr/bin/env bash
set -eu -o pipefail

build() {
    docker build --progress=plain -f Dockerfile -t joshhsoj1902/node-pi-obd-monitor:latest .
}

compose-test() {
    docker compose  -f docker-compose.test.yaml up
}

start-emu() {
    source venvobd/bin/activate
    elm -s car
}

"$@"