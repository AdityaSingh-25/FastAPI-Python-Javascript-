from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import database_models
from main import app, get_db


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def setup_function():
    database_models.Base.metadata.drop_all(bind=engine)
    database_models.Base.metadata.create_all(bind=engine)


def test_product_crud_flow():
    create_response = client.post(
        "/products",
        json={
            "name": "Growth Plan",
            "description": "Collaboration plan for scaling teams",
            "price": 149,
            "quantity": 12,
        },
    )

    assert create_response.status_code == 201
    product = create_response.json()
    assert product["id"] > 0
    assert product["name"] == "Growth Plan"

    list_response = client.get("/products")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    update_response = client.put(
        f"/products/{product['id']}",
        json={
            "name": "Growth Plan Plus",
            "description": "Expanded package for product-led teams",
            "price": 199,
            "quantity": 4,
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["quantity"] == 4

    summary_response = client.get("/products/summary")
    assert summary_response.status_code == 200
    assert summary_response.json() == {
        "total_products": 1,
        "total_inventory": 4,
        "total_catalog_value": 796.0,
        "low_stock_count": 1,
        "out_of_stock_count": 0,
        "average_price": 199.0,
    }

    delete_response = client.delete(f"/products/{product['id']}")
    assert delete_response.status_code == 200
    assert client.get("/products").json() == []


def test_rejects_invalid_price_filter():
    response = client.get("/products?min_price=500&max_price=100")

    assert response.status_code == 400
    assert response.json()["detail"] == "min_price cannot be greater than max_price"


def test_filters_sorts_and_returns_insights():
    products = [
        {
            "name": "Starter Plan",
            "description": "Self-serve plan for smaller SaaS teams",
            "price": 49,
            "quantity": 30,
        },
        {
            "name": "Analytics Add-on",
            "description": "Advanced reporting module",
            "price": 89,
            "quantity": 3,
        },
        {
            "name": "Priority Support",
            "description": "Premium support package",
            "price": 199,
            "quantity": 0,
        },
    ]

    for product in products:
        assert client.post("/products", json=product).status_code == 201

    search_response = client.get("/products?search=analytics")
    assert search_response.status_code == 200
    assert [product["name"] for product in search_response.json()] == ["Analytics Add-on"]

    low_stock_response = client.get("/products?stock_status=low")
    assert low_stock_response.status_code == 200
    assert [product["name"] for product in low_stock_response.json()] == ["Analytics Add-on"]

    sorted_response = client.get("/products?sort_by=value")
    assert sorted_response.status_code == 200
    assert [product["name"] for product in sorted_response.json()] == [
        "Starter Plan",
        "Analytics Add-on",
        "Priority Support",
    ]

    insights_response = client.get("/products/insights")
    assert insights_response.status_code == 200
    insights = insights_response.json()
    assert insights["highest_value_product"]["name"] == "Starter Plan"
    assert [product["name"] for product in insights["reorder_recommendations"]] == [
        "Analytics Add-on"
    ]
    assert [product["name"] for product in insights["out_of_stock_products"]] == [
        "Priority Support"
    ]


def test_rejects_invalid_product_filters():
    stock_response = client.get("/products?stock_status=critical")
    sort_response = client.get("/products?sort_by=margin")

    assert stock_response.status_code == 400
    assert stock_response.json()["detail"] == "stock_status must be one of: all, healthy, low, out"
    assert sort_response.status_code == 400
    assert sort_response.json()["detail"] == "sort_by must be one of: name, stock, value"


def test_returns_404_for_missing_product():
    response = client.get("/products/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"
