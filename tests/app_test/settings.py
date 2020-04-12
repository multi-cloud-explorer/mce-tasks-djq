import os
import environ

env = environ.Env(DEBUG=(bool, False))

try:
    environ.Env.read_env(env.str('ENV_PATH', '.env'))
except:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PROJECT_DIR = os.path.abspath(os.path.join(BASE_DIR, '..'))

SECRET_KEY = env('MCE_SECRET_KEY', default='fa(=utzixi05twa3j*v$eaccuyq)!-_c-8=sr#hih^7i&xcw)^')

DEBUG = env('MCE_DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.humanize',
    'django_select2',
    'django_filters',
    'django_extensions',
    'django_q',
    'mce_django_app',
    'mce_tasks_djq',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'tests.app_test.urls'

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

WSGI_APPLICATION = 'tests.app_test.wsgi.application'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

DATABASES = {
    'default': env.db(),
}

LOGIN_URL = 'admin:login'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LOCALE_PATHS = ( os.path.join(BASE_DIR, 'locale'), )

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'static')

SITE_ID = env('MCE_SITE_ID', default=1, cast=int)

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'debug': {
            'format': '%(asctime)s - [%(name)s] - [%(process)d] - [%(module)s] - [line:%(lineno)d] - [%(levelname)s] - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '[%(process)d] - %(asctime)s - %(name)s: [%(levelname)s] - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'debug'
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': env('MCE_LOG_LEVEL', default='DEBUG'),
            'propagate': False,
        },
        'urllib3': {'level': 'ERROR'},
        'chardet': {'level': 'WARN'},
        'cchardet': {'level': 'WARN'},
    },
}

Q_CLUSTER = {
    'name': 'testing',
    'workers': 1,
    #'daemonize_workers': False,
    #'poll': 0.5,
    'cached': False,
    'scheduler': False,
    'orm': 'default',
    'sync': True,
    'retry': 0,
    'timeout': 3600,
    'save_limit': 0,
    'log_level': 'DEBUG',
    'cpu_affinity': 1,
}

