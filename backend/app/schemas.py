from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class TaskCreate(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500, description="Research topic")
    year_from: int = Field(..., ge=1900, le=2030, description="Start year")
    year_to: int = Field(..., ge=1900, le=2030, description="End year")
    paper_limit: int = Field(default=10, ge=5, le=50, description="Number of papers to retrieve")
    language: str = Field(default="zh", description="Output language: zh or en")


class TaskResponse(BaseModel):
    task_id: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class TaskStatusResponse(BaseModel):
    task_id: str
    topic: str
    status: str
    current_phase: Optional[str] = None
    progress: int = 0
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PaperInfo(BaseModel):
    paper_index: int
    title: str
    authors: Optional[List[str]] = None
    year: Optional[int] = None
    abstract: Optional[str] = None
    source: str
    url: Optional[str] = None
    citation_count: int = 0
    relevance_score: Optional[float] = None


class AnalysisInfo(BaseModel):
    paper_index: int
    title: str
    problem: Optional[str] = None
    method: Optional[str] = None
    contribution: Optional[str] = None
    limitation: Optional[str] = None
    dataset: Optional[str] = None
    category: Optional[str] = None


class ReviewResult(BaseModel):
    task_id: str
    status: str
    outline: Optional[Dict] = None
    content: Optional[str] = None
    valid_citations: Optional[List[str]] = None
    invalid_citations: Optional[List[str]] = None
    citation_report: Optional[str] = None
    papers: Optional[List[PaperInfo]] = None
    analyses: Optional[List[AnalysisInfo]] = None
    rag_evidence: Optional[List[Dict[str, Any]]] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    message: str
    task_id: str
