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
    pass


class ReviewWorkflow:
    def __init__(self):
        self.query_agent = QueryAgent()
        self.search_agent = SearchAgent()
        self.rank_agent = RankAgent()
        self.read_agent = ReadAgent()
        self.organize_agent = OrganizeAgent()
        self.outline_agent = OutlineAgent()
        self.write_agent = WriteAgent()
        self.citation_check_agent = CitationCheckAgent()
        self.rag_service = get_rag_service()

    async def run(self, task_id: str, db: Session):
        logger.info(f"Workflow: Starting task {task_id}")

        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.error(f"Workflow: Task {task_id} not found")
            return

        try:
            task.status = "running"
            task.current_phase = "QueryAgent"
            task.progress = 0
            db.commit()

            query_result = await self.query_agent.run(
                topic=task.topic,
                year_from=task.year_from,
                year_to=task.year_to,
                output_language=task.language
            )
            task.progress = 10
            db.commit()

            task.current_phase = "SearchAgent"
            db.commit()

            papers = await self.search_agent.run(
                search_queries=query_result.get("search_queries", [task.topic]),
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

            task.current_phase = "RankAgent"
            db.commit()

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

            task.current_phase = "ReadAgent"
            db.commit()

            analyses = await self.read_agent.run(
                ranked_papers=ranked_papers,
                output_language=task.language
            )
            task.progress = 50
            db.commit()

            task.current_phase = "OrganizeAgent"
            db.commit()

            organized = await self.organize_agent.run(
                analyses=analyses,
                output_language=task.language
            )
            task.progress = 60
            db.commit()

            task.current_phase = "OutlineAgent"
            db.commit()

            outline = await self.outline_agent.run(
                categories=organized.get("categories", []),
                topic=task.topic,
                output_language=task.language
            )
            task.progress = 70
            db.commit()

            task.current_phase = "RAGAgent"
            db.commit()

            rag_evidence = self.rag_service.build_evidence_pack(
                outline=outline,
                analyses=analyses,
                topic=task.topic
            )
            task.progress = 75
            db.commit()

            task.current_phase = "WriteAgent"
            db.commit()

            content = await self.write_agent.run(
                outline=outline,
                categories=organized.get("categories", []),
                ranked_papers=ranked_papers,
                rag_evidence=rag_evidence,
                output_language=task.language
            )
            task.progress = 85
            db.commit()

            task.current_phase = "CitationCheckAgent"
            db.commit()

            valid_ids = [f"paper_{p.get('paper_index', i+1)}" for i, p in enumerate(ranked_papers)]
            citation_result = self.citation_check_agent.run(content, valid_ids)
            task.progress = 95
            db.commit()

            self._save_results(task_id, db, ranked_papers, analyses, outline, content, citation_result)

            task.status = "completed"
            task.progress = 100
            task.current_phase = "Done"
            db.commit()

            logger.info(f"Workflow: Task {task_id} completed successfully")

        except Exception as e:
            logger.error(f"Workflow: Task {task_id} failed: {e}")
            task.status = "failed"
            task.error_message = str(e)
            db.commit()
            raise

    def _save_results(
        self,
        task_id: str,
        db: Session,
        ranked_papers: list,
        analyses: list,
        outline: dict,
        content: str,
        citation_result: dict
    ):
        old_paper_ids = [
            paper_id for (paper_id,) in db.query(Paper.id).filter(Paper.task_id == task_id).all()
        ]
        if old_paper_ids:
            db.query(PaperAnalysis).filter(PaperAnalysis.paper_id.in_(old_paper_ids)).delete(
                synchronize_session=False
            )
        db.query(Review).filter(Review.task_id == task_id).delete(synchronize_session=False)
        db.query(Paper).filter(Paper.task_id == task_id).delete(synchronize_session=False)
        db.flush()

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
            db.flush()

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

        review = Review(
            id=str(uuid.uuid4()),
            task_id=task_id,
            outline=outline,
            content=content,
            valid_citations=citation_result.get("valid_citations"),
            invalid_citations=citation_result.get("invalid_citations"),
            citation_report=citation_result.get("citation_report")
        )
        db.add(review)
        db.commit()
