# syntax=docker/dockerfile:1

############################
# Stage 1: builder
############################
FROM python:3.13-slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libjpeg62-turbo-dev \
        zlib1g-dev \
        libwebp-dev \
        libfreetype6-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# requirements.txt is checked into the repo as UTF-16LE with a BOM (a
# Windows-editor artifact). pip's requirement parser expects UTF-8/ASCII,
# so normalize the encoding at build time -- this keeps the image building
# regardless of the source file's encoding.
COPY requirements.txt .
RUN python -c "\
import io; \
data = io.open('requirements.txt', encoding='utf-16').read(); \
io.open('requirements.txt', 'w', encoding='utf-8').write(data)"

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn==23.0.0

# Flatten clothin/ (manage.py, the clothin/ settings package, and all apps)
# into /build/app, so DJANGO_SETTINGS_MODULE=clothin.settings resolves the
# same way it does when running manage.py from the clothin/ directory.
COPY clothin/ /build/app/

# collectstatic imports settings.py in full, which unconditionally reads
# SECRET_KEY, DB_PASSWORD, SOCIAL_AUTH_GITHUB_KEY/SECRET,
# STRIPE_PUBLISHABLE_KEY/STRIPE_SECRET_KEY/STRIPE_WEBHOOK_SECRET via
# os.environ[...] with no defaults -- even though collectstatic itself
# never uses their values. These placeholders exist only in this
# discarded build stage; they are never copied into the runtime image and
# no running container ever sees them.
ENV SECRET_KEY=build-time-placeholder \
    DB_PASSWORD=build-time-placeholder \
    SOCIAL_AUTH_GITHUB_KEY=build-time-placeholder \
    SOCIAL_AUTH_GITHUB_SECRET=build-time-placeholder \
    STRIPE_PUBLISHABLE_KEY=pk_test_build_time_placeholder \
    STRIPE_SECRET_KEY=sk_test_build_time_placeholder \
    STRIPE_WEBHOOK_SECRET=whsec_build_time_placeholder

RUN cd /build/app && python manage.py collectstatic --noinput

############################
# Stage 2: runtime
############################
FROM python:3.13-slim-bookworm AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        libjpeg62-turbo \
        libwebp7 \
        libfreetype6 \
        zlib1g \
        postgresql-client \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/sh --create-home appuser

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY --from=builder /build/app /app

COPY docker/entrypoint.web.sh /entrypoint.web.sh
COPY docker/entrypoint.scheduler.sh /entrypoint.scheduler.sh
RUN chmod +x /entrypoint.web.sh /entrypoint.scheduler.sh \
    && mkdir -p /app/media \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# No dedicated health endpoint exists in urls.py; hitting '/' is a
# reasonable proxy for "gunicorn is up and Django can serve a real
# request" (and correctly reports unhealthy if the DB is unreachable,
# which is desired).
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/ -o /dev/null || exit 1

ENTRYPOINT ["/entrypoint.web.sh"]
# --workers 2: this runs on a t3.micro (1GB RAM) alongside Postgres, Redis,
# and nginx -- the usual 3-worker default assumes more headroom than this
# box comfortably has.
CMD ["gunicorn", "clothin.wsgi:application", "--bind", "0.0.0.0:8000", \
     "--workers", "2", "--timeout", "60", \
     "--access-logfile", "-", "--error-logfile", "-"]
