"""
Development settings - for local development
"""

import os

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# 개발용 DB 설정 (PostgreSQL, .env에서 값 로드)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME"),
        "USER": os.environ.get("DB_USER"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": os.environ.get("DB_HOST"),
        "PORT": os.environ.get("DB_PORT"),
    }
}


# CORS settings for development
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8080",  # 소셜 로그인 테스트 페이지
    "http://127.0.0.1:8080",  # 소셜 로그인 테스트 페이지
]

CORS_ALLOW_CREDENTIALS = True


# Email backend for development
# EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
# 실제 이메일 전송을 원하면 위 줄을 주석 해제하세요 (콘솔 출력용)


# Django Debug Toolbar
INSTALLED_APPS += ["debug_toolbar"]

MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE

INTERNAL_IPS = [
    "127.0.0.1",
    "localhost",
]


# Logging configuration for development
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "[{levelname}] {message}",
            "style": "{",
        },
    },
    "filters": {
        "sensitive_data": {
            "()": "apps.users.services.logging.SensitiveDataFilter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "filters": ["sensitive_data"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "api": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "apps.chat": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "daphne": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# JWT Authentication for development
REST_AUTH.update(
    {
        "JWT_AUTH_COOKIE_SECURE": False,
        "JWT_AUTH_COOKIE_SAMESITE": "Lax",
    }
)
