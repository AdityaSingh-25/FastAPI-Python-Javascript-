from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session as DBSession
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import logging

import database_models
from database import Session, engine
from models import ProductCreate, ProductResponse

app = FastAPI()

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
    return "Welcome to Project X"


def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()


#  HELPER FUNCTION (NEW)
def to_product_response(p):
    return ProductResponse(
        id=p.id,
        name=p.name,
        description=p.description,
        price=p.price,
        quantity=p.quantity
    )
    #  Converts SQLAlchemy object → Pydantic model
    # Fixes "value is not a valid dict" error


# GET ALL PRODUCTS (FIXED)
@app.get("/products", response_model=List[ProductResponse])
def get_all_products(
    skip: int = 0,
    limit: int = 10,
    min_price: float = 0,
    max_price: float = 100000,
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
    #  FIX: Manual conversion avoids FastAPI serialization issues


# GET PRODUCT BY ID (FIXED)
@app.get("/products/{id}", response_model=ProductResponse)
def get_product_by_id(id: int, db: DBSession = Depends(get_db)):
    product = db.query(database_models.Product)\
        .filter(database_models.Product.id == id)\
        .first()

    if not product:
        logger.warning(f"Product not found: ID={id}")
        raise HTTPException(status_code=404, detail="Product not found")

    return to_product_response(product)
    #  FIX: Explicit conversion


# CREATE PRODUCT (FIXED)
@app.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def add_product(product: ProductCreate, db: DBSession = Depends(get_db)):

    try:
        db_product = database_models.Product(**product.dict())

        db.add(db_product)
        db.commit()
        db.refresh(db_product)

        logger.info(f"Product created: ID={db_product.id}")

        return to_product_response(db_product)
        #  FIX: return converted object

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating product: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create product")


# UPDATE PRODUCT (FIXED)
@app.put("/products/{id}", response_model=ProductResponse)
def update_product(id: int, updated_product: ProductCreate, db: DBSession = Depends(get_db)):

    db_product = db.query(database_models.Product)\
        .filter(database_models.Product.id == id)\
        .first()

    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        for key, value in updated_product.dict().items():
            setattr(db_product, key, value)

        db.commit()
        db.refresh(db_product)

        logger.info(f"Product updated: ID={id}")

        return to_product_response(db_product)
        #  FIX: return converted object

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating product {id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update product")


# DELETE PRODUCT (unchanged)
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