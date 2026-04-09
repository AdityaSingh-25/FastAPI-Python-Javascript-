from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

db_url="postgresql://postgres:success@localhost:2525/project_X"
engine = create_engine(db_url)

Session=sessionmaker(autocommit=False, autoflush=False, bind=engine)