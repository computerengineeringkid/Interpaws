import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Resolve database URL from environment (Docker Compose sets DATABASE_URL)
# Fallback to localhost for non-Docker local development.
SQLALCHEMY_DATABASE_URL = os.getenv(
	"DATABASE_URL",
	"postgresql://user:password@localhost/interpawsdb",
)

# Create the SQLAlchemy engine
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create a SessionLocal class. Each instance of this will be a new database session.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a Base class. Our database models will inherit from this class.
Base = declarative_base()
