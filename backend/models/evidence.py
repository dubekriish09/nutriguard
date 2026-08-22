from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .base import Base
import uuid

class DataSource(Base):
    __tablename__ = 'data_sources'
    
    source_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    short_name = Column(String, unique=True, nullable=False)
    organization = Column(String, nullable=False)
    source_type = Column(String)
    title = Column(String)
    publication = Column(String)
    doi = Column(String)
    url = Column(String)
    publication_date = Column(Date)
    accessed_date = Column(Date)
    version_or_edition = Column(String)
    evidence_level = Column(String, nullable=False)
    notes = Column(String)
    is_active = Column(Boolean, default=True)

class Evidence(Base):
    __tablename__ = 'evidence'
    
    evidence_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.source_id'), nullable=False)
    
    title = Column(String)
    citation = Column(String)
    evidence_summary = Column(String, nullable=False)
    relevant_quote = Column(String)
    page_or_section = Column(String)
    evidence_level = Column(String, nullable=False)
    
    version = Column(String, default="1")
    reviewer = Column(String)
    reviewed_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))
    reviewed_at = Column(DateTime(timezone=True))
    
    status = Column(String, default="UNVERIFIED")
    notes = Column(String)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

class RuleEvidence(Base):
    __tablename__ = 'rule_evidence'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey('rules.rule_id'))
    cn_rule_id = Column(UUID(as_uuid=True), ForeignKey('condition_nutrition_rules.cn_rule_id'))
    interaction_id = Column(UUID(as_uuid=True), ForeignKey('drug_food_interactions.interaction_id'))
    
    evidence_id = Column(UUID(as_uuid=True), ForeignKey('evidence.evidence_id'), nullable=False)
    relationship_type = Column(String, default="supports")
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
