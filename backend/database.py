from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

SQLALCHEMY_DATABASE_URL = "sqlite:///./financial_intelligence.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from models import Transaction, MonthlyAggregate, CategoryAggregate, YearlyAggregate, MonthlyNote  # noqa: F401
    import models_investment  # noqa: F401  — registers Investment, Holding, Liability, Goal, CategoryTagOverride
    Base.metadata.create_all(bind=engine)
