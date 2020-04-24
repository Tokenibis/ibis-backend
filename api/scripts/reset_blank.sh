#!/bin/bash

# !!WARNING!! This script deletes all existing data in the db.sqlite
# database.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

cd $DIR/.. && \
    rm db.sqlite3 -rf && \
    rm ibis/migrations/ -rf && \
    rm distribution/migrations/ -rf && \
    rm users/migrations -rf && \
    rm tracker/migrations -rf && \
    rm notifications/migrations -rf && \
    python3 manage.py makemigrations users ibis distribution notifications tracker && \
    python3 manage.py migrate users && \
    python3 manage.py migrate ibis && \
    python3 manage.py migrate distribution && \
    python3 manage.py migrate notifications && \
    python3 manage.py migrate tracker && \
    python3 manage.py migrate && \
    python3 manage.py run_setup
