#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py createcachetable

# Honour the compose `command:` (e.g. runserver in dev); default to gunicorn.
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --timeout 60
