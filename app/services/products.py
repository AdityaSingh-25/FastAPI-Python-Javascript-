"""Product domain logic.

This layer is framework-agnostic: it talks to the database and raises plain
domain exceptions. The router layer maps those exceptions onto HTTP responses.
"""

import csv
import io
from typing import List, Optional, Tuple

from pydantic import ValidationError
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import db_models
from app.config import get_settings
from app.schemas import ProductCreate

settings = get_settings()

STOCK_STATUSES = {"all", "healthy", "low", "out"}
SORT_FIELDS = {"name", "stock", "value", "price"}
REQUIRED_CSV_COLUMNS = {"name", "description", "price", "quantity"}


class ProductNotFound(Exception):
    pass


class InvalidStockAdjustment(Exception):
    pass


class CsvImportError(Exception):
    pass


def get_stock_status(quantity: int) -> str:
    if quantity == 0:
        return "out"
    if quantity <= settings.low_stock_threshold:
        return "low"
    return "healthy"


def list_products(
    db: Session,
    *,
    skip: int,
    limit: int,
    min_price: float,
    max_price: float,
    search: str,
    stock_status: str,
    category: str,
    sort_by: str,
) -> Tuple[List[db_models.Product], int]:
    query = (
        db.query(db_models.Product)
        .filter(db_models.Product.price >= min_price)
        .filter(db_models.Product.price <= max_price)
    )

    if category.strip():
        query = query.filter(db_models.Product.category == category.strip())

    if search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                db_models.Product.name.ilike(term),
                db_models.Product.description.ilike(term),
            )
        )

    products = query.all()

    if stock_status != "all":
        products = [p for p in products if get_stock_status(p.quantity) == stock_status]

    if sort_by == "value":
        products.sort(key=lambda p: p.price * p.quantity, reverse=True)
    elif sort_by == "stock":
        products.sort(key=lambda p: p.quantity)
    elif sort_by == "price":
        products.sort(key=lambda p: p.price, reverse=True)
    else:
        products.sort(key=lambda p: p.name.lower())

    total = len(products)
    return products[skip:skip + limit], total


def summarize(db: Session) -> dict:
    products = db.query(db_models.Product).all()
    total_inventory = sum(p.quantity for p in products)
    total_catalog_value = sum(p.price * p.quantity for p in products)
    low_stock_count = sum(1 for p in products if get_stock_status(p.quantity) == "low")
    out_of_stock_count = sum(1 for p in products if get_stock_status(p.quantity) == "out")
    average_price = sum(p.price for p in products) / len(products) if products else 0

    breakdown = {}
    for p in products:
        name = p.category or "Uncategorized"
        stat = breakdown.setdefault(
            name, {"product_count": 0, "total_inventory": 0, "total_catalog_value": 0.0}
        )
        stat["product_count"] += 1
        stat["total_inventory"] += p.quantity
        stat["total_catalog_value"] += p.price * p.quantity

    category_breakdown = [
        {
            "category": name,
            "product_count": stat["product_count"],
            "total_inventory": stat["total_inventory"],
            "total_catalog_value": round(stat["total_catalog_value"], 2),
        }
        for name, stat in sorted(breakdown.items(), key=lambda item: item[0].lower())
    ]

    return {
        "total_products": len(products),
        "total_inventory": total_inventory,
        "total_catalog_value": round(total_catalog_value, 2),
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "average_price": round(average_price, 2),
        "category_breakdown": category_breakdown,
    }


def insights(db: Session) -> dict:
    products = db.query(db_models.Product).all()
    highest_value_product = max(
        products, key=lambda p: p.price * p.quantity, default=None
    )
    reorder = [p for p in products if get_stock_status(p.quantity) == "low"]
    out_of_stock = [p for p in products if get_stock_status(p.quantity) == "out"]

    reorder.sort(key=lambda p: p.quantity)
    out_of_stock.sort(key=lambda p: p.name.lower())

    return {
        "highest_value_product": highest_value_product,
        "reorder_recommendations": reorder,
        "out_of_stock_products": out_of_stock,
    }


def list_categories(db: Session) -> List[str]:
    rows = db.query(db_models.Product.category).distinct().all()
    return sorted(
        {(row[0] or "Uncategorized") for row in rows}, key=lambda name: name.lower()
    )


def get_product(db: Session, product_id: int) -> db_models.Product:
    product = (
        db.query(db_models.Product)
        .filter(db_models.Product.id == product_id)
        .first()
    )
    if not product:
        raise ProductNotFound(f"Product {product_id} not found")
    return product


def create_product(db: Session, data: ProductCreate) -> db_models.Product:
    product = db_models.Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product_id: int, data: ProductCreate) -> db_models.Product:
    product = get_product(db, product_id)
    for key, value in data.model_dump().items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: int) -> None:
    product = get_product(db, product_id)
    db.delete(product)
    db.commit()


def adjust_stock(db: Session, product_id: int, delta: int) -> db_models.Product:
    product = get_product(db, product_id)
    new_quantity = product.quantity + delta
    if new_quantity < 0:
        raise InvalidStockAdjustment("Stock cannot be reduced below zero")
    product.quantity = new_quantity
    db.commit()
    db.refresh(product)
    return product


def import_csv(db: Session, raw: bytes, filename: Optional[str]) -> Tuple[int, list]:
    if not filename or not filename.lower().endswith(".csv"):
        raise CsvImportError("File must be a .csv")

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvImportError("File must be UTF-8 encoded") from exc

    reader = csv.DictReader(io.StringIO(text))
    headers = {h.strip() for h in (reader.fieldnames or [])}
    if not REQUIRED_CSV_COLUMNS.issubset(headers):
        raise CsvImportError(
            "CSV must include columns: name, description, price, quantity"
        )

    errors = []
    pending = []

    # Row 1 is the header, so data rows start at line 2.
    for offset, row in enumerate(reader, start=2):
        clean = {key.strip(): (value or "").strip() for key, value in row.items() if key}
        payload = {field: clean.get(field, "") for field in REQUIRED_CSV_COLUMNS}
        if clean.get("category"):
            payload["category"] = clean["category"]

        try:
            product = ProductCreate(**payload)
        except ValidationError as exc:
            first = exc.errors()[0]
            field = first["loc"][0] if first.get("loc") else "row"
            errors.append({"row": offset, "error": f"{field}: {first['msg']}"})
            continue

        pending.append(db_models.Product(**product.model_dump()))

    if pending:
        db.add_all(pending)
        db.commit()

    return len(pending), errors
