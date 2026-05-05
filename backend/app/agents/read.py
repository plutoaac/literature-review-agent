"""
论文阅读分析 Agent（ReadAgent）

职责：调用 LLM 并发分析每篇论文的摘要，提取结构化信息。

提取的字段：
- problem（研究问题）：论文要解决什么问题
- method（使用方法）：采用了什么方法或技术
- contribution（主要贡献）：论文的主要贡献
- limitation（局限性）：论文的不足之处
- dataset（数据集）：使用的数据集
- category（研究方向分类）：如模型架构、训练方法、应用场景等

并发控制：使用 asyncio.Semaphore 限制最大并发数（默认 4），
避免同时发送过多 LLM 请求导致 API 限流。
"""

import asyncio
import logging
from typing import List, Dict
from app.services.llm import get_llm_client, LLMProviderError
from app.utils.json_parser import JsonExtractionError, extract_json_object

logger = logging.getLogger(__name__)


class ReadAgent:
    """论文阅读分析 Agent：并发调用 LLM 分析每篇论文的摘要"""

    def __init__(self, llm=None, max_concurrency: int = 4):
        """
        Args:
            llm: LLM 客户端实例（可选，默认从工厂函数创建）
            max_concurrency: 最大并发 LLM 请求数（防止 API 限流）
        """
        self.llm = llm or get_llm_client()
        self.max_concurrency = max_concurrency

    async def run(self, ranked_papers: List[Dict], output_language: str) -> List[Dict]:
        """
        并发分析所有论文

        Args:
            ranked_papers: 排序后的论文列表（来自 RankAgent）
            output_language: 输出语言（"zh" 或 "en"）

        Returns:
            分析结果列表，与输入论文一一对应，每篇新增 problem/method/contribution 等字段
        """
        logger.info(f"ReadAgent: Analyzing {len(ranked_papers)} papers")

        # 创建信号量，限制并发 LLM 请求数
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def analyze_with_limit(paper: Dict) -> Dict:
            """带并发限制的论文分析函数"""
            async with semaphore:
                return await self._analyze_paper(paper, output_language)

        # 并发执行所有论文分析
        # return_exceptions=True：单篇失败不会取消其他任务，异常作为结果返回
        results = await asyncio.gather(
            *[analyze_with_limit(paper) for paper in ranked_papers],
            return_exceptions=True
        )

        # 处理结果：异常的论文使用 fallback 分析
        analyses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"ReadAgent: Paper {i} failed: {result}")
                analyses.append(self._fallback_analysis(ranked_papers[i]))
            else:
                analyses.append(result)

        logger.info(f"ReadAgent: Completed {len(analyses)} analyses")
        return list(analyses)

    async def _analyze_paper(self, paper: Dict, output_language: str) -> Dict:
        """
        分析单篇论文

        Args:
            paper: 论文数据字典（包含 title、abstract 等）
            output_language: 输出语言

        Returns:
            原始论文数据 + 结构化分析结果
        """
        title = paper.get("title", "")
        abstract = paper.get("abstract", "") or "No abstract available"

        prompt = self._build_prompt(title, abstract, output_language)

        try:
            response = await self.llm.complete([
                {"role": "user", "content": prompt}
            ])

            # 解析 LLM 返回的 JSON
            result = self._parse_response(response)
            return {
                **paper,  # 保留原始论文数据
                "problem": result.get("problem"),
                "method": result.get("method"),
                "contribution": result.get("contribution"),
                "limitation": result.get("limitation"),
                "dataset": result.get("dataset"),
                "category": result.get("category")
            }
        except LLMProviderError as e:
            # LLM 调用失败时，使用 fallback（填充 N/A）
            logger.warning(f"ReadAgent LLM error for paper '{title}': {e}")
            return self._fallback_analysis(paper)

    def _build_prompt(self, title: str, abstract: str, output_language: str) -> str:
        """
        构建论文分析的 LLM 提示词

        要求 LLM 以 JSON 格式输出 6 个结构化字段，
        并明确指定「只输出JSON，不要有其他内容」以减少解析失败。
        """
        lang_instruction = (
            "请用中文回答" if output_language == "zh" else "Please answer in English"
        )

        return f"""{lang_instruction}

你是一个学术论文分析助手。请分析以下论文，提取结构化信息。

论文标题：{title}

摘要：
{abstract}

请提取以下信息并用JSON格式输出：

1. **研究问题**（problem）：这篇论文要解决什么问题？
2. **使用方法**（method）：论文采用了什么方法或技术？
3. **主要贡献**（contribution）：论文的主要贡献是什么？
4. **局限性**（limitation）：论文有什么局限性？
5. **数据集**（dataset）：论文使用了什么数据集？（如果没有则写"N/A"）
6. **分类**（category）：这篇论文属于哪个研究方向？（如：模型架构、训练方法、应用场景等）

请用JSON格式输出：
{{
    "problem": "...",
    "method": "...",
    "contribution": "...",
    "limitation": "...",
    "dataset": "...",
    "category": "..."
}}

只输出JSON，不要有其他内容。
"""

    def _parse_response(self, response: str) -> Dict:
        """解析 LLM 返回的 JSON 响应"""
        try:
            return extract_json_object(response)
        except JsonExtractionError as e:
            logger.warning(f"Failed to parse analysis response: {e}")
            return {}

    def _fallback_analysis(self, paper: Dict) -> Dict:
        """
        Fallback 策略：LLM 调用失败时，返回基础信息

        将所有结构化字段设为 N/A，确保下游流程不会因缺失字段而报错。
        """
        return {
            **paper,
            "problem": "N/A",
            "method": "N/A",
            "contribution": paper.get("title", "N/A"),
            "limitation": "N/A",
            "dataset": "N/A",
            "category": "General"
        }
