from sqlalchemy import (Column, Integer, String, DateTime, BigInteger,
                        JSON, UniqueConstraint)
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Post(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, nullable=False)
    grouped_id = Column(BigInteger, index=True)
    channel_id = Column(BigInteger, nullable=False)
    channel_name = Column(String(255))
    post_text = Column(String)
    post_date = Column(DateTime(timezone=True), nullable=False)
    views = Column(Integer)
    reactions_count = Column(Integer, default=0)
    link = Column(String(255))
    raw_data = Column(JSON)
    photo_path = Column(String(255))
    video_path = Column(String(255))
    photo_paths = Column(JSON)
    video_paths = Column(JSON)
    __table_args__ = (UniqueConstraint('channel_id', 'message_id', name='_channel_message_uc'),)

class SyncedChannel(Base):
    __tablename__ = 'synced_channels'
    id = Column(Integer, primary_key=True)
    channel_id = Column(BigInteger, unique=True, nullable=False)