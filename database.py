
import os
from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

load_dotenv()

db_url = os.getenv("DATABASE_URL", "sqlite:///./saas_products.db")
connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}

engine = create_engine(db_url, connect_args=connect_args)
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
