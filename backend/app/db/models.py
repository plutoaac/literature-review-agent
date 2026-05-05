"""
SQLAlchemy ORM 数据库模型定义

定义了 4 张表，构成文献综述系统的数据模型：

1. Task（任务表）：存储用户创建的综述任务
2. Paper（论文表）：存储检索到的论文元数据
3. PaperAnalysis（分析表）：存储 LLM 对每篇论文的结构化分析
4. Review（综述表）：存储最终生成的综述正文和引用校验结果

表关系：
- Task 1:N Paper（一个任务关联多篇论文）
- Paper 1:1 PaperAnalysis（一篇论文对应一份分析）
- Task 1:1 Review（一个任务对应一份综述）

级联删除：删除 Task 时，自动删除关联的 Paper、PaperAnalysis 和 Review。
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import declarative_base, relationship

# 声明式基类，所有 ORM 模型继承此类
Base = declarative_base()


class Task(Base):
    """
    任务表：存储用户创建的文献综述任务

    状态流转：pending → running → completed / failed
    """
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))  # 任务 UUID
    topic = Column(String(500), nullable=False)        # 研究主题
    year_from = Column(Integer, nullable=False)        # 检索起始年份
    year_to = Column(Integer, nullable=False)          # 检索结束年份
    paper_limit = Column(Integer, nullable=False, default=10)  # 最大论文数
    language = Column(String(10), nullable=False, default="zh")  # 输出语言
    status = Column(String(20), nullable=False, default="pending")  # 任务状态
    current_phase = Column(String(50), nullable=True)  # 当前执行阶段
    progress = Column(Integer, nullable=False, default=0)  # 进度百分比（0~100）
    error_message = Column(Text, nullable=True)        # 失败时的错误信息
    created_at = Column(DateTime, default=datetime.utcnow)  # 创建时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新时间

    # 关联关系
    papers = relationship("Paper", back_populates="task", cascade="all, delete-orphan")
    review = relationship("Review", back_populates="task", uselist=False, cascade="all, delete-orphan")


class Paper(Base):
    """
    论文表：存储检索到的论文元数据

    每篇论文关联一个任务（task_id），并可选地拥有一份分析结果（PaperAnalysis）。
    """
    __tablename__ = "papers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))  # 论文 UUID
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False)  # 关联的任务 ID
    paper_index = Column(Integer, nullable=False)      # 论文在排序结果中的编号（从 1 开始）
    title = Column(String(1000), nullable=False)       # 论文标题
    authors = Column(JSON, nullable=True)              # 作者列表（JSON 数组）
    year = Column(Integer, nullable=True)              # 发表年份
    abstract = Column(Text, nullable=True)             # 摘要
    source = Column(String(50), nullable=False)        # 来源：semantic_scholar / arxiv
    url = Column(String(1000), nullable=True)          # 论文链接
    citation_count = Column(Integer, default=0)        # 被引用次数
    embedding = Column(JSON, nullable=True)            # 预留字段（当前未使用）
    relevance_score = Column(Float, nullable=True)     # 相关性评分（0~1）
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联关系
    task = relationship("Task", back_populates="papers")
    analysis = relationship("PaperAnalysis", back_populates="paper", uselist=False, cascade="all, delete-orphan")


class PaperAnalysis(Base):
    """
    论文分析表：存储 LLM 对每篇论文的结构化分析

    由 ReadAgent 生成，包含研究问题、方法、贡献、局限性等字段。
    """
    __tablename__ = "paper_analyses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))  # 分析 UUID
    paper_id = Column(String(36), ForeignKey("papers.id"), nullable=False)  # 关联的论文 ID
    problem = Column(Text, nullable=True)              # 研究问题
    method = Column(Text, nullable=True)               # 使用方法
    contribution = Column(Text, nullable=True)         # 主要贡献
    limitation = Column(Text, nullable=True)           # 局限性
    dataset = Column(String(500), nullable=True)       # 使用的数据集
    category = Column(String(200), nullable=True)      # 研究方向分类
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联关系
    paper = relationship("Paper", back_populates="analysis")


class Review(Base):
    """
    综述表：存储最终生成的综述正文和引用校验结果

    由 WriteAgent 生成正文，CitationCheckAgent 生成引用校验结果。
    每个任务最多拥有一份综述（task_id 唯一约束）。
    """
    __tablename__ = "reviews"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))  # 综述 UUID
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False, unique=True)  # 关联的任务 ID（唯一）
    outline = Column(JSON, nullable=True)              # 综述大纲（嵌套字典）
    content = Column(Text, nullable=True)              # 综述正文（Markdown 格式）
    valid_citations = Column(JSON, nullable=True)      # 有效引用列表（JSON 数组）
    invalid_citations = Column(JSON, nullable=True)    # 无效引用列表（JSON 数组）
    citation_report = Column(Text, nullable=True)      # 引用校验报告（纯文本）
    rag_evidence = Column(JSON, nullable=True)         # RAG 证据链（缓存，避免重复计算）
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联关系
    task = relationship("Task", back_populates="review")
