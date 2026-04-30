import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db, SessionLocal
from app.db.models import Task, Paper, PaperAnalysis, Review
from app.schemas import (
    TaskCreate,
    TaskResponse,
    TaskStatusResponse,
    ReviewResult,
    PaperInfo,
    AnalysisInfo,
    MessageResponse
)
from app.workflow import ReviewWorkflow
from app.services.exporter import get_exporter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


async def run_workflow_task(task_id: str):
    db = SessionLocal()
    try:
        workflow = ReviewWorkflow()
        await workflow.run(task_id, db)
    except Exception as e:
        logger.exception("Background workflow failed for task %s", task_id)
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = "failed"
            task.current_phase = "Failed"
            task.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.post("", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db)
):
    task = Task(
        id=str(__import__('uuid').uuid4()),
        topic=task_data.topic,
        year_from=task_data.year_from,
        year_to=task_data.year_to,
        paper_limit=task_data.paper_limit,
        language=task_data.language,
        status="pending",
        progress=0
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return TaskResponse(
        task_id=task.id,
        status=task.status,
        created_at=task.created_at
    )


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatusResponse(
        task_id=task.id,
        topic=task.topic,
        status=task.status,
        current_phase=task.current_phase,
        progress=task.progress,
        error_message=task.error_message,
        created_at=task.created_at
    )


@router.post("/{task_id}/run", response_model=MessageResponse)
async def run_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status == "running":
        raise HTTPException(status_code=400, detail="Task is already running")

    task.status = "pending"
    task.error_message = None
    task.current_phase = None
    task.progress = 0
    db.commit()

    background_tasks.add_task(run_workflow_task, task_id)

    return MessageResponse(
        message="Task started",
        task_id=task_id
    )


@router.get("/{task_id}/result", response_model=ReviewResult)
async def get_task_result(
    task_id: str,
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    papers = db.query(Paper).filter(Paper.task_id == task_id).order_by(Paper.paper_index).all()
    analyses = []
    for paper in papers:
        analysis = db.query(PaperAnalysis).filter(PaperAnalysis.paper_id == paper.id).first()
        if analysis:
            analyses.append(AnalysisInfo(
                paper_index=paper.paper_index,
                title=paper.title,
                problem=analysis.problem,
                method=analysis.method,
                contribution=analysis.contribution,
                limitation=analysis.limitation,
                dataset=analysis.dataset,
                category=analysis.category
            ))

    review = db.query(Review).filter(Review.task_id == task_id).first()

    paper_infos = []
    for p in papers:
        paper_infos.append(PaperInfo(
            paper_index=p.paper_index,
            title=p.title,
            authors=p.authors,
            year=p.year,
            abstract=p.abstract,
            source=p.source,
            url=p.url,
            citation_count=p.citation_count,
            relevance_score=p.relevance_score
        ))

    return ReviewResult(
        task_id=task_id,
        status=task.status,
        outline=review.outline if review else None,
        content=review.content if review else None,
        valid_citations=review.valid_citations if review else None,
        invalid_citations=review.invalid_citations if review else None,
        citation_report=review.citation_report if review else None,
        papers=paper_infos,
        analyses=analyses,
        error_message=task.error_message
    )


@router.get("/{task_id}/export")
async def export_markdown(
    task_id: str,
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    papers = db.query(Paper).filter(Paper.task_id == task_id).order_by(Paper.paper_index).all()
    analyses = []
    for paper in papers:
        analysis = db.query(PaperAnalysis).filter(PaperAnalysis.paper_id == paper.id).first()
        if analysis:
            analyses.append({
                "paper_index": paper.paper_index,
                "title": paper.title,
                "problem": analysis.problem,
                "method": analysis.method,
                "contribution": analysis.contribution,
                "limitation": analysis.limitation,
                "dataset": analysis.dataset,
                "category": analysis.category
            })

    review = db.query(Review).filter(Review.task_id == task_id).first()

    paper_dicts = [p.__dict__ for p in papers]
    for p in paper_dicts:
        p.pop('_sa_instance_state', None)

    exporter = get_exporter()
    markdown_content = exporter.export(
        topic=task.topic,
        papers=paper_dicts,
        analyses=analyses,
        outline=review.outline if review else None,
        content=review.content if review else None,
        valid_citations=review.valid_citations if review else None,
        citation_report=review.citation_report if review else ""
    )

    return {
        "content": markdown_content,
        "filename": f"review_{task.topic[:20]}_{task_id[:8]}.md"
    }
