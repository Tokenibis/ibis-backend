# Ibis Backend API

This is the application backend for the Token Ibis application. It is implemented as a REST API using the Django REST framework. Currently, the default database backend is SQLite.

## Dependencies

`$ sudo apt update && sudo apt upgrade`

`$ pip3 env install pipenv`

## Setup

Please ensure that your environment is set up to run python 3

`$ cd ibis-backend`

`$ pipenv shell`

`(ibis-backend)$ pipenv install django`

`(ibis-backend)$ pipenv install django-rest-framework`

`(ibis-backend)$ pipenv install django-rest-swagger`

`(ibis-backend)$ pipenv install django-allauth`

`(ibis-backend)$ pipenv install django-rest-auth[with_social]`

`(ibis-backend)$ pipenv install django-cors-headers`

`(ibis-backend)$ cd api`

`(ibis-backend)$ python3 manage.py makemigrations profiles`

`(ibis-backend)$ python3 manage.py makemigrations ibis`

`(ibis-backend)$ python3 manage.py migrate profiles`

`(ibis-backend)$ python3 manage.py migrate ibis`

`(ibis-backend)$ python3 manage.py migrate`

`(ibis-backend)$ python3 manage.py createsuperuser`

`(ibis-backend)$ python3 manage.py test`

## Run

`$ cd ibis-backend/api`

`$ pipenv shell`

`(ibis-backend)$ python manage.py runserver`

## Explore

To explore the contents of the api, navigate to the 'api/' path (e.g. localhost:8000/api)
