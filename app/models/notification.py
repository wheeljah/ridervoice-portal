"""
Notification raw data model
"""
from sqlalchemy import Column, Integer, String, Text, BigInteger
from app.database import Base


class NotificationRawData(Base):
    __tablename__ = "notification_raw_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(255), nullable=False, index=True)
    app_package = Column(String(255), nullable=False, index=True)
    app_name = Column(String(255), nullable=True)
    title = Column(Text, nullable=True)
    text = Column(Text, nullable=True)
    sub_text = Column(Text, nullable=True)
    big_text = Column(Text, nullable=True)
    extra_text = Column(Text, nullable=True)
    raw_data = Column(Text, nullable=True)
    timestamp = Column(BigInteger, nullable=False, index=True)
    created_at = Column(BigInteger, nullable=True)
