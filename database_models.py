# from sqlalchemy import Column, Integer, String, Float, DateTime
# from sqlalchemy.ext.declarative import declarative_base
# from datetime import datetime

# Base = declarative_base()

# class Product(Base):
#     __tablename__ = "products"

#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String)
#     description = Column(String)
#     price = Column(Float)
#     quantity = Column(Integer)

#     created_at = Column(DateTime, default=datetime.utcnow)  
#     # NEW: Automatically store when product was created

from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Product(Base):

    __tablename__ = "products"

    #  AUTO-INCREMENT PRIMARY KEY
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    name = Column(String)
    description = Column(String)
    price = Column(Float)
    quantity = Column(Integer)