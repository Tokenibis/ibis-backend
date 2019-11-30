"""
Django settings for api project.

Generated by 'django-admin startproject' using Django 2.1.5.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os
import json

with open('../config.json') as fd:
    CONF = json.load(fd)

# ------------------------------------------------------------ #
# Standard Django Settings
# ------------------------------------------------------------ #

ACCOUNT_UNIQUE_EMAIL = False

# ALLOWED_HOSTS = ['localhost', 'api.tokenibis.org', 'app.tokenibis.org']
ALLOWED_HOSTS = ['*']

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME':
        'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME':
        'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME':
        'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME':
        'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

GRAPHENE = {
    'SCHEMA': 'api.schema.schema'
}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django_extensions',
    'rest_framework',
    'rest_framework_swagger',
    'rest_framework.authtoken',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.facebook',
    'rest_auth',
    'rest_auth.registration',
    'corsheaders',
    'graphene_django',
    'users',
    'ibis',
    'tracker',
]

LANGUAGE_CODE = 'en-us'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'tracker.middleware.TrackerMiddleware',
]

ROOT_URLCONF = 'api.urls'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '%e)(pn+njk-@&iv3nd&+t$vdkpjmreg3@7#z6z0&)wh(zb&au2'

STATIC_URL = '/static/'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

WSGI_APPLICATION = 'api.wsgi.application'

# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

# ------------------------------------------------------------ #
# Additional Library/App/Middleware Settings
# ------------------------------------------------------------ #

AUTH_USER_MODEL = 'users.User'

# TODO: change to https when ready to launch from server
ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'http'

CORS_ALLOW_CREDENTIALS = True

CORS_ORIGIN_ALLOW_ALL = True

#CORS_ORIGIN_WHITELIST = (
#    'https://app.tokenibis.org',
#)

CSRF_TRUSTED_ORIGINS = ['api.tokenibis.org', 'app.tokenibis.org']

CSRF_COOKIE_DOMAIN = 'tokenibis.org'

STATIC_ROOT = os.path.join(BASE_DIR, "static/")

SITE_ID = 1

SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'

SOCIALACCOUNT_EMAIL_REQUIRED = False

SOCIALACCOUNT_QUERY_EMAIL = True

# ------------------------------------------------------------ #
# Custom Ibis Settings
# ------------------------------------------------------------ #

EMAIL_HOST = CONF['email']['host']

EMAIL_HOST_PASSWORD = CONF['email']['password']

EMAIL_HOST_USER = CONF['email']['user']

EMAIL_USE_TLS = True

PAYPAL_USE_SANDBOX = CONF['payment']['paypal']['use_sandbox']

PAYPAL_SANDBOX_CLIENT_ID = CONF['payment']['paypal']['sandbox']['client_id']

PAYPAL_SANDBOX_SECRET_KEY = CONF['payment']['paypal']['sandbox']['secret_key']

PAYPAL_LIVE_CLIENT_ID = CONF['payment']['paypal']['live']['client_id']

PAYPAL_LIVE_SECRET_KEY = CONF['payment']['paypal']['live']['secret_key']

REDIRECT_URL_GOOGLE = 'https://app.tokenibis.org/redirect/google/'

REDIRECT_URL_FACEBOOK = 'https://app.tokenibis.org/redirect/facebook/'
