# Clothin — Django E-Commerce Shop

A full-featured clothing e-commerce web application built with Django 5.2, PostgreSQL, and Stripe Checkout.

## Features

- **Product catalogue** — browseable by category, paginated product list, and detailed product pages
- **Discount pricing** — per-product percentage discounts applied consistently across cart, orders, and Stripe line items
- **Shopping cart** — database-backed cart (`CartItem`), requires login, live item count and total injected into every page via context processors
- **Wishlist** — database-backed wishlist (`WishlistItem`), requires login
- **Checkout & orders** — shipping address form creates an `Order` record before payment
- **Stripe Checkout** — redirects to hosted Stripe payment page; webhook marks order as paid on `checkout.session.completed`
- **Authentication** — register, login (username or email), logout, profile edit, password change, password reset, and **GitHub OAuth** via `social-auth-app-django`
- **CAPTCHA** — `django-simple-captcha` on registration
- **Contact form** — login-required contact page
- **Django Debug Toolbar** — enabled in development
- **Redis cache** — wired up but using `DummyCache` in dev (swap backend in settings to enable)

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 5.2 |
| Database | PostgreSQL (psycopg 3) |
| Payments | Stripe |
| OAuth | GitHub (social-auth-app-django) |
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
    ├── main/               ← Category & Product models, homepage, product list/detail, contact
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
```

### 2. Create the PostgreSQL database

```sql
CREATE USER clothing_store WITH PASSWORD '1234';
CREATE DATABASE clothing_store_db OWNER clothing_store;
```

### 3. Configure environment variables

Create a `.env` file in the repo root (`e-commerce-shop/.env`):

```env
SECRET_KEY=your-django-secret-key

DEBUG=True

DB_NAME=clothing_store_db
DB_USER=clothing_store
DB_PASSWORD=1234
DB_HOST=localhost
DB_PORT=5432

SOCIAL_AUTH_GITHUB_KEY=your-github-oauth-app-client-id
SOCIAL_AUTH_GITHUB_SECRET=your-github-oauth-app-client-secret

STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### 4. Apply migrations and create a superuser

```bash
cd clothin
python manage.py migrate
python manage.py createsuperuser
```

### 5. Run the development server

```bash
python manage.py runserver
```

The app is available at `http://127.0.0.1:8000`.

## Running Tests

```bash
# All apps
python manage.py test

# Single app
python manage.py test main
python manage.py test cart
```

## Stripe Webhook (local development)

To receive Stripe events locally, forward them with the Stripe CLI:

```bash
stripe listen --forward-to localhost:8000/payment/webhook/
```

Copy the printed webhook signing secret into `STRIPE_WEBHOOK_SECRET` in your `.env`.

## Payment Flow

1. User adds items to cart and proceeds to checkout
2. **Orders** app creates an `Order` and stores `order_id` in the session
3. **Payment** app builds a Stripe Checkout session using `Product.get_price()` (discount-aware)
4. Stripe redirects the user to its hosted payment page
5. On success, Stripe sends a `checkout.session.completed` webhook
6. Webhook handler sets `Order.paid = True`

## Authentication Backends

The app supports three login methods, tried in order:

1. **GitHub OAuth** — `/social-auth/login/github/`
2. **Username** — standard Django `ModelBackend`
3. **Email** — custom `EmailAuthBackend` (login with email instead of username)

## Admin

The Django admin is available at `/admin/`. Log in with the superuser you created during setup to manage products, categories, orders, and users.
