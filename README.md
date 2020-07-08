# Ibis Backend API

This is the Django backend for the Token Ibis application.

__This code is currently in BETA__

## Dependencies

`$ sudo apt update && sudo apt upgrade`

`$ sudo apt install graphviz-dev`

`$ sudo apt install python3.6-venv`

## Setup

Please ensure that your environment is set up to run python 3.6 or
higher.

Follow this [guide](https://www.digitalocean.com/community/tutorials/how-to-use-postgresql-with-your-django-application-on-ubuntu-14-04) to install Postgres with a database called "ibis" and user called "ibis".

`$ git submodule init`

`$ git submodule update`

`$ cd ibis-backend`

`$ python3.6 -m venv env`

`$ source env/bin/activate`

`$ pip install -r requirements.txt`

`$ cd api`

`$ python manage.py test`

### Option 1 - Load Fixtures

`$ ./api/scripts/reset_test.sh

### Option 2 - Blank Database

`$ ./api/scripts/reset_blank.sh`

### Create Admin

`$ cd ibis-backend/api`

`$ python manage.py createsuperuser`

## Run - Development

`$ cd ibis-backend/api`

`$ python manage.py runserver`

## Explore

To explore the contents of the api, navigate to the 'api/' path (e.g. localhost:8000/api)

To produce a visualization of model, execute the following commands

`$ cd ibis-backend/api`

`$ python manage.py graph_models -a -o ibis_models.png`

## License

This software is licensed under [GNU GPL v3.0](./LICENSE).
