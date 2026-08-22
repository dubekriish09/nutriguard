from sqlalchemy import Column, Integer, String, Boolean, Numeric, ForeignKey, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .base import Base
import uuid

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    entity_version = Column(Integer)
    request_id = Column(String)
    metadata_json = Column(JSON, default=dict)
    timestamp = Column(DateTime(timezone=True), default=func.now(), nullable=False)
