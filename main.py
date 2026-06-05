from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.orm import Session as DBSession
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import logging

import database_models
from database import Session, engine
from models import ProductCreate, ProductResponse, ProductSummary

app = FastAPI(
    title="SaaS Product Management Dashboard API",
    summary="Inventory and catalog management APIs for a SaaS product operations dashboard.",
    version="1.0.0",
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

database_models.Base.metadata.create_all(bind=engine)


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
    return ProductResponse(
        id=p.id,
        name=p.name,
        description=p.description,
        price=p.price,
        quantity=p.quantity
    )


@app.get("/products", response_model=List[ProductResponse])
def get_all_products(
    skip: int = 0,
    limit: int = Query(default=100, ge=1, le=500),
    min_price: float = Query(default=0, ge=0),
    max_price: float = Query(default=100000, ge=0),
    db: DBSession = Depends(get_db)
):
    logger.info(f"Fetching products | skip={skip}, limit={limit}, price={min_price}-{max_price}")

    if min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_price cannot be greater than max_price"
        )

    products = (
        db.query(database_models.Product)
        .filter(database_models.Product.price >= min_price)
        .filter(database_models.Product.price <= max_price)
        .order_by(database_models.Product.id.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [to_product_response(p) for p in products]


@app.get("/products/summary", response_model=ProductSummary)
def get_product_summary(db: DBSession = Depends(get_db)):
    products = db.query(database_models.Product).all()
    total_inventory = sum(product.quantity for product in products)
    total_catalog_value = sum(product.price * product.quantity for product in products)
    low_stock_count = sum(1 for product in products if product.quantity <= 5)

    return ProductSummary(
        total_products=len(products),
        total_inventory=total_inventory,
        total_catalog_value=round(total_catalog_value, 2),
        low_stock_count=low_stock_count,
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
