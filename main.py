from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from sqlalchemy import or_
from sqlalchemy.orm import Session as DBSession
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List
from pydantic import ValidationError
import csv
import io
import logging

import database_models
from database import Session, engine
from models import (
    CategoryStat,
    ImportResult,
    ImportRowError,
    ProductCreate,
    ProductInsights,
    ProductResponse,
    ProductSummary,
    StockAdjustment,
)

LOW_STOCK_THRESHOLD = 5


@asynccontextmanager
async def lifespan(app: FastAPI):
    database_models.Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="SaaS Product Management Dashboard API",
    summary="Inventory and catalog management APIs for a SaaS product operations dashboard.",
    version="1.0.0",
    lifespan=lifespan,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def greet():
    return {
        "name": "SaaS Product Management Dashboard",
        "status": "ready",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()


def to_product_response(p):
    return ProductResponse.model_validate(p)


def get_stock_status(quantity: int):
    if quantity == 0:
        return "out"
    if quantity <= LOW_STOCK_THRESHOLD:
        return "low"
    return "healthy"


@app.get("/products", response_model=List[ProductResponse])
def get_all_products(
    skip: int = 0,
    limit: int = Query(default=100, ge=1, le=500),
    min_price: float = Query(default=0, ge=0),
    max_price: float = Query(default=100000, ge=0),
    search: str = "",
    stock_status: str = "all",
    category: str = "",
    sort_by: str = "name",
    db: DBSession = Depends(get_db)
):
    logger.info(
        "Fetching products | skip=%s, limit=%s, price=%s-%s, search=%s, stock=%s, category=%s, sort=%s",
        skip,
        limit,
        min_price,
        max_price,
        search,
        stock_status,
        category,
        sort_by,
    )

    if min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_price cannot be greater than max_price"
        )

    if stock_status not in {"all", "healthy", "low", "out"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="stock_status must be one of: all, healthy, low, out",
        )

    if sort_by not in {"name", "stock", "value", "price"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sort_by must be one of: name, stock, value, price",
        )

    query = (
        db.query(database_models.Product)
        .filter(database_models.Product.price >= min_price)
        .filter(database_models.Product.price <= max_price)
    )

    if category.strip():
        query = query.filter(database_models.Product.category == category.strip())

    if search.strip():
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                database_models.Product.name.ilike(search_term),
                database_models.Product.description.ilike(search_term),
            )
        )

    if stock_status == "healthy":
        query = query.filter(database_models.Product.quantity > LOW_STOCK_THRESHOLD)
    elif stock_status == "low":
        query = query.filter(
            database_models.Product.quantity > 0,
            database_models.Product.quantity <= LOW_STOCK_THRESHOLD,
        )
    elif stock_status == "out":
        query = query.filter(database_models.Product.quantity == 0)

    products = query.all()

    if sort_by == "value":
        products.sort(key=lambda product: product.price * product.quantity, reverse=True)
    elif sort_by == "stock":
        products.sort(key=lambda product: product.quantity)
    elif sort_by == "price":
        products.sort(key=lambda product: product.price, reverse=True)
    else:
        products.sort(key=lambda product: product.name.lower())

    products = products[skip:skip + limit]

    return [to_product_response(p) for p in products]


@app.get("/products/summary", response_model=ProductSummary)
def get_product_summary(db: DBSession = Depends(get_db)):
    products = db.query(database_models.Product).all()
    total_inventory = sum(product.quantity for product in products)
    total_catalog_value = sum(product.price * product.quantity for product in products)
    low_stock_count = sum(1 for product in products if get_stock_status(product.quantity) == "low")
    out_of_stock_count = sum(1 for product in products if get_stock_status(product.quantity) == "out")
    average_price = sum(product.price for product in products) / len(products) if products else 0

    breakdown = {}
    for product in products:
        name = product.category or "Uncategorized"
        stat = breakdown.setdefault(
            name,
            {"product_count": 0, "total_inventory": 0, "total_catalog_value": 0.0},
        )
        stat["product_count"] += 1
        stat["total_inventory"] += product.quantity
        stat["total_catalog_value"] += product.price * product.quantity

    category_breakdown = [
        CategoryStat(
            category=name,
            product_count=stat["product_count"],
            total_inventory=stat["total_inventory"],
            total_catalog_value=round(stat["total_catalog_value"], 2),
        )
        for name, stat in sorted(breakdown.items(), key=lambda item: item[0].lower())
    ]

    return ProductSummary(
        total_products=len(products),
        total_inventory=total_inventory,
        total_catalog_value=round(total_catalog_value, 2),
        low_stock_count=low_stock_count,
        out_of_stock_count=out_of_stock_count,
        average_price=round(average_price, 2),
        category_breakdown=category_breakdown,
    )


@app.get("/products/categories", response_model=List[str])
def get_categories(db: DBSession = Depends(get_db)):
    rows = (
        db.query(database_models.Product.category)
        .distinct()
        .all()
    )
    categories = sorted(
        {(row[0] or "Uncategorized") for row in rows}, key=lambda name: name.lower()
    )
    return categories


@app.get("/products/insights", response_model=ProductInsights)
def get_product_insights(db: DBSession = Depends(get_db)):
    products = db.query(database_models.Product).all()
    highest_value_product = max(
        products,
        key=lambda product: product.price * product.quantity,
        default=None,
    )
    reorder_recommendations = [
        product for product in products if get_stock_status(product.quantity) == "low"
    ]
    out_of_stock_products = [
        product for product in products if get_stock_status(product.quantity) == "out"
    ]

    reorder_recommendations.sort(key=lambda product: product.quantity)
    out_of_stock_products.sort(key=lambda product: product.name.lower())

    return ProductInsights(
        highest_value_product=to_product_response(highest_value_product)
        if highest_value_product else None,
        reorder_recommendations=[
            to_product_response(product) for product in reorder_recommendations
        ],
        out_of_stock_products=[
            to_product_response(product) for product in out_of_stock_products
        ],
    )


@app.get("/products/{id}", response_model=ProductResponse)
def get_product_by_id(id: int, db: DBSession = Depends(get_db)):
    product = db.query(database_models.Product)\
        .filter(database_models.Product.id == id)\
        .first()

    if not product:
        logger.warning(f"Product not found: ID={id}")
        raise HTTPException(status_code=404, detail="Product not found")

    return to_product_response(product)


@app.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def add_product(product: ProductCreate, db: DBSession = Depends(get_db)):

    try:
        db_product = database_models.Product(**product.model_dump())

        db.add(db_product)
        db.commit()
        db.refresh(db_product)

        logger.info(f"Product created: ID={db_product.id}")

        return to_product_response(db_product)

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating product: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create product")


@app.put("/products/{id}", response_model=ProductResponse)
def update_product(id: int, updated_product: ProductCreate, db: DBSession = Depends(get_db)):

    db_product = db.query(database_models.Product)\
        .filter(database_models.Product.id == id)\
        .first()

    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        for key, value in updated_product.model_dump().items():
            setattr(db_product, key, value)

        db.commit()
        db.refresh(db_product)

        logger.info(f"Product updated: ID={id}")

        return to_product_response(db_product)

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating product {id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update product")


@app.delete("/products/{id}", status_code=status.HTTP_200_OK)
def delete_product(id: int, db: DBSession = Depends(get_db)):

    db_product = db.query(database_models.Product)\
        .filter(database_models.Product.id == id)\
        .first()

    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        db.delete(db_product)
        db.commit()

        logger.info(f"Product deleted: ID={id}")

        return {"message": "Product deleted successfully"}

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting product {id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete product")


@app.patch("/products/{id}/stock", response_model=ProductResponse)
def adjust_stock(id: int, adjustment: StockAdjustment, db: DBSession = Depends(get_db)):
    db_product = db.query(database_models.Product)\
        .filter(database_models.Product.id == id)\
        .first()

    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    new_quantity = db_product.quantity + adjustment.delta
    if new_quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stock cannot be reduced below zero",
        )

    try:
        db_product.quantity = new_quantity
        db.commit()
        db.refresh(db_product)

        logger.info(f"Stock adjusted: ID={id}, delta={adjustment.delta}, quantity={new_quantity}")

        return to_product_response(db_product)

    except Exception as e:
        db.rollback()
        logger.error(f"Error adjusting stock for product {id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to adjust stock")


@app.post("/products/import", response_model=ImportResult, status_code=status.HTTP_201_CREATED)
async def import_products(file: UploadFile = File(...), db: DBSession = Depends(get_db)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a .csv",
        )

    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be UTF-8 encoded",
        )

    reader = csv.DictReader(io.StringIO(text))
    required = {"name", "description", "price", "quantity"}
    if not reader.fieldnames or not required.issubset({h.strip() for h in reader.fieldnames}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV must include columns: name, description, price, quantity",
        )

    created = 0
    errors: List[ImportRowError] = []
    pending = []

    # Row 1 is the header, so data rows start at line 2.
    for offset, row in enumerate(reader, start=2):
        raw_row = {key.strip(): (value or "").strip() for key, value in row.items() if key}
        payload = {
            "name": raw_row.get("name", ""),
            "description": raw_row.get("description", ""),
            "price": raw_row.get("price", ""),
            "quantity": raw_row.get("quantity", ""),
        }
        category = raw_row.get("category", "")
        if category:
            payload["category"] = category

        try:
            product = ProductCreate(**payload)
        except ValidationError as exc:
            first = exc.errors()[0]
            field = first["loc"][0] if first.get("loc") else "row"
            errors.append(ImportRowError(row=offset, error=f"{field}: {first['msg']}"))
            continue

        pending.append(database_models.Product(**product.model_dump()))

    if pending:
        try:
            db.add_all(pending)
            db.commit()
            created = len(pending)
        except Exception as e:
            db.rollback()
            logger.error(f"Error importing products: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to import products")

    logger.info(f"Imported {created} products with {len(errors)} errors")

    return ImportResult(created=created, failed=len(errors), errors=errors)
