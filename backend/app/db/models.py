import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    topic = Column(String(500), nullable=False)
    year_from = Column(Integer, nullable=False)
    year_to = Column(Integer, nullable=False)
    paper_limit = Column(Integer, nullable=False, default=10)
    language = Column(String(10), nullable=False, default="zh")
    status = Column(String(20), nullable=False, default="pending")
    current_phase = Column(String(50), nullable=True)
    progress = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    papers = relationship("Paper", back_populates="task", cascade="all, delete-orphan")
    review = relationship("Review", back_populates="task", uselist=False, cascade="all, delete-orphan")


class Paper(Base):
    __tablename__ = "papers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False)
    paper_index = Column(Integer, nullable=False)
    title = Column(String(1000), nullable=False)
    authors = Column(JSON, nullable=True)
    year = Column(Integer, nullable=True)
    abstract = Column(Text, nullable=True)
    source = Column(String(50), nullable=False)
    url = Column(String(1000), nullable=True)
    citation_count = Column(Integer, default=0)
    embedding = Column(JSON, nullable=True)
    relevance_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="papers")
    analysis = relationship("PaperAnalysis", back_populates="paper", uselist=False, cascade="all, delete-orphan")


class PaperAnalysis(Base):
    __tablename__ = "paper_analyses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    paper_id = Column(String(36), ForeignKey("papers.id"), nullable=False)
    problem = Column(Text, nullable=True)
    method = Column(Text, nullable=True)
    contribution = Column(Text, nullable=True)
    limitation = Column(Text, nullable=True)
    dataset = Column(String(500), nullable=True)
    category = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    paper = relationship("Paper", back_populates="analysis")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False, unique=True)
    outline = Column(JSON, nullable=True)
    content = Column(Text, nullable=True)
    valid_citations = Column(JSON, nullable=True)
    invalid_citations = Column(JSON, nullable=True)
    citation_report = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="review")
