import warnings

warnings.simplefilter("always", DeprecationWarning)


def _get_database_config():
    conf = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
    return conf


SECRET_KEY = "dummy"

DATABASES = {"default": _get_database_config()}

INSTALLED_APPS = (
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "djview.tests.test_app",
)

LANGUAGES = (("de", "Deutsch"), ("en", "English"))
LANGUAGE_CODE = "de"

USE_I18N = True
USE_TZ = False
MIDDLEWARE_CLASSES = ()

ROOT_URLCONF = "djview.tests.urls"

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.InMemoryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "djview.tests.test_app.auth_backends.DummyModelBackend",
]
