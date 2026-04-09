from fastapi import Depends, FastAPI, HTTPException
from models import Product
from database import Session, engine
import database_models
from sqlalchemy.orm import Session as DBSession
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

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


products = [
    # Product(1, "phone", "Iphone_X", 100, 15),
    Product(id=1, name="Product 1", description="Description of Product 1", price=10.99, quantity=100),
    Product(id=2, name="Product 2", description="Description of Product 2", price=19.99, quantity=50),
    Product(id=3, name="Product 3", description="Description of Product 3", price=5.99, quantity=200),
    Product(id=4, name="Product 4", description="Description of Product 4", price=6.99, quantity=250)
]


def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()


def init_db():
    db = Session()

    count = db.query(database_models.Product).count()  # Check if the products table is empty
    if count == 0:

        for product in products:
            """ We are creating an instance of the Product class defined in database_models.py and 
            populating it with data from the Product instance defined in models.py. This allows us to 
            add the product to the database using SQLAlchemy."""

            # db_product = database_models.Product( 
            #     id=product.id,
            #     name=product.name,
            #     description=product.description,
            #     price=product.price,
            #     quantity=product.quantity
            # )
            db.add(database_models.Product(**product.dict()))  
            #Using **product.dict() to unpack the attributes of the Product instance and pass 
            # them as keyword arguments to the database_models.Product constructor. 
            # This is a more concise way to create the database model instance without having to 
            # manually specify each attribute.

        db.commit()

init_db()


# GET ALL PRODUCTS
@app.get("/products")  
def get_all_products(db: DBSession = Depends(get_db)):

    db_products = db.query(database_models.Product).all()  # Query the database for all products
    return db_products  # Return the list of products as the response

    # # DB connection
    # db = Session()

    # # Query
    # db.query(Product).all()
    
    # return products   # ❌ unreachable, kept as comment


# GET PRODUCT BY ID
@app.get("/products/{id}")
def get_product_by_id(id: int, db: DBSession = Depends(get_db)):
    db_product = db.query(database_models.Product).filter(database_models.Product.id == id).first()  # Query the database for the product with the specified ID
    
    # for product in products:
    if db_product:
        return db_product  # Return the product if found
    
    raise HTTPException(status_code=404, detail="Product not found")


# ADD PRODUCT
@app.post("/products")
def add_product(product: Product, db: DBSession = Depends(get_db)):
    db.add(database_models.Product(**product.dict()))
    db.commit()
    return product


# UPDATE PRODUCT (FIXED ROUTE)
@app.put("/products/{id}")
def update_product(id: int, updated_product: Product, db: DBSession = Depends(get_db)):
    db_product = db.query(database_models.Product).filter(database_models.Product.id == id).first()

    if db_product:
        for key, value in updated_product.dict().items():
            setattr(db_product, key, value)
        db.commit()
        return db_product

    raise HTTPException(status_code=404, detail="Product not found")

    # for index, product in enumerate(products):
    #     if product.id == id:
    #         products[index] = updated_product
    #         return updated_product
    # return "Product not found"


# DELETE PRODUCT (FIXED ROUTE)
@app.delete("/products/{id}")
def delete_product(id: int, db: DBSession = Depends(get_db)):
    db_product = db.query(database_models.Product).filter(database_models.Product.id == id).first()

    if db_product:
        db.delete(db_product)
        db.commit()
        return {"message": "Product deleted successfully"}

    raise HTTPException(status_code=404, detail="Product not found")

    # for i in range(len(products)):
    #     if products[i].id == id:
    #         del products[i]
    #         return "Product deleted successfully" 
    # return "Product not found"