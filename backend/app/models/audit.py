from sqlalchemy import Column, String, Float, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime

from ..db.base import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    request_id = Column(String, nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    route = Column(String, nullable=False, index=True)
    model_version = Column(String, nullable=False, index=True)
    response_type = Column(String, nullable=False)  # 'forecast', 'opportunity', 'prediction'
    confidence = Column(Float, nullable=False)
    disclaimer_version = Column(String, nullable=False, default="1.0")
    latency_ms = Column(Integer, nullable=False, default=0)
    metadata = Column(JSONB, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationship
    user = relationship("User", back_populates="audit_logs")
