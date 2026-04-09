from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session as DBSession
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import logging

import database_models
from database import Session, engine
from models import ProductCreate, ProductResponse

# Initialize app
app = FastAPI()

# Logging setup (NEW)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CORS middleware (same)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create DB tables
database_models.Base.metadata.create_all(bind=engine)


@app.get("/")
def greet():
    return "Welcome to Project X"


# Dependency to get DB session
def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()


# 🔥 GET ALL PRODUCTS (UPGRADED)
@app.get("/products", response_model=List[ProductResponse])
def get_all_products(
    skip: int = 0,              # NEW: Pagination start
    limit: int = 10,            # NEW: Pagination size
    min_price: float = 0,       # NEW: Filter by price range
    max_price: float = 100000,
    db: DBSession = Depends(get_db)
):
    logger.info("Fetching products with filters")


    return (
        db.query(database_models.Product)  
        # Start a database query on the Product table

        .filter(database_models.Product.price >= min_price)  
        # Apply filter: include only products with price >= min_price

        .filter(database_models.Product.price <= max_price)  
        # Apply filter: include only products with price <= max_price

        .order_by(database_models.Product.id.asc())  
        # Sort results in ascending order of product ID (1 → 2 → 3 ...)

        .offset(skip)  
        # Skip the first 'skip' number of records (used for pagination)

        .limit(limit)  
        # Limit the number of records returned (pagination size)

        .all()  
        # Execute the query and return all matching results as a list
)


# 🔥 GET PRODUCT BY ID (IMPROVED ERROR HANDLING)
@app.get("/products/{id}", response_model=ProductResponse)
def get_product_by_id(id: int, db: DBSession = Depends(get_db)):
    product = db.query(database_models.Product)\
        .filter(database_models.Product.id == id)\
        .first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


# 🔥 CREATE PRODUCT (USING NEW SCHEMA)
@app.post("/products", response_model=ProductResponse)
def add_product(product: ProductCreate, db: DBSession = Depends(get_db)):
    db_product = database_models.Product(**product.dict())  
    # NEW: Convert Pydantic → SQLAlchemy

    db.add(db_product)
    db.commit()
    db.refresh(db_product)  
    # NEW: Get updated object with ID

    return db_product


# 🔥 UPDATE PRODUCT (RESTFUL + CLEAN)
@app.put("/products/{id}", response_model=ProductResponse)
def update_product(id: int, updated_product: ProductCreate, db: DBSession = Depends(get_db)):
    db_product = db.query(database_models.Product)\
        .filter(database_models.Product.id == id)\
        .first()

    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Update fields dynamically
    for key, value in updated_product.dict().items():
        setattr(db_product, key, value)

    db.commit()
    db.refresh(db_product)

    return db_product


# 🔥 DELETE PRODUCT (IMPROVED RESPONSE)
@app.delete("/products/{id}")
def delete_product(id: int, db: DBSession = Depends(get_db)):
    db_product = db.query(database_models.Product)\
        .filter(database_models.Product.id == id)\
        .first()

    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(db_product)
    db.commit()

    return {"message": "Product deleted successfully"}