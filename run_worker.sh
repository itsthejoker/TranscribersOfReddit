#!/usr/bin/env bash

celery worker --app=celeryconfig -l info --purge -Q 'default' --autoscale='10,1' -n 'main@%n.%d' -E -B
