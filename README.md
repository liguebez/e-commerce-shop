# Clothin — Django E-Commerce Shop

A full-featured clothing e-commerce web application built with Django 5.2, PostgreSQL, and Stripe Checkout.

## Features

- **Product catalogue** — browseable by category, paginated product list, full-text search (name + description), and sort by price or newest
- **Discount pricing** — per-product percentage discounts applied consistently across cart, orders, and Stripe line items
- **Shopping cart** — database-backed cart (`CartItem`), requires login, live item count and totals injected into every page via context processor
- **Wishlist** — database-backed wishlist (`WishlistItem`), requires login
- **Checkout & orders** — shipping address form creates an `Order` record before payment; order status lifecycle: `pending → processing → shipped → delivered → cancelled`
- **Stripe Checkout** — redirects to hosted Stripe payment page; webhook marks order paid, sets status to `processing`, decrements stock, and sends a confirmation email
- **Authentication** — register, login (username or email), logout, profile edit, password change, password reset, and **GitHub OAuth** via `social-auth-app-django`
- **CAPTCHA** — `django-simple-captcha` on the registration and contact forms
- **Contact form** — sends email to `CONTACT_EMAIL`; pre-fills name/email for authenticated users
- **Sitemap** — `/sitemap.xml` with product and static-page entries
- **Custom error pages** — 404 and 500 templates
- **Django Debug Toolbar** — enabled in development at `/__debug__/`
- **Redis cache** — wired up but using `DummyCache` in dev (swap backend in settings to enable)

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

## Project Structure

```
e-commerce-shop/
├── .env                    ← secrets (not committed)
├── requirements.txt
└── clothin/                ← Django project root (run manage.py from here)
    ├── manage.py
    ├── clothin/            ← settings, root URLconf, wsgi/asgi
    ├── main/               ← Category & Product models, homepage, product list/detail/search, contact, sitemaps
    ├── cart/               ← CartItem model, context processors
    ├── wishlist/           ← WishlistItem model, context processors
    ├── users/              ← register, login, profile, password change/reset, email auth backend
    ├── orders/             ← Order & OrderItem models, checkout form
    └── payment/            ← Stripe Checkout views + webhook handler
```

## Prerequisites

- Python 3.11+
- PostgreSQL running locally
- A Stripe account (test mode keys are fine)
- A GitHub OAuth app (for social login)
- Stripe CLI (optional, for local webhook testing)

## Setup

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd e-commerce-shop
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install python-dotenv   # not in requirements.txt, but required
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

SOCIAL_AUTH_GITHUB_KEY=your-github-oauth-app-client-id
SOCIAL_AUTH_GITHUB_SECRET=your-github-oauth-app-client-secret

STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Email (console backend is used in dev — emails print to the terminal)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your@email.com
EMAIL_HOST_PASSWORD=your_app_password
DEFAULT_FROM_EMAIL=your@email.com

CONTACT_EMAIL=you@yourdomain.com
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

1. User adds items to cart and proceeds to checkout
2. **Orders** app validates stock, creates an `Order` with `OrderItem`s at discounted prices, clears the cart, and stores `order_id` in the session
3. **Payment** app builds a Stripe Checkout session using `Product.get_price()` (discount-aware, in cents)
4. Stripe redirects the user to its hosted payment page
5. On success, Stripe sends a `checkout.session.completed` webhook:
   - Sets `Order.paid = True` and `Order.status = 'processing'`
   - Records `Order.stripe_id` (payment intent ID)
   - Decrements `Product.stock` using `F()` expressions (atomic)
   - Sends a confirmation email rendered from `order/email_confirmation.txt`
6. On expiry, Stripe sends `checkout.session.expired` — unpaid orders are deleted

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

## Admin

The Django admin is available at `/admin/`. Log in with the superuser you created during setup to manage products, categories, orders, and users.
