from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(String(50), default='knowledge')  # knowledge, work
    status = Column(String(50), default='pending')  # pending, in_progress, completed, paused
    priority = Column(String(50), default='normal')  # low, normal, high
    tags = Column(String(255))  # 逗号分隔
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    completed_at = Column(DateTime)
    attachments = relationship('Attachment', back_populates='task')

class Attachment(Base):
    __tablename__ = 'attachments'
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(255), nullable=False)
    filetype = Column(String(255))
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
    task_id = Column(Integer, ForeignKey('tasks.id'))
    task = relationship('Task', back_populates='attachments') 