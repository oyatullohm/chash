
from pathlib import Path
from datetime import timedelta
import environ
import os
BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
environ.Env.read_env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))
SECRET_KEY = env.str('SECRET_KEY')
SMS_EMAIL_API_KEY = env.str('SMS_EMAIL_API_KEY')
SMS_PASSWORD = env.str('SMS_PASSWORD')
API_1C_LOGIN = env.str('API_1C_LOGIN')
API_1C_PASSWD = env.str('API_1C_PASSWD')

DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    
    'main.apps.MainConfig',
]


JAZZMIN_SETTINGS = {
    "site_title": "Karta Admin",
    "site_header": "Diskont Kartalar",
    "site_brand": "Karta Admin",
    "welcome_sign": "Boshqaruv paneliga xush kelibsiz",
    "copyright": "Karta Tizimi",
    "search_model": ["main.CustomUser", "main.DiscountCardReport", "main.Category"],
    "show_sidebar": True,
    "navigation_expanded": True,
    "icons": {
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "main.CustomUser": "fas fa-id-card",
        "main.DiscountCardReport": "fas fa-file-invoice-dollar",
        "main.Category": "fas fa-folder",
        "main.Notification": "fas fa-bell",
    },
    "order_with_respect_to": ["main", "main.CustomUser", "main.DiscountCardReport", "main.Category", "main.Notification"],
}

JAZZMIN_UI_TWEAKS = {
    "theme": "flatly",       # boshqa variantlar: "cosmo", "cyborg", "darkly", "litera", "lux", "minty" va h.k.
    "dark_mode_theme": None,
    "navbar": "navbar-dark",
    "sidebar": "sidebar-dark-primary",
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        # 'rest_framework.authentication.SessionAuthentication',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=12),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}



MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    # 'main.middleware.UserActivityMiddleware',
    
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Admin.urls'

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}
CELERY_BROKER_URL = "redis://127.0.0.1:6379/0"
CELERY_RESULT_BACKEND = "redis://127.0.0.1:6379/0"
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'Admin.wsgi.application'


from Admin.set_database import *

DATABASES = LOCAL_DATABASE

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



LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "standard": {
            "format": "[{asctime}] [{levelname}] {name}: {message}",
            "style": "{",
        },
    },

    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": os.path.join(BASE_DIR, "logs", "app.log"),
            "formatter": "standard",
        },
    },

    "root": {
        "handlers": ["file"],
        "level": "INFO",
    },
}

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

FIREBASE_CREDENTIALS_PATH = BASE_DIR / "firebase-service-account.json"
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


AUTH_USER_MODEL = 'main.CustomUser'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'