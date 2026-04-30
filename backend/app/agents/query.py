import logging
from typing import List, Dict
from app.services.llm import get_llm_client, LLMProviderError

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

            return self._parse_response(response)
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

1. **搜索关键词**（search_keywords）：列出5-10个相关关键词，包括同义词和相关研究方向
2. **搜索查询**（search_queries）：生成3-5个检索查询语句，用于学术文献检索
3. **研究范围说明**（research_scope）：简要说明这个研究主题的范围和重点

请用JSON格式输出：
{{
    "search_keywords": ["关键词1", "关键词2", ...],
    "search_queries": ["查询语句1", "查询语句2", ...],
    "research_scope": "范围说明..."
}}

只输出JSON，不要有其他内容。
"""

    def _parse_response(self, response: str) -> Dict:
        try:
            import json
            for line in response.strip().split('\n'):
                line = line.strip()
                if line.startswith('{') and line.endswith('}'):
                    return json.loads(line)
            return json.loads(response.strip())
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return self._fallback_response("")

    def _fallback_response(self, topic: str) -> Dict:
        keywords = [
            topic,
            topic.lower(),
            topic.replace(" ", "_"),
        ]

        return {
            "search_keywords": keywords,
            "search_queries": [topic, f"{topic} research", f"{topic} survey"],
            "research_scope": f"Research on {topic}"
        }
