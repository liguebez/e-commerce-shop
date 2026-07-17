# Clothin — Django E-Commerce Shop

A full-featured clothing e-commerce web application built with Django 5.2, PostgreSQL, and Stripe Checkout.

## Live Demo

**[https://3-34-160-167.sslip.io/](https://3-34-160-167.sslip.io/)**

Deployed on a Dockerized stack running on AWS EC2. Stripe is in **test mode** — use card `4242 4242 4242 4242`, any future expiry date, any CVC, and any postal code to complete a checkout without a real charge.

## Features

- **Product catalogue** — browseable by category, paginated product list, full-text search (name + description), and sort by price or newest
- **Discount pricing** — per-product percentage discounts applied consistently across cart, orders, and Stripe line items
- **Shopping cart** — database-backed cart (`CartItem`), requires login, live item count and totals injected into every page via context processor
- **Wishlist** — database-backed wishlist (`WishlistItem`), requires login
- **Checkout & orders** — shipping address form creates an `Order` and reserves stock **at order creation** (not at payment), inside a `select_for_update()` transaction — closes the oversell window where two customers could both check out the last unit; order status lifecycle: `pending → processing → shipped → delivered → cancelled`
- **Stripe Checkout** — redirects to hosted Stripe payment page; webhook marks the order paid, sets status to `processing`, and sends a confirmation email. On expiry/abandonment, reserved stock is restored (`checkout.session.expired` webhook, backed by a periodic `release_expired_orders` command as a safety net)
- **Authentication** — register, login (username or email), logout, profile edit, password change, password reset, and **GitHub OAuth** via `social-auth-app-django`
- **Login rate limiting** — `django-axes` locks out a username+IP after repeated failed attempts, with a styled lockout page showing a live cool-off countdown
- **CAPTCHA** — `django-simple-captcha` on the registration and contact forms
- **Contact form** — sends email to `CONTACT_EMAIL`; pre-fills name/email for authenticated users
- **Sitemap** — `/sitemap.xml` with product and static-page entries, cached 24h
- **Custom error pages** — 404 and 500 templates
- **Django Debug Toolbar** — enabled in development at `/__debug__/`
- **Redis cache** — live, caching cart totals, wishlist counts, category list, homepage products, and the sitemap (test suite always runs against `DummyCache`)
- **Error monitoring** — Sentry (optional, DSN-gated) plus a zero-dependency baseline of admin emails on unhandled 500s
- **Docker deployment** — multi-stage `Dockerfile` + `docker-compose.yml` (Postgres, Redis, gunicorn, nginx, certbot, a stock-release scheduler) — see [Deployment](#deployment)

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 5.2 |
| Database | PostgreSQL (psycopg 3) |
| Payments | Stripe |
| OAuth | GitHub (social-auth-app-django) |
| Static files | WhiteNoise (CompressedManifestStaticFilesStorage) |
| Cache | Redis (hiredis) |
| Image handling | Pillow |
| Environment | python-dotenv |
| Rate limiting | django-axes |
| Error monitoring | Sentry (sentry-sdk, optional) |
| Deployment | Docker Compose (gunicorn, nginx, certbot) |

## Project Structure

```
e-commerce-shop/
├── .env                    ← secrets (not committed)
├── requirements.txt
├── Dockerfile              ← multi-stage build (builder + slim gunicorn runtime)
├── docker-compose.yml      ← db, redis, web, scheduler, nginx, certbot services
├── docker/                 ← entrypoint scripts + nginx.conf
├── deployment.md           ← full Docker Compose production deployment guide
└── clothin/                ← Django project root (run manage.py from here)
    ├── manage.py
    ├── clothin/            ← settings, root URLconf, wsgi/asgi
    ├── main/               ← Category & Product models, homepage, product list/detail/search, contact, sitemaps
    ├── cart/               ← CartItem model, context processors
    ├── wishlist/           ← WishlistItem model, context processors
    ├── users/              ← register, login, profile, password change/reset, email auth backend
    ├── orders/             ← Order & OrderItem models, checkout form, release_expired_orders command
    └── payment/            ← Stripe Checkout views + webhook handler
```

## Prerequisites

- Python 3.11+
- PostgreSQL running locally
- Redis running locally (the cache backend is live, not optional — `manage.py test` is the only exception, which always forces `DummyCache`)
- A Stripe account (test mode keys are fine)
- A GitHub OAuth app (for social login)
- Stripe CLI (optional, for local webhook testing)
- Docker & Docker Compose (optional, only for containerized deployment — see [Deployment](#deployment))

## Setup

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd e-commerce-shop
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Create the PostgreSQL database

```sql
CREATE USER clothing_store WITH PASSWORD 'your-password';
CREATE DATABASE clothing_store_db OWNER clothing_store;
```

### 3. Configure environment variables

Copy `.env.example` to `.env` in the repo root and fill in your values:

```env
SECRET_KEY=your-django-secret-key

DEBUG=True

DB_NAME=clothing_store_db
DB_USER=clothing_store
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432

# Redis, used as the cache backend (db index 1 avoids colliding with other local tools on db 0)
REDIS_URL=redis://127.0.0.1:6379/1

SOCIAL_AUTH_GITHUB_KEY=your-github-oauth-app-client-id
SOCIAL_AUTH_GITHUB_SECRET=your-github-oauth-app-client-secret

STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Minutes an unpaid order's reserved stock is held before release_expired_orders reclaims it
ORDER_RESERVATION_MINUTES=30

# Use console backend for local dev; switch to smtp in production.
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your@email.com
EMAIL_HOST_PASSWORD=your_app_password
DEFAULT_FROM_EMAIL=your@email.com

CONTACT_EMAIL=you@yourdomain.com

# Unhandled 500s get mailed to these addresses (comma-separated); leave empty to disable
ADMIN_EMAILS=you@yourdomain.com
SERVER_EMAIL=errors@yourdomain.com

# Optional: leave SENTRY_DSN empty to disable Sentry entirely
SENTRY_DSN=
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0
```

### 4. Apply migrations and create a superuser

```bash
cd clothin
python manage.py migrate
python manage.py migrate captcha   # first-time setup for django-simple-captcha
python manage.py createsuperuser
```

### 5. Collect static files

```bash
python manage.py collectstatic
```

WhiteNoise uses `CompressedManifestStaticFilesStorage` — always run `collectstatic` after editing static files, otherwise changes will not be served.

### 6. Run the development server

```bash
python manage.py runserver
```

The app is available at `http://127.0.0.1:8000`.

## Running Tests

```bash
# All apps (from clothin/)
python manage.py test

# Single app
python manage.py test main
python manage.py test cart
python manage.py test wishlist
python manage.py test users
python manage.py test orders
python manage.py test payment
```

## Stripe Webhook (local development)

To receive Stripe events locally, forward them with the Stripe CLI:

```bash
stripe listen --forward-to localhost:8000/payment/webhook/
```

Copy the printed webhook signing secret into `STRIPE_WEBHOOK_SECRET` in your `.env`.

## Payment Flow

Stock is reserved at order creation, not at payment — this closes the oversell window where two customers could both pass a stock check for the same last unit before either one pays.

1. User adds items to cart and proceeds to checkout
2. **Orders** app validates stock and **reserves it immediately**: inside one `select_for_update()` transaction it decrements `Product.stock` via `F()` expressions, creates the `Order` with `OrderItem`s at discounted prices, clears the cart, and stores `order_id` in the session. A POST against an already-empty cart (double-submit, resubmit) is rejected rather than creating an empty order.
3. **Payment** app builds a Stripe Checkout session using `Product.get_price()` (discount-aware, in cents)
4. Stripe redirects the user to its hosted payment page
5. On success, Stripe sends a `checkout.session.completed` webhook:
   - Sets `Order.paid = True` and `Order.status = 'processing'`
   - Records `Order.stripe_id` (payment intent ID)
   - Sends a confirmation email rendered from `order/email_confirmation.txt`
   - Does **not** touch `Product.stock` — it was already reserved in step 2
6. On expiry, Stripe sends `checkout.session.expired` — the reserved stock is restored (`F()` increment per `OrderItem`) and the unpaid `Order` is deleted
7. As a backstop for orders that never reach a Stripe Checkout Session at all (so no `checkout.session.expired` event ever fires), `python manage.py release_expired_orders` — run periodically via cron or the Docker `scheduler` service — restores stock and deletes any unpaid `Order` older than `ORDER_RESERVATION_MINUTES` (default 30)

## Order Status Lifecycle

| Status | Description |
|---|---|
| `pending` | Order created, awaiting payment |
| `processing` | Payment confirmed by Stripe webhook |
| `shipped` | Set manually via admin |
| `delivered` | Set manually via admin |
| `cancelled` | Set manually via admin |

## Authentication Backends

The app supports three login methods, tried in order:

1. **GitHub OAuth** — `/social-auth/login/github/`
2. **Username** — standard Django `ModelBackend`
3. **Email** — custom `EmailAuthBackend` (login with email instead of username)

`axes.backends.AxesStandaloneBackend` runs before all three so it can intercept and lock out a username+IP after repeated failed attempts (10 by default, 1-hour cool-off), regardless of which method is used.

## Admin

The Django admin is available at `/admin/`. Log in with the superuser you created during setup to manage products, categories, orders, and users.

## Deployment

Full step-by-step instructions (TLS bootstrap, production `.env` values, Stripe webhook registration, smoke test) are in [`deployment.md`](deployment.md). Once `.env` is filled in:

```bash
docker compose build
docker compose up -d
docker compose exec web python manage.py createsuperuser
docker compose logs -f web
```

The [live demo](#live-demo) runs as this same 6-service Docker Compose stack on an AWS EC2 instance:

| Service | Role |
|---|---|
| `web` | Django app served by gunicorn, non-root, multi-stage build |
| `db` | PostgreSQL 16, internal-only (no host port) |
| `redis` | Cache backend for cart totals, wishlist counts, category list, homepage products |
| `nginx` | Terminates TLS, serves `/media/` directly, reverse-proxies everything else to `web` |
| `certbot` | Issues and auto-renews the Let's Encrypt certificate |
| `scheduler` | Runs `release_expired_orders` on a loop, restoring reserved stock from abandoned checkouts (replaces a cron job) |

Notable production concerns handled in the deployment:

- **HTTPS everywhere**, via Let's Encrypt, with `SECURE_PROXY_SSL_HEADER` configured so Django correctly recognizes requests proxied over HTTP from nginx (avoids an infinite redirect loop)
- **Oversell-safe checkout** — stock is reserved at order creation (not at payment) inside a `select_for_update()` transaction, closing the race window between two customers buying the last unit
- **Non-root containers**, a multi-stage Docker build (build tooling never ships in the runtime image), and health-checked services with dependency ordering
- **Login rate limiting** via `django-axes` (lockout after repeated failed attempts) and a case-insensitive unique constraint on email to prevent duplicate-account races
