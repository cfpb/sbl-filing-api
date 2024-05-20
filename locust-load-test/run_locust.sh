#!/bin/sh

case "$MODE" in 
    headless)
        locust --headless --config filing-api.conf
        ;;
    single)
        locust --config filing-api.conf
        ;;
esac