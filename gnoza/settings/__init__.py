from pathlib import Path
from datetime import timedelta
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
from celery.schedules import crontab
SECRET_KEY = os.environ["SECRET_KEY"]
DEBUG = True
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------

DJANGO_APPS = [
    "jazzmin",  # must be before django.contrib.admin
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
    'django_celery_beat',
    'django_celery_results'
]

LOCAL_APPS = [
    "accounts",
    "content",
    "feed",
    "interactions",
    "topics",
    "reminders",
    "ai",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "gnoza.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "gnoza.wsgi.application"
ASGI_APPLICATION = "gnoza.asgi.application"

# ---------------------------------------------------------------------------
# Database — PostgreSQL
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["DB_NAME"],
        "USER": os.environ["DB_USER"],
        "PASSWORD": os.environ["DB_PASSWORD"],
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "OPTIONS": {
            "connect_timeout": 10,
        },
    }
}

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000"
).split(",")
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "EXCEPTION_HANDLER": "gnoza.exceptions.custom_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "GnozaAI API",
    "DESCRIPTION": (
        "Personalized news and events aggregation backend. "
        "Clusters content from multiple sources, delivers AI-powered "
        "analysis and chat, and surfaces trending articles and nearby events "
        "tailored to user preferences."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/v1/",
    "SECURITY": [{"BearerAuth": []}],
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    },
    "TAGS": [
        {"name": "Auth", "description": "Registration, login, profile, passwords"},
        {"name": "Feed", "description": "Personalised content feed"},
        {"name": "Content", "description": "Articles, clusters, events, AI chat"},
        {"name": "Interactions", "description": "Bookmarks, likes, comments"},
        {"name": "Topics", "description": "Topic discovery and user topic management"},
        {"name": "Reminders", "description": "Smart reminders, learning schedules, NLP parsing"},
    ],
}


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GOOGLE_CLOUD_TTS_CREDENTIALS = os.getenv("GOOGLE_CLOUD_TTS_CREDENTIALS", "")

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        days=int(os.getenv("ACCESS_TOKEN_LIFETIME_DAYS", "7"))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=int(os.getenv("REFRESH_TOKEN_LIFETIME_DAYS", "90"))
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_PAIR_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainPairSerializer",
}


# ==========================================
# REDIS & CELERY - Production strict, Local safe fallback
# ==========================================
REDIS_URL = os.getenv('REDIS_URL')

if REDIS_URL:
    # Production: use Render's REDIS_URL exactly
    REDIS_LOCATION = REDIS_URL.rstrip('/') + '/0'
else:
    # Local development: safe fallback
    if DEBUG:
        REDIS_LOCATION = 'redis://localhost:6379/0'
        print("WARNING: REDIS_URL not set. Using local Redis fallback for development.")
    else:
        raise ValueError("REDIS_URL is required in production! Set it in Render environment variables.")

# Cache
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_LOCATION,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "gnoza"
    }
}

# Celery
CELERY_BROKER_URL = REDIS_LOCATION
CELERY_RESULT_BACKEND = REDIS_LOCATION
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Channels (WebSockets)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_LOCATION],
            "capacity": 1500,
            "expiry": 10,
        },
    },
}

# Beat Scheduler
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'


CELERY_BEAT_SCHEDULE = {
    # PRIMARY: Gemini Multi-Source (Every 4 hours)
    'gemini-multi-source-fetch': {
        'task': 'content.tasks.gemini_multi_source_fetch',
        'schedule': crontab(minute=0, hour='*/4'),
    },

    # NewsAPI (Every 2 hours at :30)
    'fetch-newsapi-articles': {
        'task': 'content.tasks.fetch_newsapi_articles',
        'schedule': crontab(minute=30, hour='*/2'),
    },

    # RSS Feeds (Every 3 hours)
    'fetch-rss-feeds': {
        'task': 'content.tasks.fetch_rss_feeds',
        'schedule': crontab(minute=0, hour='*/3'),
    },

    # Guardian (Every 6 hours at :15)
    'fetch-guardian-articles': {
        'task': 'content.tasks.fetch_guardian_articles',
        'schedule': crontab(minute=15, hour='*/6'),
    },

    # Nigerian Sources (Daily at 8 AM UTC)
    'fetch-nigerian-newspapers': {
        'task': 'content.tasks.fetch_nigerian_newspapers',
        'schedule': crontab(minute=0, hour=8),
    },

    # Events
    'fetch-ticketmaster-events': {
        'task': 'content.tasks.fetch_ticketmaster_events',
        'schedule': crontab(minute=0, hour=12),  # Daily at noon
    },

    'fetch-eventbrite-events': {
        'task': 'content.tasks.fetch_eventbrite_events',
        'schedule': crontab(minute=30, hour=12),  # Daily at 12:30 PM
    },

    'fetch-local-nigerian-events': {
        'task': 'content.tasks.fetch_local_nigerian_events',
        'schedule': crontab(minute=0, hour=14),  # Daily at 2 PM
    },

    # Cleanup
    'cleanup-duplicate-events': {
        'task': 'content.tasks.cleanup_duplicate_events',
        'schedule': crontab(minute=0, hour=3),  # Daily at 3 AM
    },

    # Enrichment
    'fetch-missing-full-text': {
        'task': 'content.tasks.fetch_missing_full_text',
        'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
    },

    'fetch-missing-images': {
        'task': 'content.tasks.fetch_missing_images',
        'schedule': crontab(minute=30, hour='*/6'),  # Every 6 hours at :30
    },

    # Reminders
    'check-and-send-due-reminders': {
        'task': 'reminders.tasks.check_and_send_due_reminders',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },

    'check-learning-sessions': {
        'task': 'reminders.tasks.check_learning_sessions',
        'schedule': crontab(minute=0),  # Every hour
    },

    'check-upcoming-birthdays': {
        'task': 'reminders.tasks.check_upcoming_birthdays',
        'schedule': crontab(minute=0, hour=6),  # Daily at 6 AM
    },

    'cleanup-old-completed-reminders': {
        'task': 'reminders.tasks.cleanup_old_completed_reminders',
        'schedule': crontab(minute=0, hour=2, day_of_week=0),  # Weekly on Sunday at 2 AM
    },
}

NEWSAPI_KEY = os.getenv('NEWSAPI_KEY')
GUARDIAN_API_KEY = os.getenv('GUARDIAN_API_KEY')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT', 'GnozaAI/1.0')

TICKETMASTER_API_KEY = os.getenv('TICKETMASTER_API_KEY')
EVENTBRITE_PRIVATE_TOKEN = os.getenv('EVENTBRITE_PRIVATE_TOKEN', '')

TICKETMASTER_COUNTRY_PRIORITIES = ['NG', 'US', 'GB', 'CA', 'ZA', 'KE', 'GH']

RSS_FEEDS = {
    'BBC World': 'http://feeds.bbci.co.uk/news/world/rss.xml',
    'BBC Africa': 'http://feeds.bbci.co.uk/news/world/africa/rss.xml',
    'Al Jazeera': 'https://www.aljazeera.com/xml/rss/all.xml',
    'TechCrunch': 'https://techcrunch.com/feed/',
    'Wired': 'https://www.wired.com/feed/rss',
    'The Verge': 'https://www.theverge.com/rss/index.xml',
}

NIGERIAN_NEWS_SOURCES = {
    'Punch Nigeria': {'homepage': 'https://punchng.com/', 'article_selector': 'article.entry-item-simple'},
    'Daily Trust': {'homepage': 'https://dailytrust.com/', 'article_selector': 'div.post-item, div.article-item'},
    'Vanguard': {'homepage': 'https://www.vanguardngr.com/', 'article_selector': 'article.entry'},
}

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY required!")

GEMINI_FLASH_MODEL = 'gemini-2.5-flash'
GEMINI_PRO_MODEL = 'gemini-2.5-pro'

GEMINI_SOURCES_PER_TOPIC = 12
GEMINI_MAX_TOPICS_PER_RUN = 15


EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "GnozaAI <noreply@gnoza.ai>")

# ---------------------------------------------------------------------------
# Jazzmin — Admin UI
# ---------------------------------------------------------------------------

from .jazzmin import JAZZMIN_SETTINGS, JAZZMIN_UI_TWEAKS