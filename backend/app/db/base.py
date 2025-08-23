"""
SQLAlchemy Base and model imports for Alembic.
"""

from sqlalchemy.ext.declarative import declarative_base

# SQLAlchemy declarative base
Base = declarative_base()

# Import all models here so Alembic can detect them
from app.models.user import User
from app.models.property import Property
from app.models.forecast import Forecast
from app.models.opportunity import Opportunity
from app.models.subscription import Subscription

# Make models available for import
__all__ = [
    "Base",
    "User", 
    "Property",
    "Forecast", 
    "Opportunity",
    "Subscription"
]
