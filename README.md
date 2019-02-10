# Ibis Backend API

This is the application backend for the Token Ibis application. It is implemented as a REST API using the Django REST framework. Currently, the default database backend is SQLite.

## Dependencies

`$ sudo apt update && sudo apt upgrade`

`$ sudo apt install pipenv`

## Setup

Please ensure that your environment is set up to run python 3

`$ cd backend`

`$ pipenv shell`

`(backend)$ pipenv install django`

`(backend)$ pipenv install django djangorestframework`

`(backend)$ cd api`

`(backend)$ python manage.py migrate`

`(backend)$ python manage.py createsuperuser`

`(backend)$ python manage.py test`

## Run

`$ cd backend`

`$ pipenv shell`

`(backend)$ python manage runserver`
