#!/bin/bash

# !!WARNING!! This script deletes all existing data in the db.sqlite
# database and loads it with the latest fake data.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

cd $DIR/..
python3 manage.py make_fixtures \
	--num_person 100 \
	--num_donation 400 \
	--num_transaction 400 \
	--num_news 400 \
	--num_event 400 \
	--num_post 400 \
	--num_comment 10000 \
	--num_follow 1000 \
	--num_rsvp 10000 \
	--num_bookmark 10000 \
	--num_like  10000

cd $DIR/..
rm db.sqlite3 -rf
rm ibis/migrations/ -rf
rm users/migrations -rf
rm tracker/migrations -rf
rm notifications/migrations -rf
python3 manage.py makemigrations users
python3 manage.py makemigrations ibis
python3 manage.py makemigrations tracker
python3 manage.py makemigrations notifications
python3 manage.py migrate users
python3 manage.py migrate ibis
python3 manage.py migrate tracker
python3 manage.py migrate notifications
python3 manage.py migrate
python3 manage.py createsuperuser --username dummy --email 'admin@admin.com' --noinput
python3 manage.py loaddata $DIR/../ibis/fixtures/fixtures.json
