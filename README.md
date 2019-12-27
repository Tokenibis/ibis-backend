# Ibis Backend API

This is the application backend for the Token Ibis application. It is
implemented as a REST API using the Django REST framework. Currently,
the default database backend is SQLite.

__This code is currently in BETA__

## Dependencies

`$ sudo apt update && sudo apt upgrade`

`$ sudo apt install graphviz-dev`

`$ pip3 install pipenv`

## Setup

Please ensure that your environment is set up to run python 3

`$ git submodule init`

`$ git submodule update`

`$ virtualenv ibis-backend`

`$ cd ibis-backend`

`$ pip3 install -r requirements.txt --user`

`$ cd api`

`$ python3 manage.py test`

### Option 1 - Load Fixtures

`$ ./api/scripts/reset_test.sh

### Option 2 - Blank Database

`$ ./api/scripts/reset_blank.sh`

### Create Admin

`$ cd ibis-backend/api`

`$ python3 manage.py createsuperuser`

## Run - Development

`$ cd ibis-backend/api`

`$ python3 manage.py runserver`

## Explore

To explore the contents of the api, navigate to the 'api/' path (e.g. localhost:8000/api)

To produce a visualization of model, execute the following commands

`$ cd ibis-backend/api`

`$ python3 manage.py graph_models -a -o ibis_models.png`

## License

This software is licensed under [GNU GPL v3.0](./LICENSE).
