# SaaS Product Management Dashboard

A full-stack SaaS product operations dashboard built with FastAPI, SQLAlchemy and React. The app helps teams manage a product catalog, track inventory health, review catalog value and perform day-to-day product CRUD workflows from a clean dashboard interface.

## Features

- FastAPI REST API for product catalog management
- React dashboard with product metrics, API-backed search, category and stock filters and sorting
- Create, update and delete product records
- Product categories with per-category breakdown metrics and category filtering
- Quick restock with inline stock adjustments (PATCH endpoint plus +/- controls)
- Audit timestamps (`created_at` / `updated_at`) surfaced in the UI
- Bulk product creation via CSV import with per-row validation and an error report
- Inventory health labels for healthy, low-stock and out-of-stock products
- Derived SaaS operations metrics including catalog value, average price and total inventory
- Product insights for highest-value product, reorder queue and out-of-stock tracking
- CSV export for the currently filtered product catalog
- SQLite local development fallback with optional `DATABASE_URL` override
- Interactive API docs at `/docs`

## Tech Stack

**Backend:** FastAPI, Python, SQLAlchemy, Pydantic  
**Frontend:** React, JavaScript, CSS  
**Database:** SQLite by default, configurable through `DATABASE_URL`

## Project Structure

```text
FastAPI_demo/
├── app/
│   ├── main.py             # App factory and router wiring
│   ├── config.py           # Pydantic-settings configuration
│   ├── database.py         # Engine/session setup
│   ├── db_models.py        # SQLAlchemy product model
│   ├── schemas.py          # Pydantic request/response schemas
│   ├── dependencies.py     # Shared FastAPI dependencies (DB session)
│   ├── routers/            # HTTP routes (products, meta)
│   └── services/           # Framework-agnostic domain logic
├── seed.py                 # Demo SaaS product data
├── requirements.txt        # Backend dependencies
├── tests/                  # Backend API tests
└── frontend/
    ├── public/
    └── src/
        ├── App.js          # Dashboard UI and API integration
        ├── App.css         # Dashboard styling
        └── index.js
```

## Getting Started

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000`.

Load sample SaaS products for a richer dashboard:

```bash
python seed.py
```

### Database & Migrations

SQLite is the zero-config default — tables are created automatically on startup and the demo needs no extra setup. For Postgres (or any non-SQLite backend), schema is managed by Alembic instead.

Start a local Postgres and point the app at it:

```bash
docker compose up -d db
export DATABASE_URL=postgresql://saas:saas@localhost:5432/saas_products
alembic upgrade head
```

Common Alembic commands:

```bash
alembic revision --autogenerate -m "describe change"   # create a migration from model changes
alembic upgrade head                                    # apply migrations
alembic downgrade -1                                    # roll back the last migration
```

### Authentication & Rate Limiting

Both are optional and disabled by default, so the demo runs open. Enable them with environment variables:

```bash
export API_KEYS=local-dev-key,another-key   # clients send one as the X-API-Key header
export RATE_LIMIT_PER_MINUTE=120            # per-identity; 0 disables
```

When keys are set, product endpoints return a structured `401` (missing/invalid key) or `429` (rate limited, with a `Retry-After` header); `/` and `/health` stay open. The frontend forwards a key when `REACT_APP_API_KEY` is set.

### Frontend

```bash
cd frontend
npm install
npm start
```

The React app runs at `http://localhost:3000` and connects to the backend at `http://127.0.0.1:8000`.

To use a different API URL:

```bash
REACT_APP_API_URL=https://your-api.example.com npm start
```

### Tests

```bash
pytest
```

## API Endpoints

| Method | Endpoint            | Description |
| ------ | ------------------- | ----------- |
| GET    | `/`                 | API metadata |
| GET    | `/health`           | Health check |
| GET    | `/products`              | List products (paginated envelope) with search, filters and sorting |
| GET    | `/products/summary`      | Product dashboard summary metrics with category breakdown |
| GET    | `/products/insights`     | Product insights for operations follow-up |
| GET    | `/products/categories`   | Distinct product categories |
| GET    | `/products/{id}`         | Fetch one product |
| POST   | `/products`              | Create a product |
| POST   | `/products/import`       | Bulk-create products from a CSV upload |
| PUT    | `/products/{id}`         | Update a product |
| PATCH  | `/products/{id}/stock`   | Adjust stock by a positive or negative delta |
| DELETE | `/products/{id}`         | Delete a product |

### Product Query Parameters

`GET /products` supports:

| Parameter      | Values |
| -------------- | ------ |
| `search`       | Product name or description text |
| `category`     | Exact category name |
| `stock_status` | `all`, `healthy`, `low`, `out` |
| `sort_by`      | `name`, `stock`, `value`, `price` |
| `skip`         | Number of records to skip |
| `limit`        | Number of records to return |
| `min_price`    | Minimum product price |
| `max_price`    | Maximum product price |

The response is a paginated envelope: `{ "items": [...], "total": <int>, "skip": <int>, "limit": <int> }`.

### CSV Import Format

`POST /products/import` accepts a multipart `file` upload. The CSV must include a header row with `name`, `description`, `price` and `quantity` columns; `category` is optional and defaults to `Uncategorized`. Rows that fail validation are skipped and returned in the response `errors` list with their row number, while valid rows are created.

```csv
name,description,price,quantity,category
Starter Plan,Self-serve plan for small teams,49,42,Subscription
Analytics Add-on,Product analytics module,89,5,Add-on
```

## GitHub Description

Recommended repository description:

```text
SaaS Product Management Dashboard built with FastAPI, SQLAlchemy and React for product catalog CRUD, inventory health tracking and dashboard metrics.
```

## Author

Aditya Singh
