from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLEnum, Index
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import enum
from .database import Base

class ContentType(enum.Enum):
    ARTICLE = "article"
    REDDIT = "reddit"
    TWEET = "tweet"

class Content(Base):
    __tablename__ = 'content'

    id = Column(Integer, primary_key=True)
    type = Column(SQLEnum(ContentType), nullable=False)
    url = Column(String(512), unique=True, nullable=False)
    title = Column(String(512), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    source = Column(String(100), nullable=False)
    scraped_at = Column(DateTime(timezone=True), nullable=False, index=True)
    extra_data = Column(JSONB, nullable=True, default={})

    # Add composite index for common queries
    __table_args__ = (
        Index('idx_type_scraped_at', type, scraped_at),
    )

    def to_dict(self):
        """Convert model instance to dictionary"""
        return {
            "id": self.id,
            "type": self.type.value,
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "summary": self.summary,
            "source": self.source,
            "scraped_at": self.scraped_at.isoformat(),
            "extra_data": self.extra_data or {}
        }