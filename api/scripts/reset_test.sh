#!/bin/bash

# !!WARNING!! This script deletes all existing data in the db.sqlite
# database and loads it with the latest fake data.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

load_fixtures() {
    for f in $DIR/../api/fixtures/*.json
    do
	python3 manage.py loaddata $f || exit 1
    done
}

cd ~/
sudo -u postgres dropdb ibis
sudo -u postgres createdb ibis

cd $DIR/.. && \
    python3 manage.py make_fixtures \
	    --num_person 100 \
	    --num_organization 50 \
	    --num_bot 10 \
	    --num_deposit 100 \
	    --num_withdrawal 100 \
	    --num_grant 100 \
	    --num_donation 200 \
	    --num_reward 200 \
	    --num_news 200 \
	    --num_event 200 \
	    --num_post 200 \
	    --num_activity 200 \
	    --num_comment 4000 \
	    --num_channel 10 \
	    --num_message_direct 1000 \
	    --num_message_channel 500 \
	    --num_follow 500 \
	    --num_rsvp 500 \
	    --num_bookmark 4000 \
	    --num_like 4000 \
	    --num_mention 500 && \
    cd $DIR/.. && \
    rm ibis/migrations/ -rf && \
    rm distribution/migrations/ -rf && \
    rm users/migrations -rf && \
    rm tracker/migrations -rf && \
    rm notifications/migrations -rf && \
    rm gifts/migrations -rf && \
    python3 manage.py makemigrations users ibis distribution notifications tracker gifts && \
    python3 manage.py migrate users && \
    python3 manage.py migrate ibis && \
    python3 manage.py migrate distribution && \
    python3 manage.py migrate notifications && \
    python3 manage.py migrate tracker && \
    python3 manage.py migrate gifts && \
    python3 manage.py migrate && \
    load_fixtures && \
    echo "
import ibis.models
for x in ibis.models.Entry.objects.all(): x.save()
" | python3 manage.py shell
