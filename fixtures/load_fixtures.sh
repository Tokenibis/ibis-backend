#!/bin/bash

# !!WARNING!! This script deletes all existing data in the db.sqlite
# database and loads it with the latest fake data.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

cd $DIR
./make_fixtures.py

cd $DIR/../api
rm db.sqlite3
rm ibis/migrations/ -rf
rm users/migrations -rf
python3 manage.py makemigrations users
python3 manage.py makemigrations ibis
python3 manage.py migrate users
python3 manage.py migrate ibis
python3 manage.py migrate
python3 manage.py createsuperuser --username admin --email 'admin@admin.com' --noinput
python3 manage.py loaddata $DIR/fixtures.json
