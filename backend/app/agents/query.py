"""
查询理解 Agent（QueryAgent）

职责：分析用户输入的研究主题，扩展为多个英文搜索关键词和查询语句。

工作流程：
1. 接收用户的研究主题（中文或英文）、年份范围、输出语言
2. 调用 LLM 分析主题，生成：
   - search_keywords：相关关键词列表（含中英文术语、同义词）
   - search_queries：用于学术数据库的英文检索语句
   - research_scope：研究范围说明
3. 如果 LLM 调用失败，使用 fallback 策略生成基础查询
"""

import logging
from typing import List, Dict
from app.services.llm import get_llm_client, LLMProviderError
from app.utils.json_parser import JsonExtractionError, extract_json_object

logger = logging.getLogger(__name__)


class QueryAgent:
    """查询理解 Agent：将用户主题转化为有效的学术检索查询"""

    def __init__(self, llm=None):
        """
        Args:
            llm: LLM 客户端实例（可选，默认从工厂函数创建）
                 支持依赖注入，方便单元测试时传入 mock 对象
        """
        self.llm = llm or get_llm_client()

    async def run(
        self,
        topic: str,
        year_from: int,
        year_to: int,
        output_language: str
    ) -> Dict:
        """
        执行查询理解

        Args:
            topic: 用户输入的研究主题
            year_from: 检索起始年份
            year_to: 检索结束年份
            output_language: 输出语言（"zh" 或 "en"）

        Returns:
            包含 search_keywords、search_queries、research_scope 的字典
        """
        logger.info(f"QueryAgent: Analyzing topic '{topic}'")

        # 构建 LLM 提示词
        prompt = self._build_prompt(topic, year_from, year_to, output_language)

        try:
            # 调用 LLM 获取响应
            response = await self.llm.complete([
                {"role": "user", "content": prompt}
            ])

            # 解析 LLM 返回的 JSON
            return self._parse_response(response, topic)
        except LLMProviderError as e:
            # LLM 调用失败时，使用 fallback 策略（基于规则生成基础查询）
            logger.error(f"QueryAgent LLM error: {e}")
            return self._fallback_response(topic)

    def _build_prompt(
        self,
        topic: str,
        year_from: int,
        year_to: int,
        output_language: str
    ) -> str:
        """
        构建发送给 LLM 的提示词

        提示词要求 LLM 以 JSON 格式输出搜索关键词、查询语句和范围说明。
        关键点：要求 search_queries 优先使用英文（因为 arXiv 和 Semantic Scholar 主要索引英文文献）。
        """
        lang_instruction = (
            "请用中文回答" if output_language == "zh" else "Please answer in English"
        )

        return f"""{lang_instruction}

你是一个学术研究助手，帮助用户扩展研究主题的关键词。

用户的研究主题是：{topic}
年份范围：{year_from} - {year_to}

请分析这个主题，输出以下信息：

1. **搜索关键词**（search_keywords）：列出5-10个相关关键词，包括中文主题对应的英文术语、同义词和相关研究方向
2. **搜索查询**（search_queries）：生成5-8个英文检索查询语句，用于 arXiv、Semantic Scholar 等英文学术数据库检索
3. **研究范围说明**（research_scope）：简要说明这个研究主题的范围和重点

请用JSON格式输出：
{{
    "search_keywords": ["English keyword 1", "English keyword 2", "中文关键词1", ...],
    "search_queries": ["English academic query 1", "English academic query 2", ...],
    "research_scope": "范围说明..."
}}

注意：search_queries 必须优先使用英文，不要只输出中文查询。只输出JSON，不要有其他内容。
"""

    def _parse_response(self, response: str, fallback_topic: str) -> Dict:
        """解析 LLM 返回的 JSON 响应，失败时使用 fallback"""
        try:
            return extract_json_object(response)
        except JsonExtractionError as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return self._fallback_response(fallback_topic)

    def _fallback_response(self, topic: str) -> Dict:
        """
        Fallback 策略：当 LLM 调用失败时，基于规则生成基础查询

        对于常见的中文研究主题（如"透明物体深度补全"），使用预定义的英文关键词。
        其他主题则使用简单的字符串变换（小写、下划线替换等）。
        """
        lower_topic = topic.lower()
        keywords = [
            topic,
            lower_topic,
            topic.replace(" ", "_"),
        ]
        search_queries = [topic, f"{topic} research", f"{topic} survey"]

        # 针对"透明物体+深度"主题的硬编码优化（课程设计演示用）
        if "透明物体" in topic and "深度" in topic:
            keywords.extend([
                "transparent object",
                "transparent objects",
                "depth completion",
                "depth estimation",
                "transparent object reconstruction",
            ])
            search_queries = [
                "transparent object depth completion",
                "depth completion for transparent objects",
                "transparent object depth estimation",
                "transparent object reconstruction depth",
                "ClearGrasp transparent object depth",
                "TransCG transparent object depth completion",
            ]

        return {
            "search_keywords": keywords,
            "search_queries": search_queries,
            "research_scope": f"Research on {topic}"
        }
