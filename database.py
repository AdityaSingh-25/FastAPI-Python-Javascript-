

import os
from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

#  Load environment variables from .env
load_dotenv()

# Get DB URL securely
db_url = os.getenv("DATABASE_URL")

#  Fail FAST if missing (very important in real systems)
if not db_url:
    raise ValueError("DATABASE_URL is not set. Check your .env file.")

#  Create engine
engine = create_engine(db_url)

#  Create session
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)