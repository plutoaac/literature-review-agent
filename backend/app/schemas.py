"""
Pydantic 数据模型定义模块

定义 API 请求和响应的数据结构，用于：
1. 请求参数校验（自动生成 422 错误响应）
2. 响应数据序列化（自动过滤多余字段）
3. OpenAPI 文档自动生成（Swagger UI 中展示字段说明）
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class TaskCreate(BaseModel):
    """创建任务的请求体"""
    topic: str = Field(..., min_length=1, max_length=500, description="Research topic")           # 研究主题，必填
    year_from: int = Field(..., ge=1900, le=2030, description="Start year")                      # 检索起始年份
    year_to: int = Field(..., ge=1900, le=2030, description="End year")                          # 检索结束年份
    paper_limit: int = Field(default=10, ge=5, le=50, description="Number of papers to retrieve") # 最大检索论文数（5~50）
    language: str = Field(default="zh", description="Output language: zh or en")                  # 输出语言："zh" 中文 / "en" 英文


class TaskResponse(BaseModel):
    """创建任务后的响应"""
    task_id: str          # 任务唯一标识（UUID）
    status: str           # 任务状态：pending / running / completed / failed
    created_at: datetime  # 创建时间

    class Config:
        from_attributes = True  # 支持从 ORM 对象直接转换（Pydantic v2）


class TaskStatusResponse(BaseModel):
    """查询任务状态的响应"""
    task_id: str
    topic: str                            # 研究主题
    status: str                           # 当前状态
    current_phase: Optional[str] = None   # 当前执行阶段（如 QueryAgent、SearchAgent 等）
    progress: int = 0                     # 进度百分比（0~100）
    error_message: Optional[str] = None   # 失败时的错误信息
    created_at: datetime

    class Config:
        from_attributes = True


class TaskHistoryItem(BaseModel):
    """历史任务列表项"""
    task_id: str
    topic: str
    status: str
    current_phase: Optional[str] = None
    progress: int = 0
    paper_limit: int
    language: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    has_result: bool = False

    class Config:
        from_attributes = True


class PaperInfo(BaseModel):
    """单篇论文的基本信息"""
    paper_index: int                           # 论文在排序结果中的编号（从 1 开始）
    title: str                                 # 论文标题
    authors: Optional[List[str]] = None        # 作者列表
    year: Optional[int] = None                 # 发表年份
    abstract: Optional[str] = None             # 摘要
    source: str                                # 来源：semantic_scholar / arxiv
    url: Optional[str] = None                  # 论文链接
    citation_count: int = 0                    # 被引用次数
    relevance_score: Optional[float] = None    # 与研究主题的相关性评分（0~1）


class AnalysisInfo(BaseModel):
    """单篇论文的结构化分析结果"""
    paper_index: int
    title: str
    problem: Optional[str] = None       # 研究问题
    method: Optional[str] = None        # 使用方法
    contribution: Optional[str] = None  # 主要贡献
    limitation: Optional[str] = None    # 局限性
    dataset: Optional[str] = None       # 使用的数据集
    category: Optional[str] = None      # 研究方向分类


class ReviewResult(BaseModel):
    """综述结果的完整响应（包含论文、分析、综述正文、RAG 证据等）"""
    task_id: str
    status: str
    outline: Optional[Dict] = None                   # 综述大纲（嵌套字典结构）
    content: Optional[str] = None                    # 综述正文（Markdown 格式）
    valid_citations: Optional[List[str]] = None      # 有效引用列表
    invalid_citations: Optional[List[str]] = None    # 无效引用列表（幻觉引用）
    citation_report: Optional[str] = None            # 引用校验报告文本
    papers: Optional[List[PaperInfo]] = None         # 论文列表
    analyses: Optional[List[AnalysisInfo]] = None    # 论文分析列表
    rag_evidence: Optional[List[Dict[str, Any]]] = None  # RAG 证据链（按章节组织）
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """通用消息响应（用于操作确认类接口）"""
    message: str    # 消息内容
    task_id: str    # 关联的任务 ID
