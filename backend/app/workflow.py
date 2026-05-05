"""
文献综述工作流编排模块

本模块是整个系统的核心，负责串联所有 Agent 完成端到端的文献综述生成流程。

工作流步骤（9 个阶段，进度 0% → 100%）：
1. QueryAgent（10%）    — 理解用户研究主题，扩展搜索关键词
2. SearchAgent（20%）   — 从 arXiv + Semantic Scholar 双源检索论文
3. RankAgent（30%）     — 基于关键词匹配、引用数、年份等多维度排序
4. ReadAgent（50%）     — 调用 LLM 逐篇分析论文摘要，提取结构化信息
5. OrganizeAgent（60%） — 将论文按研究方向分类，生成对比表
6. OutlineAgent（70%）  — 生成综述层级大纲
7. RAG（75%）           — 基于关键词召回证据片段，为写作提供依据
8. WriteAgent（85%）    — 调用 LLM 撰写综述正文
9. CitationCheck（95%） — 正则校验引用编号，标记幻觉引用

每个阶段完成后都会将进度写入数据库，前端通过轮询获取实时进度。
"""

import uuid
import logging
from sqlalchemy.orm import Session
from app.db.models import Task, Paper, PaperAnalysis, Review
from app.agents.query import QueryAgent
from app.agents.search import SearchAgent
from app.agents.rank import RankAgent
from app.agents.read import ReadAgent
from app.agents.organize import OrganizeAgent
from app.agents.outline import OutlineAgent
from app.agents.write import WriteAgent
from app.agents.citation import CitationCheckAgent
from app.services.rag import get_rag_service

logger = logging.getLogger(__name__)


class NoPapersFoundError(Exception):
    """自定义异常：未检索到相关文献时抛出，前端会展示对应的用户友好提示"""
    pass


class ReviewWorkflow:
    """
    文献综述工作流编排器

    负责协调 8 个 Agent 和 1 个 RAG 服务，按顺序执行完整的综述生成流程。
    每个任务运行时会创建一个新的 ReviewWorkflow 实例。
    """

    def __init__(self):
        # 初始化所有 Agent（每个 Agent 内部会创建 LLM 客户端或搜索服务）
        self.query_agent = QueryAgent()           # 查询理解 Agent
        self.search_agent = SearchAgent()         # 文献检索 Agent
        self.rank_agent = RankAgent()             # 文献排序 Agent
        self.read_agent = ReadAgent()             # 论文阅读分析 Agent（并发限制 4）
        self.organize_agent = OrganizeAgent()     # 文献分类 Agent
        self.outline_agent = OutlineAgent()       # 大纲生成 Agent
        self.write_agent = WriteAgent()           # 综述写作 Agent
        self.citation_check_agent = CitationCheckAgent()  # 引用校验 Agent
        self.rag_service = get_rag_service()      # 轻量 RAG 服务（基于关键词召回）

    async def run(self, task_id: str, db: Session):
        """
        执行完整的文献综述生成工作流

        Args:
            task_id: 任务 UUID
            db: SQLAlchemy 数据库会话
        """
        logger.info(f"Workflow: Starting task {task_id}")

        # 从数据库读取任务信息
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.error(f"Workflow: Task {task_id} not found")
            return

        try:
            # ========== 阶段 1：查询理解（进度 0% → 10%）==========
            task.status = "running"
            task.current_phase = "QueryAgent"   # 前端显示当前阶段名称
            task.progress = 0
            db.commit()

            # 调用 QueryAgent 分析研究主题，生成英文搜索关键词和查询语句
            query_result = await self.query_agent.run(
                topic=task.topic,
                year_from=task.year_from,
                year_to=task.year_to,
                output_language=task.language
            )
            task.progress = 10
            db.commit()

            # ========== 阶段 2：文献检索（进度 10% → 20%）==========
            task.current_phase = "SearchAgent"
            db.commit()

            # 从 arXiv 和 Semantic Scholar 双源检索论文
            search_queries = [
                task.topic,
                *query_result.get("search_queries", []),
                *query_result.get("search_keywords", []),
            ]

            papers = await self.search_agent.run(
                search_queries=search_queries,
                year_from=task.year_from,
                year_to=task.year_to,
                limit=task.paper_limit
            )
            if not papers:
                raise NoPapersFoundError(
                    "未检索到相关文献，请尝试使用更具体的英文关键词、扩大年份范围或降低主题限定。"
                )
            task.progress = 20
            db.commit()

            # ========== 阶段 3：文献排序（进度 20% → 30%）==========
            task.current_phase = "RankAgent"
            db.commit()

            # 基于多维度（关键词匹配、引用数、年份、来源权重）对论文排序
            ranked_papers = await self.rank_agent.run(
                papers=papers,
                topic=task.topic,
                limit=task.paper_limit
            )
            if not ranked_papers:
                raise NoPapersFoundError(
                    "检索结果未能通过排序筛选，请调整研究主题或年份范围后重试。"
                )
            task.progress = 30
            db.commit()

            # ========== 阶段 4：论文阅读分析（进度 30% → 50%）==========
            task.current_phase = "ReadAgent"
            db.commit()

            # 调用 LLM 并发分析每篇论文的摘要，提取结构化信息（问题/方法/贡献/局限性）
            analyses = await self.read_agent.run(
                ranked_papers=ranked_papers,
                output_language=task.language
            )
            task.progress = 50
            db.commit()

            # ========== 阶段 5：文献分类（进度 50% → 60%）==========
            task.current_phase = "OrganizeAgent"
            db.commit()

            # 调用 LLM 将论文按研究方向分组，生成对比表
            organized = await self.organize_agent.run(
                analyses=analyses,
                output_language=task.language
            )
            task.progress = 60
            db.commit()

            # ========== 阶段 6：大纲生成（进度 60% → 70%）==========
            task.current_phase = "OutlineAgent"
            db.commit()

            # 调用 LLM 根据文献分类生成层级结构的综述大纲
            outline = await self.outline_agent.run(
                categories=organized.get("categories", []),
                topic=task.topic,
                output_language=task.language
            )
            task.progress = 70
            db.commit()

            # ========== 阶段 7：RAG 证据召回（进度 70% → 75%）==========
            task.current_phase = "RAGAgent"
            db.commit()

            # 基于综述大纲的每个章节，从论文分析中召回相关证据片段
            # 使用轻量关键词匹配（不依赖向量模型），适合课程设计部署
            rag_evidence = self.rag_service.build_evidence_pack(
                outline=outline,
                analyses=analyses,
                topic=task.topic
            )
            task.progress = 75
            db.commit()

            # ========== 阶段 8：综述写作（进度 75% → 85%）==========
            task.current_phase = "WriteAgent"
            db.commit()

            # 调用 LLM 根据大纲、论文信息和 RAG 证据撰写综述正文
            content = await self.write_agent.run(
                outline=outline,
                categories=organized.get("categories", []),
                ranked_papers=ranked_papers,
                rag_evidence=rag_evidence,
                output_language=task.language
            )
            task.progress = 85
            db.commit()

            # ========== 阶段 9：引用校验（进度 85% → 95%）==========
            task.current_phase = "CitationCheckAgent"
            db.commit()

            # 使用正则表达式提取综述中的 [paper_X] 引用，与实际论文列表比对
            # 标记幻觉引用（LLM 编造的不存在的引用）
            valid_ids = [f"paper_{p.get('paper_index', i+1)}" for i, p in enumerate(ranked_papers)]
            citation_result = self.citation_check_agent.run(content, valid_ids)
            task.progress = 95
            db.commit()

            # ========== 保存结果到数据库（进度 95% → 100%）==========
            self._save_results(task_id, db, ranked_papers, analyses, outline, content, citation_result, rag_evidence)

            # 标记任务完成
            task.status = "completed"
            task.progress = 100
            task.current_phase = "Done"
            db.commit()

            logger.info(f"Workflow: Task {task_id} completed successfully")

        except Exception as e:
            # 任何阶段失败，将任务标记为 failed 并记录错误信息
            # 不再 re-raise，由调用方（routes.py 的后台任务）统一处理
            logger.error(f"Workflow: Task {task_id} failed: {e}")
            task.status = "failed"
            task.error_message = str(e)
            db.commit()

    def _save_results(
        self,
        task_id: str,
        db: Session,
        ranked_papers: list,
        analyses: list,
        outline: dict,
        content: str,
        citation_result: dict,
        rag_evidence: list = None
    ):
        """
        将工作流结果保存到数据库

        采用「先删后插」策略：如果任务已有旧数据（如重跑任务），先清理再重新插入。
        使用 flush() 确保每篇论文获得 ID 后再插入关联的分析记录。
        """
        # 清理旧数据（支持任务重跑场景）
        old_paper_ids = [
            paper_id for (paper_id,) in db.query(Paper.id).filter(Paper.task_id == task_id).all()
        ]
        if old_paper_ids:
            # 先删子表（PaperAnalysis），再删父表（Paper），避免外键约束冲突
            db.query(PaperAnalysis).filter(PaperAnalysis.paper_id.in_(old_paper_ids)).delete(
                synchronize_session=False
            )
        db.query(Review).filter(Review.task_id == task_id).delete(synchronize_session=False)
        db.query(Paper).filter(Paper.task_id == task_id).delete(synchronize_session=False)
        db.flush()  # 确保删除操作提交到数据库（但不 commit，与后续插入在同一事务中）

        # 插入论文和分析数据
        for i, paper_data in enumerate(ranked_papers):
            paper = Paper(
                id=str(uuid.uuid4()),
                task_id=task_id,
                paper_index=paper_data.get("paper_index", i + 1),
                title=paper_data.get("title", "Untitled"),
                authors=paper_data.get("authors"),
                year=paper_data.get("year"),
                abstract=paper_data.get("abstract"),
                source=paper_data.get("source", "unknown"),
                url=paper_data.get("url"),
                citation_count=paper_data.get("citation_count", 0),
                relevance_score=paper_data.get("relevance_score")
            )
            db.add(paper)
            db.flush()  # 获取 paper.id，用于关联 PaperAnalysis

            # 插入论文分析结果
            analysis_data = analyses[i] if i < len(analyses) else {}
            analysis = PaperAnalysis(
                id=str(uuid.uuid4()),
                paper_id=paper.id,
                problem=analysis_data.get("problem"),
                method=analysis_data.get("method"),
                contribution=analysis_data.get("contribution"),
                limitation=analysis_data.get("limitation"),
                dataset=analysis_data.get("dataset"),
                category=analysis_data.get("category")
            )
            db.add(analysis)

        # 插入综述结果（大纲、正文、引用校验结果、RAG 证据缓存）
        review = Review(
            id=str(uuid.uuid4()),
            task_id=task_id,
            outline=outline,
            content=content,
            valid_citations=citation_result.get("valid_citations"),
            invalid_citations=citation_result.get("invalid_citations"),
            citation_report=citation_result.get("citation_report"),
            rag_evidence=rag_evidence
        )
        db.add(review)
        db.commit()  # 提交整个事务
