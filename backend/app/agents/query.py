import logging
from typing import List, Dict
from app.services.llm import get_llm_client, LLMProviderError
from app.utils.json_parser import JsonExtractionError, extract_json_object

logger = logging.getLogger(__name__)


class QueryAgent:
    def __init__(self):
        self.llm = get_llm_client()

    async def run(
        self,
        topic: str,
        year_from: int,
        year_to: int,
        output_language: str
    ) -> Dict:
        logger.info(f"QueryAgent: Analyzing topic '{topic}'")

        prompt = self._build_prompt(topic, year_from, year_to, output_language)

        try:
            response = await self.llm.complete([
                {"role": "user", "content": prompt}
            ])

            return self._parse_response(response, topic)
        except LLMProviderError as e:
            logger.error(f"QueryAgent LLM error: {e}")
            return self._fallback_response(topic)

    def _build_prompt(
        self,
        topic: str,
        year_from: int,
        year_to: int,
        output_language: str
    ) -> str:
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
        try:
            return extract_json_object(response)
        except JsonExtractionError as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return self._fallback_response(fallback_topic)

    def _fallback_response(self, topic: str) -> Dict:
        lower_topic = topic.lower()
        keywords = [
            topic,
            lower_topic,
            topic.replace(" ", "_"),
        ]
        search_queries = [topic, f"{topic} research", f"{topic} survey"]

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
