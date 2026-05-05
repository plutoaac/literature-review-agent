"""
API 路由定义模块

定义文献综述系统的 5 个 RESTful API 端点：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/tasks | 创建新任务 |
| GET  | /api/tasks/{id} | 查询任务状态 |
| POST | /api/tasks/{id}/run | 启动任务执行 |
| GET  | /api/tasks/{id}/result | 获取综述结果 |
| GET  | /api/tasks/{id}/export | 导出 Markdown |

所有端点使用 FastAPI 的依赖注入获取数据库会话（get_db），
任务执行通过 BackgroundTasks 在后台异步运行，不阻塞 HTTP 响应。
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db, SessionLocal
from app.db.models import Task, Paper, PaperAnalysis, Review
from app.schemas import (
    TaskCreate,
    TaskResponse,
    TaskStatusResponse,
    TaskHistoryItem,
    ReviewResult,
    PaperInfo,
    AnalysisInfo,
    MessageResponse
)
from app.workflow import ReviewWorkflow
from app.services.exporter import get_exporter
from app.services.rag import get_rag_service

logger = logging.getLogger(__name__)

# 创建路由组，所有端点以 /api/tasks 开头
router = APIRouter(prefix="/api/tasks", tags=["tasks"])


async def run_workflow_task(task_id: str):
    """
    后台任务：执行文献综述工作流

    由 BackgroundTasks 调度，在独立的异步上下文中运行，
    不阻塞 HTTP 请求/响应循环。

    工作流内部已捕获异常并标记任务状态为 failed，
    此处仅做兜底处理（如工作流外的未预期异常）。
    """
    db = SessionLocal()  # 创建独立的数据库会话（后台任务不能共享请求的会话）
    try:
        workflow = ReviewWorkflow()
        await workflow.run(task_id, db)
    except Exception as e:
        # 兜底处理：工作流内部已处理大部分异常，此处捕获未预期的异常
        logger.exception("Background workflow failed for task %s", task_id)
        task = db.query(Task).filter(Task.id == task_id).first()
        if task and task.status != "failed":  # 避免重复设置
            task.status = "failed"
            task.current_phase = "Failed"
            task.error_message = str(e)
            db.commit()
    finally:
        db.close()  # 确保关闭数据库会话


@router.get("", response_model=list[TaskHistoryItem])
async def list_tasks(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """获取最近任务列表，用于首页历史记录面板。"""
    limit = max(1, min(limit, 50))
    tasks = (
        db.query(Task)
        .order_by(Task.created_at.desc())
        .limit(limit)
        .all()
    )

    task_ids = [task.id for task in tasks]
    review_task_ids = set()
    if task_ids:
        review_task_ids = {
            task_id
            for (task_id,) in db.query(Review.task_id)
            .filter(Review.task_id.in_(task_ids))
            .all()
        }

    return [
        TaskHistoryItem(
            task_id=task.id,
            topic=task.topic,
            status=task.status,
            current_phase=task.current_phase,
            progress=task.progress,
            paper_limit=task.paper_limit,
            language=task.language,
            error_message=task.error_message,
            created_at=task.created_at,
            updated_at=task.updated_at,
            has_result=task.id in review_task_ids,
        )
        for task in tasks
    ]


@router.post("", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db)
):
    """
    创建新任务（POST /api/tasks）

    只创建任务记录（status="pending"），不立即执行。
    需要再调用 POST /api/tasks/{id}/run 启动执行。

    Args:
        task_data: 任务参数（研究主题、年份范围、论文数量、语言）
        db: 数据库会话（依赖注入）

    Returns:
        包含 task_id、status、created_at 的响应
    """
    import uuid

    task = Task(
        id=str(uuid.uuid4()),
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
    db.refresh(task)  # 刷新以获取数据库生成的默认值（如 created_at）

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
    """
    查询任务状态（GET /api/tasks/{task_id}）

    前端通过轮询此接口获取任务进度（progress 0~100）和当前阶段（current_phase）。

    Returns:
        任务状态信息，包含进度百分比和当前执行阶段
    """
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
    """
    启动任务执行（POST /api/tasks/{task_id}/run）

    将工作流添加到 FastAPI 的后台任务队列，立即返回 "Task started" 响应。
    工作流在后台异步执行，前端通过轮询 get_task_status 获取进度。

    Args:
        task_id: 任务 UUID
        background_tasks: FastAPI 后台任务管理器
        db: 数据库会话

    Returns:
        启动确认消息
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 防止重复启动正在运行的任务
    if task.status == "running":
        raise HTTPException(status_code=400, detail="Task is already running")

    # 重置任务状态（支持重跑失败的任务）
    task.status = "pending"
    task.error_message = None
    task.current_phase = None
    task.progress = 0
    db.commit()

    # 将工作流添加到后台任务队列（非阻塞）
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
    """
    获取综述结果（GET /api/tasks/{task_id}/result）

    返回完整的综述结果，包含：
    - 论文列表和分析数据
    - 综述大纲和正文
    - RAG 证据链
    - 引用校验结果

    注意：RAG 证据在此接口中重新计算（而非存储），
    意味着每次请求都会触发一次 RAG 召回。
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 查询关联的论文列表
    papers = db.query(Paper).filter(Paper.task_id == task_id).order_by(Paper.paper_index).all()

    # 查询每篇论文的分析结果
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

    # 查询综述结果（大纲、正文、引用校验）
    review = db.query(Review).filter(Review.task_id == task_id).first()

    # 构建论文信息列表
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

    # 重新计算 RAG 证据（将论文和分析数据合并为 RAG 输入格式）
    rag_inputs = []
    for paper in papers:
        analysis = db.query(PaperAnalysis).filter(PaperAnalysis.paper_id == paper.id).first()
        if analysis:
            rag_inputs.append({
                "paper_index": paper.paper_index,
                "title": paper.title,
                "abstract": paper.abstract,
                "source": paper.source,
                "year": paper.year,
                "problem": analysis.problem,
                "method": analysis.method,
                "contribution": analysis.contribution,
                "limitation": analysis.limitation,
                "category": analysis.category,
            })

    # RAG 证据：优先使用缓存（workflow 中计算并存储），否则重新计算
    rag_evidence = review.rag_evidence if review and review.rag_evidence else None
    if not rag_evidence:
        # 降级：重新计算（兼容旧数据或缓存缺失的情况）
        rag_evidence = get_rag_service().build_evidence_pack(
            outline=review.outline if review else None,
            analyses=rag_inputs,
            topic=task.topic,
        )

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
        rag_evidence=rag_evidence,
        error_message=task.error_message
    )


@router.get("/{task_id}/export")
async def export_markdown(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    导出 Markdown（GET /api/tasks/{task_id}/export）

    将综述结果导出为 Markdown 格式，返回 JSON 包含 content 和 filename。
    前端接收后创建 Blob 并触发浏览器下载。

    Returns:
        {"content": "Markdown 内容", "filename": "review_主题_任务ID.md"}
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 查询论文和分析数据
    papers = db.query(Paper).filter(Paper.task_id == task_id).order_by(Paper.paper_index).all()
    analyses = []
    for paper in papers:
        analysis = db.query(PaperAnalysis).filter(PaperAnalysis.paper_id == paper.id).first()
        if analysis:
            analyses.append({
                "paper_index": paper.paper_index,
                "title": paper.title,
                "abstract": paper.abstract,
                "source": paper.source,
                "year": paper.year,
                "problem": analysis.problem,
                "method": analysis.method,
                "contribution": analysis.contribution,
                "limitation": analysis.limitation,
                "dataset": analysis.dataset,
                "category": analysis.category
            })

    # 查询综述并获取 RAG 证据（优先使用缓存）
    review = db.query(Review).filter(Review.task_id == task_id).first()
    rag_evidence = review.rag_evidence if review and review.rag_evidence else None
    if not rag_evidence:
        rag_evidence = get_rag_service().build_evidence_pack(
            outline=review.outline if review else None,
            analyses=analyses,
            topic=task.topic,
        )

    # 将 ORM 对象转为字典（移除 SQLAlchemy 内部属性）
    paper_dicts = [p.__dict__ for p in papers]
    for p in paper_dicts:
        p.pop('_sa_instance_state', None)

    # 调用导出器生成 Markdown
    exporter = get_exporter()
    markdown_content = exporter.export(
        topic=task.topic,
        papers=paper_dicts,
        analyses=analyses,
        outline=review.outline if review else None,
        content=review.content if review else None,
        valid_citations=review.valid_citations if review else None,
        citation_report=review.citation_report if review else "",
        rag_evidence=rag_evidence
    )

    return {
        "content": markdown_content,
        "filename": f"review_{task.topic[:20]}_{task_id[:8]}.md"
    }
