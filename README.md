# SaaS Product Management Dashboard

A full-stack SaaS product operations dashboard built with FastAPI, SQLAlchemy, and React. The app helps teams manage a product catalog, track inventory health, review catalog value, and perform day-to-day product CRUD workflows from a clean dashboard interface.

## Features

- FastAPI REST API for product catalog management
- React dashboard with product metrics, API-backed search, stock filters, and sorting
- Create, update, and delete product records
- Inventory health labels for healthy, low-stock, and out-of-stock products
- Derived SaaS operations metrics including catalog value, average price, and total inventory
- Product insights for highest-value product, reorder queue, and out-of-stock tracking
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
├── main.py                 # FastAPI application and product routes
├── database.py             # Database engine/session setup
├── database_models.py      # SQLAlchemy product model
├── models.py               # Pydantic request/response schemas
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
uvicorn main:app --reload
```

The API runs at `http://127.0.0.1:8000`.

Load sample SaaS products for a richer dashboard:

```bash
python seed.py
```

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
| GET    | `/products`         | List products with pagination, search, filters, and sorting |
| GET    | `/products/summary` | Product dashboard summary metrics |
| GET    | `/products/insights`| Product insights for operations follow-up |
| GET    | `/products/{id}`    | Fetch one product |
| POST   | `/products`         | Create a product |
| PUT    | `/products/{id}`    | Update a product |
| DELETE | `/products/{id}`    | Delete a product |

### Product Query Parameters

`GET /products` supports:

| Parameter      | Values |
| -------------- | ------ |
| `search`       | Product name or description text |
| `stock_status` | `all`, `healthy`, `low`, `out` |
| `sort_by`      | `name`, `stock`, `value` |
| `skip`         | Number of records to skip |
| `limit`        | Number of records to return |
| `min_price`    | Minimum product price |
| `max_price`    | Maximum product price |

## GitHub Description

Recommended repository description:

```text
SaaS Product Management Dashboard built with FastAPI, SQLAlchemy, and React for product catalog CRUD, inventory health tracking, and dashboard metrics.
```

## Author

Aditya Singh
