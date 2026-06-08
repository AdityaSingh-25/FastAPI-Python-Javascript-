from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import db_models
from app.dependencies import get_db
from app.main import app


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
    db_models.Base.metadata.drop_all(bind=engine)
    db_models.Base.metadata.create_all(bind=engine)


def items(response):
    return response.json()["items"]


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
    assert list_response.json()["total"] == 1
    assert len(items(list_response)) == 1

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
        "category_breakdown": [
            {
                "category": "Uncategorized",
                "product_count": 1,
                "total_inventory": 4,
                "total_catalog_value": 796.0,
            }
        ],
    }

    delete_response = client.delete(f"/products/{product['id']}")
    assert delete_response.status_code == 200
    assert items(client.get("/products")) == []


def test_rejects_invalid_price_filter():
    response = client.get("/products?min_price=500&max_price=100")

    assert response.status_code == 400
    assert response.json()["detail"] == "min_price cannot be greater than max_price"


def test_pagination_metadata():
    _seed(
        [
            {"name": f"Item {i}", "description": "Paginated product", "price": 10 + i, "quantity": 5}
            for i in range(5)
        ]
    )

    response = client.get("/products?skip=2&limit=2")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 5
    assert body["skip"] == 2
    assert body["limit"] == 2
    assert len(body["items"]) == 2


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
    assert [product["name"] for product in items(search_response)] == ["Analytics Add-on"]

    low_stock_response = client.get("/products?stock_status=low")
    assert low_stock_response.status_code == 200
    assert [product["name"] for product in items(low_stock_response)] == ["Analytics Add-on"]

    sorted_response = client.get("/products?sort_by=value")
    assert sorted_response.status_code == 200
    assert [product["name"] for product in items(sorted_response)] == [
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
    assert sort_response.json()["detail"] == "sort_by must be one of: name, stock, value, price"


def test_returns_404_for_missing_product():
    response = client.get("/products/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


def _seed(products):
    for product in products:
        assert client.post("/products", json=product).status_code == 201


def test_category_filter_and_listing():
    _seed(
        [
            {
                "name": "Starter Plan",
                "description": "Self-serve plan",
                "price": 49,
                "quantity": 30,
                "category": "Subscription",
            },
            {
                "name": "Analytics Add-on",
                "description": "Reporting module",
                "price": 89,
                "quantity": 8,
                "category": "Add-on",
            },
            {
                "name": "Growth Plan",
                "description": "Plan for scaling teams",
                "price": 149,
                "quantity": 12,
                "category": "Subscription",
            },
        ]
    )

    categories_response = client.get("/products/categories")
    assert categories_response.status_code == 200
    assert categories_response.json() == ["Add-on", "Subscription"]

    filtered = client.get("/products?category=Subscription")
    assert filtered.status_code == 200
    assert sorted(product["name"] for product in items(filtered)) == ["Growth Plan", "Starter Plan"]


def test_category_defaults_to_uncategorized():
    response = client.post(
        "/products",
        json={
            "name": "Mystery Box",
            "description": "No category provided",
            "price": 25,
            "quantity": 4,
        },
    )

    assert response.status_code == 201
    assert response.json()["category"] == "Uncategorized"


def test_sort_by_price():
    _seed(
        [
            {"name": "Cheap", "description": "Low cost item", "price": 10, "quantity": 5},
            {"name": "Pricey", "description": "High cost item", "price": 500, "quantity": 5},
            {"name": "Mid", "description": "Mid cost item", "price": 100, "quantity": 5},
        ]
    )

    response = client.get("/products?sort_by=price")
    assert response.status_code == 200
    assert [product["name"] for product in items(response)] == ["Pricey", "Mid", "Cheap"]


def test_stock_adjustment():
    created = client.post(
        "/products",
        json={
            "name": "Restock Me",
            "description": "Needs more stock",
            "price": 30,
            "quantity": 2,
        },
    )
    product_id = created.json()["id"]

    increase = client.patch(f"/products/{product_id}/stock", json={"delta": 10})
    assert increase.status_code == 200
    assert increase.json()["quantity"] == 12

    decrease = client.patch(f"/products/{product_id}/stock", json={"delta": -4})
    assert decrease.status_code == 200
    assert decrease.json()["quantity"] == 8

    below_zero = client.patch(f"/products/{product_id}/stock", json={"delta": -100})
    assert below_zero.status_code == 400
    assert below_zero.json()["detail"] == "Stock cannot be reduced below zero"

    missing = client.patch("/products/999/stock", json={"delta": 1})
    assert missing.status_code == 404


def test_csv_import_creates_and_reports_errors():
    csv_content = (
        "name,description,price,quantity,category\n"
        "Imported Plan,Imported via CSV,120,15,Subscription\n"
        "Add-on Pack,Bundle of add-ons,40,7,Add-on\n"
        "B,Too short name,10,1,Misc\n"
        "Bad Price,Invalid price value,-5,3,Misc\n"
    )

    response = client.post(
        "/products/import",
        files={"file": ("products.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 201
    result = response.json()
    assert result["created"] == 2
    assert result["failed"] == 2
    assert {error["row"] for error in result["errors"]} == {4, 5}

    listed = client.get("/products")
    assert sorted(product["name"] for product in items(listed)) == ["Add-on Pack", "Imported Plan"]


def test_csv_import_rejects_missing_columns():
    response = client.post(
        "/products/import",
        files={"file": ("bad.csv", "name,price\nWidget,10\n", "text/csv")},
    )

    assert response.status_code == 400
    assert "must include columns" in response.json()["detail"]


def test_product_response_includes_timestamps():
    created = client.post(
        "/products",
        json={
            "name": "Timestamped",
            "description": "Has audit fields",
            "price": 60,
            "quantity": 9,
        },
    )

    body = created.json()
    assert body["created_at"] is not None
    assert body["updated_at"] is not None
